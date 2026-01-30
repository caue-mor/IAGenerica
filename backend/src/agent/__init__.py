"""
Agent module for IA-Generica.

This module provides the complete LangGraph-based conversation agent with:
- StateGraph for state management
- PostgreSQL checkpointing for persistence
- Unified memory system
- Goal-based flow interpretation
- Intelligent AI brain for natural responses
- Tool system for actions
- Flow executor for deterministic flows
- ReAct agent for free conversation

Main components:
- IntelligentConversationGraph: The new architecture LangGraph
- ConversationGraph: Alias for backward compatibility
- UnifiedMemory: Complete memory system
- FlowInterpreter: Converts flows to goals
- AIBrain: Intelligent response generation
- GoalTracker: Progress monitoring
- AgentState: TypedDict for state management
- PromptBuilder: Dynamic prompt generation
- Tools: Data collection, notification, scheduling, knowledge
"""

from .graph import (
    IntelligentConversationGraph,
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

# New architecture components
from .memory import (
    UnifiedMemory,
    MemoryManager,
    LeadProfile,
    KnownFacts,
    Interaction,
    ConversationState,
    GoalProgress,
    Sentiment,
    InteractionStyle
)

from .flow_interpreter import (
    FlowInterpreter,
    FlowIntent,
    ConversationGoal,
    FlowCondition,
    FlowAction,
    NotificationConfig,
    HandoffTrigger,
    GoalPriority,
    FieldCategory,
    interpret_flow,
    create_intent_from_dict
)

from .brain import (
    AIBrain,
    CompanyContext,
    BrainDecision,
    ResponseAction,
    create_brain
)

from .goal_tracker import (
    GoalTracker,
    GoalStatus,
    GoalUpdate,
    TriggeredCondition,
    ConditionResult,
    ExtractionResult
)

from .checkpointer import (
    SupabaseCheckpointSaver,
    create_checkpointer,
    get_migration_sql
)

# Agent Router
from .router import (
    AgentRouter,
    AgentType,
    RoutingContext,
    RoutingDecision,
    agent_router,
    route_conversation,
    should_use_proposal_agent
)

# Proposal Agent
from .proposal_agent import (
    ProposalAgent,
    ProposalSignal,
    ObjectionType,
    ProposalDecision,
    proposal_agent,
    create_proposal_agent
)

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
    # Main graph (new architecture)
    "IntelligentConversationGraph",
    "ConversationGraph",
    "ConversationAgent",
    "agent",
    "invoke_agent",
    "get_graph",

    # Memory system
    "UnifiedMemory",
    "MemoryManager",
    "LeadProfile",
    "KnownFacts",
    "Interaction",
    "ConversationState",
    "GoalProgress",
    "Sentiment",
    "InteractionStyle",

    # Flow interpreter
    "FlowInterpreter",
    "FlowIntent",
    "ConversationGoal",
    "FlowCondition",
    "FlowAction",
    "NotificationConfig",
    "HandoffTrigger",
    "GoalPriority",
    "FieldCategory",
    "interpret_flow",
    "create_intent_from_dict",

    # AI Brain
    "AIBrain",
    "CompanyContext",
    "BrainDecision",
    "ResponseAction",
    "create_brain",

    # Goal tracker
    "GoalTracker",
    "GoalStatus",
    "GoalUpdate",
    "TriggeredCondition",
    "ConditionResult",
    "ExtractionResult",

    # Checkpointer
    "SupabaseCheckpointSaver",
    "create_checkpointer",
    "get_migration_sql",

    # Agent Router
    "AgentRouter",
    "AgentType",
    "RoutingContext",
    "RoutingDecision",
    "agent_router",
    "route_conversation",
    "should_use_proposal_agent",

    # Proposal Agent
    "ProposalAgent",
    "ProposalSignal",
    "ObjectionType",
    "ProposalDecision",
    "proposal_agent",
    "create_proposal_agent",

    # State (legacy)
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
