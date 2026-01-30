"""
LangGraph StateGraph for intelligent conversation agent.

This module implements the conversation agent using the new architecture:
- UnifiedMemory for comprehensive state management
- FlowInterpreter for goal-based flow understanding
- AIBrain for intelligent, natural responses
- GoalTracker for progress tracking
- PostgreSQL checkpointing for persistence
"""
from __future__ import annotations

import logging
from typing import Optional, Any
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    BaseMessage
)
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from ..core.config import settings
from ..models import Company, Lead, LeadUpdate, Conversation, FlowConfig
from ..services.database import db
from ..services.elevenlabs import elevenlabs, ElevenLabsService
from ..services.openai_tts import openai_tts
from ..services.notification import notification_service

# New architecture imports
from .memory import UnifiedMemory, MemoryManager, Sentiment
from .flow_interpreter import FlowInterpreter, FlowIntent, interpret_flow
from .brain import AIBrain, CompanyContext, BrainDecision, ResponseAction
from .goal_tracker import GoalTracker, ExtractionResult
from .checkpointer import SupabaseCheckpointSaver, create_checkpointer

# Router and Proposal Agent
from .router import agent_router, AgentType, RoutingDecision
from .proposal_agent import proposal_agent, ProposalDecision
from ..services.proposal_service import proposal_service

# Legacy imports for backward compatibility
from .state import (
    AgentState,
    CompanyConfig,
    ToolResult,
    create_initial_state,
    merge_lead_data,
    get_conversation_context
)
from .prompts import PromptBuilder
from .tools import get_all_tools

logger = logging.getLogger(__name__)


