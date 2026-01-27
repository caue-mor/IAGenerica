"""
LangGraph StateGraph for conversation agent.

This module implements the complete conversation agent using LangGraph with:
- StateGraph for state management
- MemorySaver for checkpointing
- ToolNode for tool execution
- Conditional routing between flow executor and free agent
"""
import logging
from typing import Optional, Any, Literal
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    BaseMessage,
    ToolMessage
)
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from ..core.config import settings
from ..models import Company, Lead, LeadUpdate, Conversation, FlowConfig, FlowNode, NodeType
from ..services.database import db
from ..services.elevenlabs import elevenlabs, ElevenLabsService
from ..services.openai_tts import openai_tts, OpenAITTSService
from ..services.notification import notification_service
from ..flow.executor import FlowExecutor
from ..flow.humanizer import ConversationalQuestionHandler, HumanizerContext
from ..flow.extractor import extractor, ExtractionConfidence
from .intelligent_flow import intelligent_flow, intelligent_extractor, FlowContext
from .state import (
    AgentState,
    CompanyConfig,
    ToolResult,
    create_initial_state,
    merge_lead_data,
    get_conversation_context
)
from .prompts import PromptBuilder
from .tools import all_tools, get_all_tools

logger = logging.getLogger(__name__)


class ConversationGraph:
    """
    LangGraph-based conversation agent.

    This class orchestrates the conversation flow using a StateGraph with:
    - Router node: Decides between flow executor and free agent
    - Flow executor node: Handles deterministic flow nodes
    - Agent node: ReAct agent for free conversation
    - Tools node: Executes tool calls
    - Humanizer node: Humanizes responses before sending
    """

    def __init__(self):
        """Initialize the conversation graph."""
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.7
        )

        self.tools = get_all_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Memory-based checkpointer for persistence
        self.checkpointer = MemorySaver()

        # Build the graph
        self.graph = self._build_graph()

        logger.info(f"[GRAPH] Initialized with {len(self.tools)} tools and model {settings.OPENAI_MODEL}")

    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph StateGraph.

        Graph structure:
                            +-----------------+
                            |     router      |
                            +--------+--------+
                                    |
                    +---------------+---------------+
                    |                               |
            +-------v-------+               +-------v-------+
            | flow_executor |               |     agent     |
            +-------+-------+               +-------+-------+
                    |                               |
                    |                       +-------v-------+
                    |                       |    tools      |
                    |                       +-------+-------+
                    |                               |
                    +---------------+---------------+
                                    |
                            +-------v-------+
                            |   humanizer   |
                            +-------+-------+
                                    |
                            +-------v-------+
                            |      END      |
                            +---------------+
        """
        # Create the graph
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("router", self._router_node)
        graph.add_node("flow_executor", self._flow_executor_node)
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(self.tools))
        graph.add_node("humanizer", self._humanizer_node)

        # Set entry point
        graph.set_entry_point("router")

        # Add conditional edges from router
        graph.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "flow_executor": "flow_executor",
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
                "humanizer": "humanizer"
            }
        )

        # Tools always go back to agent
        graph.add_edge("tools", "agent")

        # Flow executor goes to humanizer
        graph.add_edge("flow_executor", "humanizer")

        # Humanizer ends the graph
        graph.add_edge("humanizer", END)

        # Compile with checkpointer
        compiled = graph.compile(checkpointer=self.checkpointer)

        logger.info("[GRAPH] Graph compiled successfully")
        return compiled

    def _router_node(self, state: AgentState) -> dict[str, Any]:
        """
        Router node - decides the execution path.

        Routes to:
        - flow_executor: If there's an active flow and current node
        - agent: For free conversation
        - end: If AI is disabled or requires human
        """
        logger.info(f"[ROUTER] Processing - ai_enabled={state.get('ai_enabled')}, "
                   f"requires_human={state.get('requires_human')}, "
                   f"current_node_id={state.get('current_node_id')}")

        # Check if AI is disabled or requires human
        if not state.get("ai_enabled", True):
            logger.info("[ROUTER] AI disabled - routing to end")
            return {"next_node": "end"}

        if state.get("requires_human", False):
            logger.info("[ROUTER] Requires human - routing to end")
            return {"next_node": "end"}

        # Check if there's an active flow
        flow_config = state.get("flow_config")
        current_node_id = state.get("current_node_id")

        if flow_config and current_node_id:
            logger.info(f"[ROUTER] Active flow found - routing to flow_executor (node: {current_node_id})")
            return {"next_node": "flow_executor"}

        # Check if flow should start
        if flow_config and not current_node_id:
            start_node = flow_config.get("start_node_id")
            if start_node:
                logger.info(f"[ROUTER] Starting flow - routing to flow_executor (start: {start_node})")
                return {
                    "next_node": "flow_executor",
                    "current_node_id": start_node
                }

        # Default to free agent
        logger.info("[ROUTER] No flow - routing to agent")
        return {"next_node": "agent"}

    def _route_decision(self, state: AgentState) -> str:
        """Determine the next node based on router output."""
        return state.get("next_node", "agent")

    def _should_use_tools(self, state: AgentState) -> str:
        """
        Determine if the agent should use tools.

        Checks the last message for tool calls.
        """
        messages = state.get("messages", [])
        if not messages:
            return "humanizer"

        last_message = messages[-1]

        # Check if the last message has tool calls
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            logger.info(f"[AGENT] Tool calls detected: {[tc['name'] for tc in last_message.tool_calls]}")
            return "tools"

        return "humanizer"

    async def _flow_executor_node(self, state: AgentState) -> dict[str, Any]:
        """
        Flow executor node - processes deterministic flow nodes.

        Handles:
        - GREETING: Send greeting message
        - QUESTION: Ask question and collect data
        - MESSAGE: Send templated message
        - CONDITION: Evaluate condition and branch
        - HANDOFF: Transfer to human
        - ACTION: Execute actions
        """
        current_node_id = state.get("current_node_id")
        flow_config = state.get("flow_config", {})

        logger.info(f"[FLOW] Processing node: {current_node_id}")

        if not current_node_id or not flow_config:
            logger.warning("[FLOW] No current node or flow config")
            return {"next_node": "agent"}

        # Get the current node from flow config
        node = self._get_flow_node(flow_config, current_node_id)

        if not node:
            logger.warning(f"[FLOW] Node {current_node_id} not found")
            return {"next_node": "agent"}

        # Track visited nodes
        nodes_visited = state.get("nodes_visited", []) or []
        nodes_visited = list(nodes_visited)  # Make a copy
        nodes_visited.append(current_node_id)

        # Initialize result
        result = {
            "nodes_visited": nodes_visited,
            "previous_node_id": current_node_id
        }

        # Get lead data for template processing
        lead_data = merge_lead_data(state, {})
        if state.get("lead_name"):
            lead_data["nome"] = state.get("lead_name")

        node_type = node.get("type")
        config = node.get("config", {})

        # Save node type for humanizer
        result["previous_node_type"] = node_type
        result["last_node_type"] = node_type

        # Save response type for audio/text output (from node config)
        result["node_response_type"] = config.get("response_type", "text")
        result["node_voice_id"] = config.get("voice_id")

        logger.info(f"[FLOW] Node type: {node_type}")

        # Detect question-type nodes (NOME, EMAIL, TELEFONE, etc.)
        # These are custom types that function like QUESTION nodes
        question_like_types = ["NOME", "EMAIL", "TELEFONE", "PHONE", "CPF", "CNPJ", "ENDERECO", "ADDRESS", "DATA", "DATE", "NUMERO", "NUMBER"]
        is_question_type = node_type in question_like_types or (config.get("pergunta") and config.get("campo_destino"))

        # Process based on node type
        if node_type == "GREETING":
            template_message = self._process_template(config.get("mensagem", "Ola!"), lead_data)
            user_message = self._get_last_user_message(state)

            # Use AI to generate a natural greeting that responds to user
            if user_message:
                flow_ctx = FlowContext(
                    current_node_id=current_node_id,
                    node_type=node_type,
                    node_config=config,
                    field_to_collect=None,
                    question_to_ask=None,
                    collected_fields=dict(state.get("collected_fields", {}) or {}),
                    lead_name=state.get("lead_name"),
                    company_info={
                        "agent_name": state.get("company_config", {}).get("agent_name", "Assistente"),
                        "nome_empresa": state.get("company_config", {}).get("company_name", "nossa empresa"),
                        "agent_tone": state.get("company_config", {}).get("agent_tone", "amigavel"),
                        "use_emojis": state.get("company_config", {}).get("use_emojis", False),
                    },
                    conversation_history=state.get("messages", [])[-5:]
                )
                result["response"] = await intelligent_flow.generate_greeting_response(
                    user_message=user_message,
                    flow_context=flow_ctx,
                    greeting_text=template_message
                )
            else:
                result["response"] = template_message

            result["current_node_id"] = node.get("next_node_id")

        elif node_type == "MESSAGE":
            message = self._process_template(config.get("mensagem", ""), lead_data)
            result["response"] = message
            result["current_node_id"] = node.get("next_node_id")

        elif node_type == "QUESTION" or is_question_type:
            # Handle QUESTION and question-like types (NOME, EMAIL, etc.)
            # Check if we're waiting for an answer
            pending_field = state.get("pending_field")
            user_message = self._get_last_user_message(state)
            campo_destino = config.get("campo_destino") or node_type.lower()

            logger.info(f"[FLOW] Question node: pending_field={pending_field}, campo_destino={campo_destino}, user_msg={user_message[:30] if user_message else None}")

            if pending_field == campo_destino and user_message:
                # Process the answer
                extracted = await self._extract_field_value(
                    user_message,
                    campo_destino,
                    config.get("tipo_campo", "text"),
                    config.get("opcoes")
                )

                logger.info(f"[FLOW] Extracted value: {extracted}")

                if extracted and extracted != "INVALID":
                    # Save the value
                    field_name = campo_destino
                    collected_fields = dict(state.get("collected_fields", {}) or {})
                    collected_fields[field_name] = extracted

                    # Special handling for name
                    if field_name.lower() == "nome":
                        result["lead_name"] = extracted
                        await db.update_lead_name(state["lead_id"], extracted)
                    else:
                        await db.update_lead_field(state["lead_id"], field_name, extracted)

                    result["collected_fields"] = collected_fields
                    result["pending_field"] = None
                    result["pending_question"] = None
                    result["current_node_id"] = node.get("next_node_id")

                    logger.info(f"[FLOW] Field saved: {field_name}={extracted}, next_node={result['current_node_id']}")

                    # Process next node immediately if it's not a question
                    next_node = self._get_flow_node(flow_config, node.get("next_node_id"))
                    if next_node and next_node.get("type") not in ["QUESTION"] + question_like_types:
                        # Recursively process next node
                        return await self._flow_executor_node({**state, **result})
                else:
                    # Invalid answer - use AI to generate natural response
                    logger.info(f"[FLOW] Extraction failed, using AI to generate response")

                    # Build flow context for intelligent response
                    flow_ctx = FlowContext(
                        current_node_id=current_node_id,
                        node_type=node_type,
                        node_config=config,
                        field_to_collect=campo_destino,
                        question_to_ask=config.get("pergunta"),
                        collected_fields=dict(state.get("collected_fields", {}) or {}),
                        lead_name=state.get("lead_name"),
                        company_info={
                            "agent_name": state.get("company_config", {}).get("agent_name", "Assistente"),
                            "nome_empresa": state.get("company_config", {}).get("company_name", "nossa empresa"),
                            "agent_tone": state.get("company_config", {}).get("agent_tone", "amigavel"),
                            "use_emojis": state.get("company_config", {}).get("use_emojis", False),
                            "informacoes_complementares": state.get("company_config", {}).get("extra_info", "")
                        },
                        conversation_history=state.get("messages", [])[-10:]
                    )

                    # Use AI to process the message and generate natural response
                    ai_result = await intelligent_flow.process_user_message(
                        user_message=user_message,
                        flow_context=flow_ctx,
                        state=state
                    )

                    # Check if AI extracted a valid value
                    if ai_result.get("is_valid") and ai_result.get("extracted_value"):
                        # AI successfully extracted the value
                        extracted = ai_result["extracted_value"]
                        field_name = campo_destino
                        collected_fields = dict(state.get("collected_fields", {}) or {})
                        collected_fields[field_name] = extracted

                        # Save the value
                        if field_name.lower() == "nome":
                            result["lead_name"] = extracted
                            await db.update_lead_name(state["lead_id"], extracted)
                        else:
                            await db.update_lead_field(state["lead_id"], field_name, extracted)

                        result["collected_fields"] = collected_fields
                        result["pending_field"] = None
                        result["pending_question"] = None
                        result["current_node_id"] = node.get("next_node_id")

                        # Use AI's natural response
                        result["response"] = ai_result.get("response", f"Perfeito! Registrei {field_name}.")

                        logger.info(f"[FLOW] AI extracted: {field_name}={extracted}")

                        # Process next node if not a question
                        next_node = self._get_flow_node(flow_config, node.get("next_node_id"))
                        if next_node and next_node.get("type") not in ["QUESTION"] + question_like_types:
                            return await self._flow_executor_node({**state, **result})
                    else:
                        # AI couldn't extract but generated natural response
                        result["response"] = ai_result.get("response", config.get("pergunta", "Pode me informar?"))
            else:
                # Ask the question
                question = self._process_template(config.get("pergunta", ""), lead_data)
                result["response"] = question
                result["pending_field"] = campo_destino
                result["pending_question"] = question
                logger.info(f"[FLOW] Asking question: {question}, pending_field={campo_destino}")

        elif node_type == "CONDITION":
            # Evaluate condition
            field = config.get("campo")
            operator = config.get("operador")
            expected = config.get("valor")
            actual = lead_data.get(field)

            condition_met = self._evaluate_condition(actual, operator, expected)

            if condition_met and node.get("true_node_id"):
                result["current_node_id"] = node.get("true_node_id")
            elif not condition_met and node.get("false_node_id"):
                result["current_node_id"] = node.get("false_node_id")
            else:
                result["current_node_id"] = node.get("next_node_id")

            # Process next node immediately
            return await self._flow_executor_node({**state, **result})

        elif node_type == "HANDOFF":
            message = self._process_template(
                config.get("mensagem_cliente", "Transferindo para atendimento humano."),
                lead_data
            )
            result["response"] = message
            result["requires_human"] = True
            result["handoff_reason"] = config.get("motivo", "Fluxo concluido")
            result["handoff_requested_at"] = datetime.utcnow().isoformat()
            result["ai_enabled"] = False
            result["flow_completed"] = True

            # Disable AI in database
            await db.set_conversation_ai(state["conversation_id"], False)
            await db.set_lead_ai(state["lead_id"], False)

            # Send handoff notification to team
            await notification_service.notify_handoff(
                company_id=state["company_id"],
                lead_id=state["lead_id"],
                lead_name=state.get("lead_name"),
                reason=config.get("motivo", "Fluxo concluido")
            )
            logger.info(f"[FLOW] Handoff notification sent for lead {state['lead_id']}")

        elif node_type == "ACTION":
            # Execute action (handled by FlowExecutor)
            executor = FlowExecutor(flow_config)
            action_result = await executor.execute_node(
                FlowNode(**node),
                lead_data
            )
            result["last_tool_result"] = ToolResult(
                tool_name="flow_action",
                success=action_result.get("action_result", {}).get("success", False),
                result=action_result,
                timestamp=datetime.utcnow().isoformat()
            )
            result["current_node_id"] = node.get("next_node_id")

            # Process next node immediately
            if result["current_node_id"]:
                return await self._flow_executor_node({**state, **result})

        elif node_type == "FOLLOWUP":
            # Schedule follow-up using the scheduler service
            from ..services.followup_scheduler import followup_scheduler, FollowupType

            delay_hours = config.get("delay_hours", 24)
            delay_minutes = config.get("delay_minutes")
            followup_message = self._process_template(
                config.get("mensagem", "Ola! Passando para saber se posso ajudar com mais alguma coisa."),
                lead_data
            )
            followup_type_str = config.get("tipo", "reminder")

            type_map = {
                "reminder": FollowupType.REMINDER,
                "reengagement": FollowupType.REENGAGEMENT,
                "qualification": FollowupType.QUALIFICATION,
                "proposal": FollowupType.PROPOSAL,
                "confirmation": FollowupType.CONFIRMATION,
                "custom": FollowupType.CUSTOM
            }

            scheduled_followup = await followup_scheduler.schedule_followup(
                company_id=state["company_id"],
                lead_id=state["lead_id"],
                message=followup_message,
                delay_hours=delay_hours if not delay_minutes else None,
                delay_minutes=delay_minutes,
                followup_type=type_map.get(followup_type_str, FollowupType.REMINDER),
                metadata={
                    "node_id": current_node_id,
                    "flow_scheduled": True
                }
            )

            logger.info(f"[FLOW] Follow-up scheduled: ID={scheduled_followup.id}, delay={delay_hours}h/{delay_minutes}m")

            # Optionally send confirmation message
            if config.get("confirmar", False):
                result["response"] = config.get("mensagem_confirmacao", "Entendido! Entrarei em contato novamente em breve.")

            result["current_node_id"] = node.get("next_node_id")

        logger.info(f"[FLOW] Result: response={result.get('response', '')[:50]}..., next_node={result.get('current_node_id')}")

        return result

    async def _agent_node(self, state: AgentState) -> dict[str, Any]:
        """
        Agent node - ReAct agent for free conversation.

        Uses the LLM with tools bound for intelligent conversation.
        """
        logger.info("[AGENT] Processing free conversation")

        # Build context for prompt
        context = get_conversation_context(state)

        # Build system prompt
        system_prompt = PromptBuilder.build_system_prompt(
            agent_name=context.get("agent_name", "Assistente"),
            agent_tone=context.get("agent_tone", "amigavel"),
            use_emojis=context.get("use_emojis", False),
            company_name=context.get("company_name", "Empresa"),
            company_info=context.get("company_info"),
            lead_name=context.get("lead_name"),
            lead_data=context.get("lead_data", {})
        )

        # Build messages for LLM
        messages = [SystemMessage(content=system_prompt)]

        # Add conversation history from state
        for msg in state.get("messages", []):
            messages.append(msg)

        logger.info(f"[AGENT] Invoking LLM with {len(messages)} messages")

        try:
            # Invoke LLM with tools
            response = await self.llm_with_tools.ainvoke(messages)

            logger.info(f"[AGENT] LLM response type: {type(response).__name__}")

            # Check for tool calls
            if hasattr(response, "tool_calls") and response.tool_calls:
                logger.info(f"[AGENT] Tool calls: {[tc['name'] for tc in response.tool_calls]}")

            return {
                "messages": [response],
                "last_ai_response_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"[AGENT] Error invoking LLM: {e}")
            return {
                "messages": [AIMessage(content="Desculpe, ocorreu um erro. Pode repetir?")],
                "error": str(e),
                "error_count": state.get("error_count", 0) + 1
            }

    async def _humanizer_node(self, state: AgentState) -> dict[str, Any]:
        """
        Humanizer node - CRITICAL component that transforms script into conversation.

        This node:
        - Humanizes flow responses using ConversationalQuestionHandler
        - Responds to what user said FIRST (empathy)
        - Then asks questions naturally (not reading scripts)
        - Applies emoji/formatting settings
        """
        logger.info("[HUMANIZER] Processing response")

        # Get response from state or last AI message
        response = state.get("response", "")
        node_type = state.get("previous_node_type") or state.get("last_node_type")
        pending_field = state.get("pending_field")

        if not response:
            messages = state.get("messages", [])
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    response = msg.content
                    break

        if not response:
            response = "Como posso ajudar?"

        # Get company config for humanization
        company_config = state.get("company_config", {})
        agent_name = company_config.get("agent_name", "Assistente")
        company_name = company_config.get("company_name", "nossa empresa")
        use_emojis = company_config.get("use_emojis", False)
        agent_tone = company_config.get("agent_tone", "friendly")

        # Get user message for context
        user_message = self._get_last_user_message(state) or ""

        # Humanize flow responses (questions, greetings, messages)
        should_humanize = (
            pending_field or  # It's a question waiting for answer
            node_type in ["QUESTION", "NOME", "EMAIL", "TELEFONE", "CIDADE", "GREETING", "MESSAGE"] or
            (state.get("pending_question") and response == state.get("pending_question"))
        )

        if should_humanize and response:
            try:
                # Create humanizer context
                humanizer = ConversationalQuestionHandler()
                context = humanizer.create_context(
                    lead_name=state.get("lead_name"),
                    agent_name=agent_name,
                    company_name=company_name,
                    tone="friendly" if agent_tone == "amigavel" else agent_tone
                )

                # Get conversation history for context
                history = []
                for msg in state.get("messages", [])[-4:]:
                    if isinstance(msg, HumanMessage):
                        history.append({"role": "user", "content": msg.content})
                    elif isinstance(msg, AIMessage):
                        history.append({"role": "assistant", "content": msg.content})

                # Humanize the response
                field_to_collect = pending_field or node_type.lower() if node_type else "resposta"
                retry_count = state.get("retry_count", 0)

                humanized = await humanizer.humanize(
                    user_message=user_message,
                    conversation_history=history,
                    field_to_collect=field_to_collect,
                    original_question=response,
                    context=context,
                    retry_count=retry_count,
                    skip_humanize=False
                )

                if humanized:
                    response = humanized
                    logger.info(f"[HUMANIZER] Humanized response: {response[:80]}...")

            except Exception as e:
                logger.error(f"[HUMANIZER] Error humanizing: {e}")
                # Keep original response on error

        # Apply emoji settings
        if not use_emojis:
            import re
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"  # emoticons
                "\U0001F300-\U0001F5FF"  # symbols & pictographs
                "\U0001F680-\U0001F6FF"  # transport & map symbols
                "\U0001F700-\U0001F77F"  # alchemical symbols
                "\U0001F780-\U0001F7FF"  # Geometric Shapes
                "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
                "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
                "\U0001FA00-\U0001FA6F"  # Chess Symbols
                "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
                "\U00002702-\U000027B0"  # Dingbats
                "\U0001F1E0-\U0001F1FF"  # Flags
                "]+",
                flags=re.UNICODE
            )
            response = emoji_pattern.sub("", response).strip()

        logger.info(f"[HUMANIZER] Final response: {response[:100]}...")

        # Check if audio response is requested
        response_type = state.get("node_response_type", "text")
        voice_id = state.get("node_voice_id")
        audio_base64 = None

        logger.info(f"[HUMANIZER] Response type from state: {response_type}, voice_id: {voice_id}")

        if response_type in ["audio", "both"] and response:
            # Try ElevenLabs first, then fallback to OpenAI TTS
            audio_generated = False

            # Try ElevenLabs
            try:
                tts_service = ElevenLabsService(voice_id=voice_id) if voice_id else elevenlabs

                logger.info(f"[HUMANIZER] Trying ElevenLabs...")

                if tts_service.is_configured():
                    audio_base64 = await tts_service.get_audio_base64(response, voice_id)
                    if audio_base64:
                        logger.info(f"[HUMANIZER] ElevenLabs audio generated ({len(audio_base64)} chars)")
                        audio_generated = True

            except Exception as e:
                logger.warning(f"[HUMANIZER] ElevenLabs failed: {e}")

            # Fallback to OpenAI TTS if ElevenLabs failed
            if not audio_generated:
                try:
                    logger.info(f"[HUMANIZER] Trying OpenAI TTS as fallback...")

                    if openai_tts.is_configured():
                        # Map voice_id to OpenAI voice or use default from config
                        openai_voice = openai_tts.voice  # Uses OPENAI_TTS_VOICE from settings
                        if voice_id and voice_id in openai_tts.VOICES:
                            openai_voice = voice_id

                        # Use gpt-4o-mini-tts with instructions for better voice control
                        audio_base64 = await openai_tts.get_audio_base64(
                            text=response,
                            voice=openai_voice,
                            instructions=openai_tts.instructions
                        )
                        logger.info(f"[HUMANIZER] Using OpenAI TTS: model={openai_tts.model}, voice={openai_voice}")
                        if audio_base64:
                            logger.info(f"[HUMANIZER] OpenAI TTS audio generated ({len(audio_base64)} chars)")
                            audio_generated = True
                        else:
                            logger.warning("[HUMANIZER] OpenAI TTS failed to generate audio")
                    else:
                        logger.warning("[HUMANIZER] OpenAI TTS not configured")

                except Exception as e:
                    logger.error(f"[HUMANIZER] OpenAI TTS error: {e}")

            # If both failed, fallback to text
            if not audio_generated:
                logger.warning("[HUMANIZER] All TTS services failed, falling back to text")
                response_type = "text"
        else:
            logger.info(f"[HUMANIZER] Skipping audio generation (response_type={response_type})")

        return {
            "response": response,
            "response_type": response_type,
            "audio_base64": audio_base64,
            "last_message_at": datetime.utcnow().isoformat()
        }

    def _get_flow_node(self, flow_config: dict, node_id: str) -> Optional[dict]:
        """Get a node from the flow config by ID."""
        if not flow_config or not node_id:
            return None

        nodes = flow_config.get("nodes", [])
        for node in nodes:
            if isinstance(node, dict) and node.get("id") == node_id:
                return node
        return None

    def _process_template(self, template: str, data: dict[str, Any]) -> str:
        """Replace placeholders in template with actual values."""
        result = template
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value) if value else "")
        return result

    def _get_last_user_message(self, state: AgentState) -> Optional[str]:
        """Get the content of the last user message."""
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return msg.content
        return None

    async def _extract_field_value(
        self,
        user_message: str,
        field_name: str,
        field_type: str,
        options: Optional[list] = None
    ) -> Optional[str]:
        """
        Extract a field value from user message using AI.

        Uses IntelligentExtractor which:
        - Understands natural language responses
        - Interprets context and intent
        - Extracts values even from non-standard formats
        """
        try:
            logger.info(f"[EXTRACT] Using AI to extract '{field_name}' from: {user_message[:50]}...")

            # Use intelligent extractor (LLM-based)
            extracted_value, is_valid, explanation = await intelligent_extractor.extract_field(
                user_message=user_message,
                field_name=field_name,
                field_type=field_type or "text",
                options=options
            )

            if is_valid and extracted_value:
                logger.info(f"[EXTRACT] AI extracted {field_name}: {extracted_value} ({explanation})")
                return extracted_value

            # Quick fallback for simple cases
            if field_name.lower() in ["nome", "cidade", "interesse", "tipo"]:
                # If message is short and looks like a direct answer
                cleaned = user_message.strip()
                if len(cleaned) >= 2 and len(cleaned.split()) <= 5:
                    # Remove common prefixes
                    prefixes = ["meu nome é", "me chamo", "sou o", "sou a", "pode me chamar de",
                               "moro em", "estou em", "é para", "seria para", "para"]
                    for prefix in prefixes:
                        if cleaned.lower().startswith(prefix):
                            cleaned = cleaned[len(prefix):].strip()
                            break

                    if cleaned and len(cleaned) >= 2:
                        logger.info(f"[EXTRACT] Quick fallback extracted {field_name}: {cleaned}")
                        return cleaned.title() if field_name.lower() == "nome" else cleaned

            logger.info(f"[EXTRACT] Could not extract {field_name} from message")
            return None

        except Exception as e:
            logger.error(f"[EXTRACT] Error: {e}")
            return None

    def _evaluate_condition(self, actual: Any, operator: str, expected: Any) -> bool:
        """Evaluate a condition."""
        if operator == "equals":
            return str(actual or "").lower() == str(expected or "").lower()
        elif operator == "not_equals":
            return str(actual or "").lower() != str(expected or "").lower()
        elif operator == "contains":
            return str(expected or "").lower() in str(actual or "").lower()
        elif operator == "not_contains":
            return str(expected or "").lower() not in str(actual or "").lower()
        elif operator == "greater_than":
            try:
                return float(actual) > float(expected)
            except (ValueError, TypeError):
                return False
        elif operator == "less_than":
            try:
                return float(actual) < float(expected)
            except (ValueError, TypeError):
                return False
        elif operator == "is_empty":
            return not actual or actual == ""
        elif operator == "is_not_empty":
            return actual and actual != ""
        elif operator == "exists":
            return actual is not None
        return False

    async def invoke(
        self,
        state: AgentState,
        config: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        Invoke the conversation graph.

        Args:
            state: The current agent state
            config: Optional configuration including thread_id for checkpointing

        Returns:
            Updated state with response
        """
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
            logger.info(f"[GRAPH] Completed successfully")
            return result
        except Exception as e:
            logger.error(f"[GRAPH] Error: {e}")
            raise


