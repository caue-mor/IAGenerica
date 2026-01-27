"""
Agent state definition for LangGraph with complete checkpointing support.

This module defines the AgentState TypedDict that maintains the complete
state of a conversation through the LangGraph StateGraph.
"""
from typing import TypedDict, Annotated, Sequence, Optional, Any, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from datetime import datetime


class CompanyConfig(TypedDict, total=False):
    """Company configuration for the agent."""
    company_id: int
    company_name: str
    agent_name: str
    agent_tone: str
    use_emojis: bool
    company_info: str
    industry: Optional[str]
    business_hours: Optional[str]
    timezone: str


class LeadData(TypedDict, total=False):
    """Lead data collected during conversation."""
    nome: Optional[str]
    email: Optional[str]
    celular: str
    interesse: Optional[str]
    cidade: Optional[str]
    dados_coletados: dict[str, Any]


class FlowState(TypedDict, total=False):
    """Flow execution state."""
    current_node_id: Optional[str]
    previous_node_id: Optional[str]
    start_node_id: Optional[str]
    nodes_visited: list[str]
    flow_started_at: Optional[str]
    flow_completed: bool


class ToolResult(TypedDict, total=False):
    """Result from a tool execution."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str]
    timestamp: str


class AgentState(TypedDict, total=False):
    """
    Complete agent state for LangGraph StateGraph.

    This state is checkpointed and persisted across conversation turns.
    Uses Annotated types for proper message accumulation.
    """

    # ==================== MESSAGES ====================
    # Messages are accumulated using add_messages reducer
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # ==================== IDENTIFIERS ====================
    company_id: int
    lead_id: int
    conversation_id: int
    thread_id: str  # Unique thread identifier for checkpointing

    # ==================== COMPANY CONTEXT ====================
    company_config: CompanyConfig

    # ==================== LEAD CONTEXT ====================
    lead_name: Optional[str]
    lead_phone: str
    lead_data: dict[str, Any]  # dados_coletados from database
    lead_email: Optional[str]

    # ==================== FLOW STATE ====================
    current_node_id: Optional[str]
    previous_node_id: Optional[str]
    flow_config: Optional[dict[str, Any]]  # Full flow JSON config
    flow_completed: bool
    nodes_visited: list[str]

    # ==================== COLLECTED DATA ====================
    collected_fields: dict[str, Any]  # Fields collected in current session
    pending_field: Optional[str]  # Field waiting for user input
    pending_question: Optional[str]  # Question waiting for answer

    # ==================== QUALIFICATION ====================
    qualification_stage: Literal[
        "initial",
        "qualifying",
        "qualified",
        "proposal",
        "negotiation",
        "closed_won",
        "closed_lost"
    ]
    qualification_score: int  # 0-100
    qualification_reasons: list[str]

    # ==================== AI CONTROL ====================
    ai_enabled: bool
    requires_human: bool
    handoff_reason: Optional[str]
    handoff_requested_at: Optional[str]

    # ==================== ROUTING ====================
    next_node: Literal[
        "router",
        "flow_executor",
        "agent",
        "tools",
        "humanizer",
        "end"
    ]

    # ==================== TOOL EXECUTION ====================
    last_tool_result: Optional[ToolResult]
    tool_results: list[ToolResult]  # History of tool executions
    pending_tool_calls: list[dict[str, Any]]

    # ==================== CONTEXT & METADATA ====================
    context: dict[str, Any]  # General context storage
    conversation_summary: Optional[str]  # AI-generated summary
    user_intent: Optional[str]  # Detected user intent
    sentiment: Optional[Literal["positive", "neutral", "negative"]]

    # ==================== RESPONSE ====================
    response: str  # Final response to send
    response_type: Literal["text", "template", "media"]
    media_url: Optional[str]

    # ==================== TIMESTAMPS ====================
    session_started_at: str
    last_message_at: str
    last_ai_response_at: Optional[str]

    # ==================== ERROR HANDLING ====================
    error: Optional[str]
    error_count: int
    retry_count: int


def create_initial_state(
    company_id: int,
    lead_id: int,
    conversation_id: int,
    thread_id: str,
    lead_phone: str,
    company_config: Optional[CompanyConfig] = None,
    lead_name: Optional[str] = None,
    lead_data: Optional[dict[str, Any]] = None,
    flow_config: Optional[dict[str, Any]] = None,
    current_node_id: Optional[str] = None
) -> AgentState:
    """
    Create initial agent state with default values.

    Args:
        company_id: Company ID from database
        lead_id: Lead ID from database
        conversation_id: Conversation ID from database
        thread_id: Unique thread ID for checkpointing
        lead_phone: Lead's phone number
        company_config: Company configuration
        lead_name: Lead's name if known
        lead_data: Previously collected lead data
        flow_config: Flow configuration JSON
        current_node_id: Current node in flow

    Returns:
        Initialized AgentState
    """
    now = datetime.utcnow().isoformat()

    return AgentState(
        # Messages
        messages=[],

        # Identifiers
        company_id=company_id,
        lead_id=lead_id,
        conversation_id=conversation_id,
        thread_id=thread_id,

        # Company context
        company_config=company_config or CompanyConfig(
            company_id=company_id,
            company_name="Empresa",
            agent_name="Assistente",
            agent_tone="amigavel",
            use_emojis=False,
            company_info="",
            timezone="America/Sao_Paulo"
        ),

        # Lead context
        lead_name=lead_name,
        lead_phone=lead_phone,
        lead_data=lead_data or {},
        lead_email=None,

        # Flow state
        current_node_id=current_node_id,
        previous_node_id=None,
        flow_config=flow_config,
        flow_completed=False,
        nodes_visited=[],

        # Collected data
        collected_fields={},
        pending_field=None,
        pending_question=None,

        # Qualification
        qualification_stage="initial",
        qualification_score=0,
        qualification_reasons=[],

        # AI control
        ai_enabled=True,
        requires_human=False,
        handoff_reason=None,
        handoff_requested_at=None,

        # Routing
        next_node="router",

        # Tool execution
        last_tool_result=None,
        tool_results=[],
        pending_tool_calls=[],

        # Context
        context={},
        conversation_summary=None,
        user_intent=None,
        sentiment=None,

        # Response
        response="",
        response_type="text",
        media_url=None,

        # Timestamps
        session_started_at=now,
        last_message_at=now,
        last_ai_response_at=None,

        # Error handling
        error=None,
        error_count=0,
        retry_count=0
    )


def merge_lead_data(state: AgentState, new_data: dict[str, Any]) -> dict[str, Any]:
    """
    Merge new data into existing lead data.

    Args:
        state: Current agent state
        new_data: New data to merge

    Returns:
        Merged lead data dictionary
    """
    existing = state.get("lead_data", {}) or {}
    collected = state.get("collected_fields", {}) or {}

    merged = {**existing, **collected, **new_data}

    # Remove None values
    return {k: v for k, v in merged.items() if v is not None}


def get_conversation_context(state: AgentState) -> dict[str, Any]:
    """
    Extract conversation context from state for prompts.

    Args:
        state: Current agent state

    Returns:
        Context dictionary for prompt building
    """
    company_config = state.get("company_config", {})

    return {
        "company_name": company_config.get("company_name", "Empresa"),
        "agent_name": company_config.get("agent_name", "Assistente"),
        "agent_tone": company_config.get("agent_tone", "amigavel"),
        "use_emojis": company_config.get("use_emojis", False),
        "company_info": company_config.get("company_info", ""),
        "lead_name": state.get("lead_name"),
        "lead_data": merge_lead_data(state, {}),
        "qualification_stage": state.get("qualification_stage", "initial"),
        "current_node_id": state.get("current_node_id"),
        "flow_completed": state.get("flow_completed", False),
        "requires_human": state.get("requires_human", False)
    }