class IntelligentConversationGraph:
    """
    Intelligent conversation agent using the new architecture.

    This class orchestrates conversations using:
    - UnifiedMemory: Complete memory system
    - FlowInterpreter: Goal-based flow understanding
    - AIBrain: Intelligent response generation
    - GoalTracker: Progress monitoring
    """

    def __init__(self, use_postgres_checkpointer: bool = True):
        """
        Initialize the intelligent conversation graph.

        Args:
            use_postgres_checkpointer: Use PostgreSQL for checkpointing (default True)
        """
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.7
        )

        self.tools = get_all_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Initialize AIBrain
        self.brain = AIBrain()

        # Initialize memory manager
        self.memory_manager = MemoryManager(db)

        # Checkpointer - try PostgreSQL, fallback to Memory
        if use_postgres_checkpointer:
            try:
                self.checkpointer = create_checkpointer()
                logger.info("[GRAPH] Using PostgreSQL checkpointer")
            except Exception as e:
                logger.warning(f"[GRAPH] PostgreSQL checkpointer failed, using MemorySaver: {e}")
                self.checkpointer = MemorySaver()
        else:
            self.checkpointer = MemorySaver()

        # Build the graph
        self.graph = self._build_graph()

        logger.info(f"[GRAPH] Intelligent graph initialized with {len(self.tools)} tools")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph with intelligent routing."""
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("router", self._router_node)
        graph.add_node("intelligent_processor", self._intelligent_processor_node)
        graph.add_node("proposal_processor", self._proposal_processor_node)
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(self.tools))
        graph.add_node("response_formatter", self._response_formatter_node)

        # Set entry point
        graph.set_entry_point("router")

        # Add conditional edges from router
        graph.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "intelligent_processor": "intelligent_processor",
                "proposal_processor": "proposal_processor",
                "agent": "agent",
                "end": END
            }
        )

        # Add conditional edges from agent (for tool calls)
        graph.add_conditional_edges(
            "agent",
            self._should_use_tools,
            {
                "tools": "tools",
                "response_formatter": "response_formatter"
            }
        )

        # Tools always go back to agent
        graph.add_edge("tools", "agent")

        # Intelligent processor goes to response formatter
        graph.add_edge("intelligent_processor", "response_formatter")

        # Proposal processor goes to response formatter
        graph.add_edge("proposal_processor", "response_formatter")

        # Response formatter ends the graph
        graph.add_edge("response_formatter", END)

        # Compile with checkpointer
        compiled = graph.compile(checkpointer=self.checkpointer)

        logger.info("[GRAPH] Intelligent graph compiled successfully")
        return compiled

    def _router_node(self, state: AgentState) -> dict[str, Any]:
        """
        Router node - decides the execution path.

        Routes to:
        - proposal_processor: If lead has active proposal (closing mode)
        - intelligent_processor: If there's an active flow (uses new architecture)
        - agent: For free conversation without flow
        - end: If AI is disabled or requires human
        """
        logger.info(f"[ROUTER] Processing - ai_enabled={state.get('ai_enabled')}, "
                   f"current_node_id={state.get('current_node_id')}")

        # Check if AI is disabled or requires human
        if not state.get("ai_enabled", True):
            logger.info("[ROUTER] AI disabled - routing to end")
            return {"next_node": "end"}

        if state.get("requires_human", False):
            logger.info("[ROUTER] Requires human - routing to end")
            return {"next_node": "end"}

        # Check if lead has active proposal - use proposal processor (closing mode)
        lead_data = state.get("lead_data", {})
        proposta_ativa_id = lead_data.get("proposta_ativa_id") or state.get("proposta_ativa_id")

        if proposta_ativa_id:
            logger.info(f"[ROUTER] Active proposal {proposta_ativa_id} detected - routing to proposal_processor")
            return {"next_node": "proposal_processor", "proposta_ativa_id": proposta_ativa_id}

        # Check if there's an active flow - use intelligent processor
        flow_config = state.get("flow_config")
        if flow_config:
            logger.info("[ROUTER] Flow detected - routing to intelligent_processor")
            return {"next_node": "intelligent_processor"}

        # Default to free agent
        logger.info("[ROUTER] No flow - routing to agent")
        return {"next_node": "agent"}

    def _route_decision(self, state: AgentState) -> str:
        """Determine the next node based on router output."""
        next_node = state.get("next_node", "intelligent_processor")
        # Valid nodes: intelligent_processor, proposal_processor, agent, end
        if next_node in ["intelligent_processor", "proposal_processor", "agent", "end"]:
            return next_node
        return "intelligent_processor"

    def _should_use_tools(self, state: AgentState) -> str:
        """Determine if the agent should use tools."""
        messages = state.get("messages", [])
        if not messages:
            return "response_formatter"

        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            logger.info(f"[AGENT] Tool calls detected: {[tc['name'] for tc in last_message.tool_calls]}")
            return "tools"

        return "response_formatter"

    async def _intelligent_processor_node(self, state: AgentState) -> dict[str, Any]:
        """
        Intelligent processor node - the heart of the new architecture.

        This node:
        1. Loads UnifiedMemory with full context
        2. Interprets flow as goals using FlowInterpreter
        3. Uses AIBrain to understand and respond naturally
        4. Tracks progress with GoalTracker
        5. Updates memory for persistence
        """
        logger.info("[INTELLIGENT] Processing with new architecture")

        result = {}

        try:
            # Get identifiers
            lead_id = state.get("lead_id")
            conversation_id = state.get("conversation_id")
            company_config = state.get("company_config", {})

            # Get user message
            user_message = self._get_last_user_message(state)
            if not user_message:
                return {"response": "Como posso ajudar?"}

            # Step 1: Load or create UnifiedMemory
            try:
                memory = await self.memory_manager.load_memory(lead_id, conversation_id)
            except ValueError:
                # Create new memory if not found
                memory = UnifiedMemory(
                    lead_id=lead_id,
                    conversation_id=conversation_id,
                    collected_data=state.get("lead_data", {})
                )

            # Merge any existing collected fields
            collected = state.get("collected_fields", {})
            for field, value in collected.items():
                if value:
                    memory.collected_data[field] = value

            # Step 2: Interpret flow as goals
            flow_config = state.get("flow_config", {})
            if flow_config:
                try:
                    if isinstance(flow_config, dict):
                        flow = FlowConfig(**flow_config)
                    else:
                        flow = flow_config
                    flow_intent = interpret_flow(flow)
                except Exception as e:
                    logger.error(f"[INTELLIGENT] Flow interpretation error: {e}")
                    flow_intent = FlowIntent()
            else:
                flow_intent = FlowIntent()

            # Apply settings from company config
            flow_intent.company_name = company_config.get("company_name", "")
            flow_intent.agent_name = company_config.get("agent_name", "Assistente")
            flow_intent.agent_tone = company_config.get("agent_tone", "amigavel")
            flow_intent.use_emojis = company_config.get("use_emojis", False)

            # Step 3: Create GoalTracker
            goal_tracker = GoalTracker(flow_intent, memory)

            # Step 4: Create CompanyContext for AIBrain
            company_context = CompanyContext(
                company_name=company_config.get("company_name", "Empresa"),
                agent_name=company_config.get("agent_name", "Assistente"),
                agent_tone=company_config.get("agent_tone", "amigavel"),
                use_emojis=company_config.get("use_emojis", False),
                company_info=company_config.get("company_info", "")
            )

            # Step 5: Process with AIBrain
            decision: BrainDecision = await self.brain.process(
                user_message=user_message,
                memory=memory,
                flow_intent=flow_intent,
                company_context=company_context,
                goal_tracker=goal_tracker
            )

            # Step 6: Update state based on decision
            result["response"] = decision.response
            result["sentiment"] = decision.sentiment.value
            result["user_intent"] = decision.user_intent

            # Handle handoff
            if decision.should_handoff:
                result["requires_human"] = True
                result["handoff_reason"] = decision.handoff_reason
                result["ai_enabled"] = False

                # Disable AI in database
                await db.set_conversation_ai(conversation_id, False)
                await db.set_lead_ai(lead_id, False)

                # Build complete lead info for notification
                lead_info_parts = []
                if memory.collected_data.get("nome"):
                    lead_info_parts.append(f"Nome: {memory.collected_data['nome']}")
                if memory.collected_data.get("produto"):
                    lead_info_parts.append(f"Produto: {memory.collected_data['produto']}")
                if memory.collected_data.get("cep"):
                    lead_info_parts.append(f"CEP: {memory.collected_data['cep']}")
                for key, value in memory.collected_data.items():
                    if key not in ["nome", "produto", "cep"] and value:
                        lead_info_parts.append(f"{key.title()}: {value}")

                # Send detailed handoff notification
                detailed_reason = f"{decision.handoff_reason}\n\n📋 Dados coletados:\n" + "\n".join(lead_info_parts) if lead_info_parts else decision.handoff_reason

                await notification_service.notify_handoff(
                    company_id=state.get("company_id"),
                    lead_id=lead_id,
                    lead_name=memory.collected_data.get("nome"),
                    reason=detailed_reason
                )
                logger.info(f"[INTELLIGENT] Handoff notification sent with data: {memory.collected_data}")

            # Update collected fields from extractions
            if decision.extractions:
                collected_fields = dict(state.get("collected_fields", {}) or {})
                for extraction in decision.extractions:
                    collected_fields[extraction.field] = extraction.value

                    # Special handling for name
                    if extraction.field.lower() == "nome":
                        result["lead_name"] = extraction.value
                        await db.update_lead_name(lead_id, extraction.value)
                    else:
                        await db.update_lead_field(lead_id, extraction.field, extraction.value)

                result["collected_fields"] = collected_fields

            # Track progress
            progress = goal_tracker.get_progress()
            result["qualification_score"] = progress.qualification_score

            # Check if flow is complete (all goals collected)
            all_goals_complete = all(g.collected for g in flow_intent.goals) if flow_intent.goals else False
            if flow_intent.is_complete() or all_goals_complete:
                result["flow_completed"] = True
                logger.info("[INTELLIGENT] All goals completed - notifying company")

                # Send notification with all collected data
                try:
                    await notification_service.notify_qualified_lead(
                        company_id=state.get("company_id"),
                        lead_id=lead_id,
                        lead_name=memory.collected_data.get("nome"),
                        qualification_score=progress.qualification_score,
                        qualification_data=memory.collected_data
                    )
                    logger.info(f"[INTELLIGENT] Notification sent with data: {memory.collected_data}")
                except Exception as notif_err:
                    logger.error(f"[INTELLIGENT] Failed to send notification: {notif_err}")

            # Step 7: Update memory with interaction
            memory.add_interaction(
                user_message=user_message,
                ai_response=decision.response,
                extracted_data={e.field: e.value for e in decision.extractions},
                sentiment=decision.sentiment,
                topics=[decision.user_intent] if decision.user_intent else []
            )

            # Update conversation state
            memory.update_conversation_state(
                current_topic=decision.next_goal,
                last_ai_action="responded",
                sentiment=decision.sentiment,
                user_intent=decision.user_intent
            )

            # Step 8: Save memory
            await self.memory_manager.save_memory(memory)

            logger.info(f"[INTELLIGENT] Decision: action={decision.action.value}, "
                       f"extractions={len(decision.extractions)}, "
                       f"handoff={decision.should_handoff}")

        except Exception as e:
            logger.error(f"[INTELLIGENT] Error: {e}", exc_info=True)
            result["response"] = "Desculpe, ocorreu um erro. Pode repetir?"
            result["error"] = str(e)

        return result

    async def _proposal_processor_node(self, state: AgentState) -> dict[str, Any]:
        """
        Proposal processor node - handles conversations when lead has active proposal.

        This specialized processor:
        1. Loads the active proposal
        2. Uses ProposalAgent for objection handling
        3. Detects buying signals
        4. Notifies company at critical moments
        5. Never offers discounts (company policy)
        """
        logger.info("[PROPOSAL] Processing with Proposal Agent (closing mode)")

        result = {}

        try:
            # Get identifiers
            lead_id = state.get("lead_id")
            conversation_id = state.get("conversation_id")
            company_config = state.get("company_config", {})
            company_id = state.get("company_id")
            proposta_ativa_id = state.get("proposta_ativa_id")

            # Get user message
            user_message = self._get_last_user_message(state)
            if not user_message:
                return {"response": "Como posso ajudar com a proposta?"}

            # Load the active proposal
            if not proposta_ativa_id:
                lead_data = state.get("lead_data", {})
                proposta_ativa_id = lead_data.get("proposta_ativa_id")

            if not proposta_ativa_id:
                # No active proposal - fallback to intelligent processor
                logger.warning("[PROPOSAL] No active proposal found, falling back")
                return await self._intelligent_processor_node(state)

            proposal = await proposal_service.get_proposal(proposta_ativa_id)
            if not proposal:
                logger.warning(f"[PROPOSAL] Proposal {proposta_ativa_id} not found")
                return await self._intelligent_processor_node(state)

            # Load memory
            try:
                memory = await self.memory_manager.load_memory(lead_id, conversation_id)
            except ValueError:
                memory = UnifiedMemory(
                    lead_id=lead_id,
                    conversation_id=conversation_id,
                    collected_data=state.get("lead_data", {})
                )

            # Process with Proposal Agent
            decision: ProposalDecision = await proposal_agent.process(
                user_message=user_message,
                proposal=proposal,
                memory=memory,
                company_name=company_config.get("company_name", "Empresa"),
                agent_name=company_config.get("agent_name", "Consultor")
            )

            # Set response
            result["response"] = decision.response

            # Handle handoff
            if decision.should_handoff:
                result["requires_human"] = True
                result["handoff_reason"] = decision.handoff_reason
                result["ai_enabled"] = False

                # Disable AI in database
                await db.set_conversation_ai(conversation_id, False)
                await db.set_lead_ai(lead_id, False)

                # Send handoff notification
                await notification_service.notify_handoff(
                    company_id=company_id,
                    lead_id=lead_id,
                    lead_name=memory.collected_data.get("nome"),
                    reason=decision.handoff_reason
                )
                logger.info(f"[PROPOSAL] Handoff requested: {decision.handoff_reason}")

            # Handle proposal actions
            if decision.proposal_action == "accept":
                await proposal_service.accept_proposal(proposal.id)
                logger.info(f"[PROPOSAL] Lead accepted proposal {proposal.id}")

            elif decision.proposal_action == "reject":
                # Don't immediately reject - the agent tried to save the deal
                # Mark as negotiating to give more chances
                await proposal_service.mark_negotiating(
                    proposal.id,
                    f"Lead indicated rejection intent: {user_message}"
                )
                logger.info(f"[PROPOSAL] Lead showing rejection signals for proposal {proposal.id}")

            # Send notifications for critical moments
            if decision.should_notify:
                await proposal_agent.notify_critical_moment(
                    company_id=company_id,
                    lead_id=lead_id,
                    proposal=proposal,
                    notification_message=decision.notification_message,
                    priority=decision.notification_priority
                )
                logger.info(f"[PROPOSAL] Critical moment notification sent")

            # Update memory
            memory.add_interaction(
                user_message=user_message,
                ai_response=decision.response,
                extracted_data={},
                sentiment=Sentiment.NEUTRAL,
                topics=["proposal_negotiation"]
            )
            await self.memory_manager.save_memory(memory)

            # Log signals
            if decision.signals:
                logger.info(f"[PROPOSAL] Signals detected: {[s.value for s in decision.signals]}")

            if decision.objection_detected:
                logger.info(f"[PROPOSAL] Objection detected: {decision.objection_detected.value}")

        except Exception as e:
            logger.error(f"[PROPOSAL] Error: {e}", exc_info=True)
            result["response"] = "Desculpe, ocorreu um erro. Posso ajudar com a proposta de outra forma?"
            result["error"] = str(e)

        return result

    async def _agent_node(self, state: AgentState) -> dict[str, Any]:
        """
        Agent node - ReAct agent for free conversation without flow.

        This is the fallback when no flow is configured.
        """
        logger.info("[AGENT] Processing free conversation")

        context = get_conversation_context(state)

        system_prompt = PromptBuilder.build_system_prompt(
            agent_name=context.get("agent_name", "Assistente"),
            agent_tone=context.get("agent_tone", "amigavel"),
            use_emojis=context.get("use_emojis", False),
            company_name=context.get("company_name", "Empresa"),
            company_info=context.get("company_info"),
            lead_name=context.get("lead_name"),
            lead_data=context.get("lead_data", {})
        )

        messages = [SystemMessage(content=system_prompt)]
        for msg in state.get("messages", []):
            messages.append(msg)

        try:
            response = await self.llm_with_tools.ainvoke(messages)
            return {
                "messages": [response],
                "last_ai_response_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"[AGENT] Error: {e}")
            return {
                "messages": [AIMessage(content="Desculpe, ocorreu um erro. Pode repetir?")],
                "error": str(e)
            }

    async def _response_formatter_node(self, state: AgentState) -> dict[str, Any]:
        """
        Response formatter node - formats and optionally converts to audio.
        """
        logger.info("[FORMATTER] Processing response")

        response = state.get("response", "")
        if not response:
            messages = state.get("messages", [])
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    response = msg.content
                    break

        if not response:
            response = "Como posso ajudar?"

        company_config = state.get("company_config", {})
        use_emojis = company_config.get("use_emojis", False)

        # Remove emojis if not enabled
        if not use_emojis:
            import re
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"
                "\U0001F300-\U0001F5FF"
                "\U0001F680-\U0001F6FF"
                "\U0001F700-\U0001F77F"
                "\U0001F780-\U0001F7FF"
                "\U0001F800-\U0001F8FF"
                "\U0001F900-\U0001F9FF"
                "\U0001FA00-\U0001FA6F"
                "\U0001FA70-\U0001FAFF"
                "\U00002702-\U000027B0"
                "\U0001F1E0-\U0001F1FF"
                "]+",
                flags=re.UNICODE
            )
            response = emoji_pattern.sub("", response).strip()

        # Handle audio generation
        response_type = state.get("node_response_type", "text")
        voice_id = state.get("node_voice_id")
        audio_base64 = None

        if response_type in ["audio", "both"] and response:
            # Try ElevenLabs first
            try:
                tts_service = ElevenLabsService(voice_id=voice_id) if voice_id else elevenlabs
                if tts_service.is_configured():
                    audio_base64 = await tts_service.get_audio_base64(response, voice_id)
                    if audio_base64:
                        logger.info("[FORMATTER] ElevenLabs audio generated")
            except Exception as e:
                logger.warning(f"[FORMATTER] ElevenLabs failed: {e}")

            # Fallback to OpenAI TTS
            if not audio_base64:
                try:
                    if openai_tts.is_configured():
                        audio_base64 = await openai_tts.get_audio_base64(
                            text=response,
                            voice=openai_tts.voice
                        )
                        if audio_base64:
                            logger.info("[FORMATTER] OpenAI TTS audio generated")
                except Exception as e:
                    logger.error(f"[FORMATTER] OpenAI TTS error: {e}")

            if not audio_base64:
                response_type = "text"

        return {
            "response": response,
            "response_type": response_type,
            "audio_base64": audio_base64,
            "last_message_at": datetime.utcnow().isoformat()
        }

    def _get_last_user_message(self, state: AgentState) -> Optional[str]:
        """Get the content of the last user message."""
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return msg.content
        return None

    async def invoke(
        self,
        state: AgentState,
        config: Optional[dict] = None
    ) -> dict[str, Any]:
        """Invoke the conversation graph."""
        thread_id = state.get("thread_id", "default")

        invoke_config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        if config:
            invoke_config.update(config)

        logger.info(f"[GRAPH] Invoking with thread_id={thread_id}")

        try:
            result = await self.graph.ainvoke(state, invoke_config)
            logger.info("[GRAPH] Completed successfully")
            return result
        except Exception as e:
            logger.error(f"[GRAPH] Error: {e}")
            raise


# ==================== LEGACY COMPATIBILITY ====================

# Keep the old ConversationGraph as an alias
class ConversationGraph(IntelligentConversationGraph):
    """Alias for backward compatibility."""
    pass


# Singleton instance
_graph_instance: Optional[IntelligentConversationGraph] = None


def get_graph() -> IntelligentConversationGraph:
    """Get or create the singleton ConversationGraph instance."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = IntelligentConversationGraph()
    return _graph_instance


