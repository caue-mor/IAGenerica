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
from ..models import Company, Lead, Conversation, FlowConfig, FlowNode, NodeType
from ..services.database import db
from ..flow.executor import FlowExecutor
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

        logger.info(f"[FLOW] Node type: {node_type}")

        # Detect question-type nodes (NOME, EMAIL, TELEFONE, etc.)
        # These are custom types that function like QUESTION nodes
        question_like_types = ["NOME", "EMAIL", "TELEFONE", "PHONE", "CPF", "CNPJ", "ENDERECO", "ADDRESS", "DATA", "DATE", "NUMERO", "NUMBER"]
        is_question_type = node_type in question_like_types or (config.get("pergunta") and config.get("campo_destino"))

        # Process based on node type
        if node_type == "GREETING":
            message = self._process_template(config.get("mensagem", "Ola!"), lead_data)
            result["response"] = message
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
                    # Invalid answer, ask again
                    result["response"] = f"Desculpe, nao entendi. {config.get('pergunta', 'Pode repetir?')}"
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
            # Schedule follow-up
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
        Humanizer node - final processing before response.

        This node:
        - Extracts the final response from messages or state
        - Applies any final formatting
        - Ensures response is ready for delivery
        """
        logger.info("[HUMANIZER] Processing response")

        # Get response from state or last AI message
        response = state.get("response", "")

        if not response:
            messages = state.get("messages", [])
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    response = msg.content
                    break

        if not response:
            response = "Como posso ajudar?"

        # Apply emoji settings
        company_config = state.get("company_config", {})
        if not company_config.get("use_emojis", False):
            # Simple emoji removal (basic patterns)
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

        return {
            "response": response,
            "response_type": "text",
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
        """Extract a field value from user message using LLM."""
        prompt = PromptBuilder.build_extraction_prompt(
            user_message=user_message,
            field_name=field_name,
            field_type=field_type,
            options=options
        )

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            extracted = response.content.strip()
            return extracted if extracted != "INVALID" else None
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

    # Load pending_field from conversation context
    conv_context = conversation.context or {}
    if conv_context.get("pending_field"):
        state["pending_field"] = conv_context.get("pending_field")
        state["pending_question"] = conv_context.get("pending_question")
        logger.info(f"[AGENT] Loaded pending_field from context: {state['pending_field']}")

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
    new_node_id = result.get("current_node_id")
    if new_node_id != conversation.current_node_id:
        await db.update_conversation_node(conversation.id, new_node_id)

    # Save pending_field to conversation context
    new_context = {
        "pending_field": result.get("pending_field"),
        "pending_question": result.get("pending_question"),
        "collected_fields": result.get("collected_fields", {})
    }
    await db.update_conversation_context(conversation.id, new_context)
    logger.info(f"[AGENT] Saved context: pending_field={new_context.get('pending_field')}")

    # Return formatted result
    return {
        "response": result.get("response", ""),
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