# ==================== CONVENIENCE FUNCTIONS ====================


# Singleton instance
_graph_instance: Optional[ConversationGraph] = None


def get_graph() -> ConversationGraph:
    """Get or create the singleton ConversationGraph instance."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = ConversationGraph()
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

    Args:
        company: Company model
        lead: Lead model
        conversation: Conversation model
        user_message: The user's message
        message_history: Optional list of previous messages

    Returns:
        Dictionary with response, ai_enabled, should_handoff, etc.
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

    # Load full context from conversation (Memory/FlowContext)
    conv_context = conversation.context or {}

    # Restore pending field state
    if conv_context.get("pending_field"):
        state["pending_field"] = conv_context.get("pending_field")
        state["pending_question"] = conv_context.get("pending_question")
        logger.info(f"[AGENT] Loaded pending_field from context: {state['pending_field']}")

    # Restore flow state
    if conv_context.get("flow_completed"):
        state["flow_completed"] = True
        logger.info(f"[AGENT] Flow was previously completed")

    # Restore collected_fields from context (session data)
    if conv_context.get("collected_fields"):
        state["collected_fields"] = conv_context.get("collected_fields", {})
        logger.info(f"[AGENT] Loaded collected_fields from context: {list(state['collected_fields'].keys())}")

    # Restore nodes_visited for flow tracking
    if conv_context.get("nodes_visited"):
        state["nodes_visited"] = conv_context.get("nodes_visited", [])
        logger.info(f"[AGENT] Loaded nodes_visited from context: {len(state['nodes_visited'])} nodes")

    # Restore qualification state
    if conv_context.get("qualification_stage"):
        state["qualification_stage"] = conv_context.get("qualification_stage", "initial")
        state["qualification_score"] = conv_context.get("qualification_score", 0)
        state["qualification_reasons"] = conv_context.get("qualification_reasons", [])
        logger.info(f"[AGENT] Loaded qualification: stage={state['qualification_stage']}, score={state['qualification_score']}")

    # Restore additional context
    if conv_context.get("user_intent"):
        state["user_intent"] = conv_context.get("user_intent")
    if conv_context.get("sentiment"):
        state["sentiment"] = conv_context.get("sentiment")
    if conv_context.get("conversation_summary"):
        state["conversation_summary"] = conv_context.get("conversation_summary")

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
        for msg in message_history[-10:]:  # Last 10 messages
            if msg.get("role") == "user" or msg.get("direction") == "inbound":
                messages.append(HumanMessage(content=msg.get("content", "")))
            else:
                messages.append(AIMessage(content=msg.get("content", "")))

    # Add current user message
    messages.append(HumanMessage(content=user_message))

    state["messages"] = messages

    # Invoke the graph
    result = await graph.invoke(state)

    # Update conversation node in database
    # IMPORTANT: Don't save None - keep the current node to avoid resetting on restart
    new_node_id = result.get("current_node_id")
    flow_completed = result.get("flow_completed", False)

    if new_node_id and new_node_id != conversation.current_node_id:
        # Only update if we have a valid new node
        await db.update_conversation_node(conversation.id, new_node_id)
        logger.info(f"[AGENT] Updated current_node_id: {new_node_id}")
    elif flow_completed:
        # Flow explicitly completed - we can clear the node
        await db.update_conversation_node(conversation.id, None)
        logger.info(f"[AGENT] Flow completed, cleared current_node_id")
    else:
        # Keep the current node (don't reset to None)
        logger.info(f"[AGENT] Keeping current_node_id: {conversation.current_node_id}")

    # Sync collected_fields to lead.dados_coletados for persistence
    collected_fields = result.get("collected_fields", {})
    if collected_fields:
        # Merge with existing lead data
        existing_data = lead.dados_coletados or {}
        merged_data = {**existing_data, **collected_fields}

        # Update lead in database with merged data
        if merged_data != existing_data:
            await db.update_lead(lead.id, LeadUpdate(dados_coletados=merged_data))
            logger.info(f"[AGENT] Synced collected_fields to lead.dados_coletados: {list(collected_fields.keys())}")

    # Save complete flow context to conversation (Memory/FlowContext)
    new_context = {
        # Flow state
        "pending_field": result.get("pending_field"),
        "pending_question": result.get("pending_question"),
        "collected_fields": result.get("collected_fields", {}),
        "nodes_visited": result.get("nodes_visited", []),
        "flow_completed": flow_completed,

        # Qualification state
        "qualification_stage": result.get("qualification_stage", "initial"),
        "qualification_score": result.get("qualification_score", 0),
        "qualification_reasons": result.get("qualification_reasons", []),

        # Conversation context
        "user_intent": result.get("user_intent"),
        "sentiment": result.get("sentiment"),
        "conversation_summary": result.get("conversation_summary"),

        # Handoff state
        "requires_human": result.get("requires_human", False),
        "handoff_reason": result.get("handoff_reason"),
        "handoff_requested_at": result.get("handoff_requested_at"),

        # Metadata
        "last_node_type": result.get("last_node_type"),
        "last_response_type": result.get("response_type", "text"),
        "updated_at": datetime.utcnow().isoformat()
    }
    await db.update_conversation_context(conversation.id, new_context)
    logger.info(f"[AGENT] Saved full context: pending_field={new_context.get('pending_field')}, "
               f"collected={len(new_context.get('collected_fields', {}))}, "
               f"visited={len(new_context.get('nodes_visited', []))}, "
               f"flow_completed={flow_completed}")

    # Return formatted result
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


# Backward compatibility - agent instance
class ConversationAgent:
    """
    Backward compatible wrapper for ConversationGraph.

    This class maintains the old API while using the new graph internally.
    """

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
        """Invoke the agent (wrapper for invoke_agent)."""
        return await invoke_agent(
            company=company,
            lead=lead,
            conversation=conversation,
            user_message=user_message,
            message_history=message_history
        )


# Singleton for backward compatibility
agent = ConversationAgent()