async def invoke_agent(
    company: Company,
    lead: Lead,
    conversation: Conversation,
    user_message: str,
    message_history: list[dict[str, str]] = None
) -> dict[str, Any]:
    """
    Convenience function to invoke the agent.

    This function:
    1. Creates the initial state from models
    2. Adds the user message and history
    3. Invokes the graph
    4. Returns the result with response
    """
    graph = get_graph()

    # Parse flow config
    flow_config = None
    if company.flow_config:
        try:
            if isinstance(company.flow_config, dict):
                flow_config = company.flow_config
            else:
                flow_config = company.flow_config.model_dump()
        except Exception:
            flow_config = None

    # Create company config
    company_config = CompanyConfig(
        company_id=company.id,
        company_name=company.nome_empresa or company.empresa or "Empresa",
        agent_name=company.agent_name or "Assistente",
        agent_tone=company.agent_tone or "amigavel",
        use_emojis=company.use_emojis or False,
        company_info=company.informacoes_complementares or "",
        timezone="America/Sao_Paulo"
    )

    # Create initial state
    state = create_initial_state(
        company_id=company.id,
        lead_id=lead.id,
        conversation_id=conversation.id,
        thread_id=conversation.thread_id,
        lead_phone=lead.celular,
        company_config=company_config,
        lead_name=lead.nome,
        lead_data=lead.dados_coletados or {},
        flow_config=flow_config,
        current_node_id=conversation.current_node_id
    )

    # Add active proposal ID if present (for Proposal Agent routing)
    if lead.proposta_ativa_id:
        state["proposta_ativa_id"] = lead.proposta_ativa_id
        logger.info(f"[INVOKE] Lead has active proposal: {lead.proposta_ativa_id}")

    # Load context from conversation
    conv_context = conversation.context or {}

    # Restore state from context
    if conv_context.get("pending_field"):
        state["pending_field"] = conv_context.get("pending_field")
        state["pending_question"] = conv_context.get("pending_question")

    if conv_context.get("flow_completed"):
        state["flow_completed"] = True

    if conv_context.get("collected_fields"):
        state["collected_fields"] = conv_context.get("collected_fields", {})

    if conv_context.get("nodes_visited"):
        state["nodes_visited"] = conv_context.get("nodes_visited", [])

    if conv_context.get("qualification_stage"):
        state["qualification_stage"] = conv_context.get("qualification_stage", "initial")
        state["qualification_score"] = conv_context.get("qualification_score", 0)
        state["qualification_reasons"] = conv_context.get("qualification_reasons", [])

    # Update AI enabled status
    state["ai_enabled"] = conversation.ai_enabled and lead.ai_enabled

    # Check if AI is disabled
    if not state["ai_enabled"]:
        return {
            "response": None,
            "ai_enabled": False,
            "should_handoff": False
        }

    # Build message history
    messages = []
    if message_history:
        for msg in message_history[-10:]:
            if msg.get("role") == "user" or msg.get("direction") == "inbound":
                messages.append(HumanMessage(content=msg.get("content", "")))
            else:
                messages.append(AIMessage(content=msg.get("content", "")))

    messages.append(HumanMessage(content=user_message))
    state["messages"] = messages

    # Invoke the graph
    result = await graph.invoke(state)

    # Update database
    new_node_id = result.get("current_node_id")
    flow_completed = result.get("flow_completed", False)

    if new_node_id and new_node_id != conversation.current_node_id:
        await db.update_conversation_node(conversation.id, new_node_id)
    elif flow_completed:
        await db.update_conversation_node(conversation.id, None)

    # Sync collected fields
    collected_fields = result.get("collected_fields", {})
    if collected_fields:
        existing_data = lead.dados_coletados or {}
        merged_data = {**existing_data, **collected_fields}
        if merged_data != existing_data:
            await db.update_lead(lead.id, LeadUpdate(dados_coletados=merged_data))

    # Save context
    new_context = {
        "pending_field": result.get("pending_field"),
        "pending_question": result.get("pending_question"),
        "collected_fields": result.get("collected_fields", {}),
        "nodes_visited": result.get("nodes_visited", []),
        "flow_completed": flow_completed,
        "qualification_stage": result.get("qualification_stage", "initial"),
        "qualification_score": result.get("qualification_score", 0),
        "qualification_reasons": result.get("qualification_reasons", []),
        "user_intent": result.get("user_intent"),
        "sentiment": result.get("sentiment"),
        "conversation_summary": result.get("conversation_summary"),
        "requires_human": result.get("requires_human", False),
        "handoff_reason": result.get("handoff_reason"),
        "handoff_requested_at": result.get("handoff_requested_at"),
        "last_node_type": result.get("last_node_type"),
        "last_response_type": result.get("response_type", "text"),
        "updated_at": datetime.utcnow().isoformat()
    }
    await db.update_conversation_context(conversation.id, new_context)

    return {
        "response": result.get("response", ""),
        "response_type": result.get("response_type", "text"),
        "audio_base64": result.get("audio_base64"),
        "ai_enabled": result.get("ai_enabled", True),
        "should_handoff": result.get("requires_human", False),
        "handoff_reason": result.get("handoff_reason"),
        "current_node_id": result.get("current_node_id"),
        "lead_data": merge_lead_data(result, {}),
        "flow_completed": result.get("flow_completed", False),
        "pending_field": result.get("pending_field")
    }


class ConversationAgent:
    """Backward compatible wrapper for ConversationGraph."""

    def __init__(self):
        self._graph = get_graph()

    async def invoke(
        self,
        company: Company,
        lead: Lead,
        conversation: Conversation,
        user_message: str,
        message_history: list[dict[str, str]] = None
    ) -> dict[str, Any]:
        """Invoke the agent."""
        return await invoke_agent(
            company=company,
            lead=lead,
            conversation=conversation,
            user_message=user_message,
            message_history=message_history
        )


# Singleton for backward compatibility
agent = ConversationAgent()
