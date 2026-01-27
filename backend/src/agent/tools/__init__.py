"""
Agent tools module.

This module exports all available tools for the LangGraph agent.
Tools are organized by category:

- data_collection: Tools for collecting and updating lead information
- notification: Tools for handling transfers and team notifications
- scheduling: Tools for scheduling follow-ups and visits
- knowledge: Tools for searching knowledge base and retrieving information
"""

from .data_collection import (
    data_collection_tools,
    update_field,
    update_lead_name,
    get_lead_data,
    update_lead_status,
    update_lead_email
)

from .notification import (
    notification_tools,
    transfer_to_human,
    notify_team,
    enable_ai,
    mark_as_spam
)

from .scheduling import (
    scheduling_tools,
    schedule_followup,
    schedule_visit,
    cancel_scheduled_event
)

from .knowledge import (
    knowledge_tools,
    search_knowledge,
    get_lead_history,
    get_company_info,
    get_available_statuses
)

# Combine all tools into a single list
all_tools = (
    data_collection_tools +
    notification_tools +
    scheduling_tools +
    knowledge_tools
)


def get_all_tools():
    """
    Get all available tools as a list.

    Returns:
        List of all tool functions
    """
    return all_tools


def get_tools_by_category(category: str):
    """
    Get tools filtered by category.

    Args:
        category: Category name - "data_collection", "notification", "scheduling", "knowledge"

    Returns:
        List of tools in the specified category
    """
    categories = {
        "data_collection": data_collection_tools,
        "notification": notification_tools,
        "scheduling": scheduling_tools,
        "knowledge": knowledge_tools
    }
    return categories.get(category, [])


def get_tool_descriptions():
    """
    Get descriptions of all available tools.

    Returns:
        Dictionary mapping tool names to their descriptions
    """
    descriptions = {}
    for tool in all_tools:
        descriptions[tool.name] = tool.description
    return descriptions


__all__ = [
    # Tool lists by category
    "data_collection_tools",
    "notification_tools",
    "scheduling_tools",
    "knowledge_tools",
    "all_tools",

    # Helper functions
    "get_all_tools",
    "get_tools_by_category",
    "get_tool_descriptions",

    # Data collection tools
    "update_field",
    "update_lead_name",
    "get_lead_data",
    "update_lead_status",
    "update_lead_email",

    # Notification tools
    "transfer_to_human",
    "notify_team",
    "enable_ai",
    "mark_as_spam",

    # Scheduling tools
    "schedule_followup",
    "schedule_visit",
    "cancel_scheduled_event",

    # Knowledge tools
    "search_knowledge",
    "get_lead_history",
    "get_company_info",
    "get_available_statuses"
]
