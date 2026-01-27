"""
Agent module for IA-Generica.

This module provides the complete LangGraph-based conversation agent with:
- StateGraph for state management
- MemorySaver for checkpointing
- Tool system for actions
- Flow executor for deterministic flows
- ReAct agent for free conversation

Main components:
- ConversationGraph: The main LangGraph StateGraph
- AgentState: TypedDict for state management
- PromptBuilder: Dynamic prompt generation
- Tools: Data collection, notification, scheduling, knowledge
"""

from .graph import (
    ConversationGraph,
    ConversationAgent,
    agent,
    invoke_agent,
    get_graph
)

from .state import (
    AgentState,
    CompanyConfig,
    LeadData,
    FlowState,
    ToolResult,
    create_initial_state,
    merge_lead_data,
    get_conversation_context
)

from .prompts import PromptBuilder

from .tools import (
    all_tools,
    get_all_tools,
    get_tools_by_category,
    get_tool_descriptions,
    # Data collection tools
    data_collection_tools,
    update_field,
    update_lead_name,
    get_lead_data,
    update_lead_status,
    update_lead_email,
    # Notification tools
    notification_tools,
    transfer_to_human,
    notify_team,
    enable_ai,
    mark_as_spam,
    # Scheduling tools
    scheduling_tools,
    schedule_followup,
    schedule_visit,
    cancel_scheduled_event,
    # Knowledge tools
    knowledge_tools,
    search_knowledge,
    get_lead_history,
    get_company_info,
    get_available_statuses
)

__all__ = [
    # Main graph
    "ConversationGraph",
    "ConversationAgent",
    "agent",
    "invoke_agent",
    "get_graph",

    # State
    "AgentState",
    "CompanyConfig",
    "LeadData",
    "FlowState",
    "ToolResult",
    "create_initial_state",
    "merge_lead_data",
    "get_conversation_context",

    # Prompts
    "PromptBuilder",

    # Tools - lists
    "all_tools",
    "get_all_tools",
    "get_tools_by_category",
    "get_tool_descriptions",
    "data_collection_tools",
    "notification_tools",
    "scheduling_tools",
    "knowledge_tools",

    # Tools - individual
    "update_field",
    "update_lead_name",
    "get_lead_data",
    "update_lead_status",
    "update_lead_email",
    "transfer_to_human",
    "notify_team",
    "enable_ai",
    "mark_as_spam",
    "schedule_followup",
    "schedule_visit",
    "cancel_scheduled_event",
    "search_knowledge",
    "get_lead_history",
    "get_company_info",
    "get_available_statuses"
]
