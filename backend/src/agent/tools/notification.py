"""
Notification tools for the agent.

Tools for handling transfers to human agents and team notifications.
"""
import logging
from typing import Any, Optional
from datetime import datetime
from langchain_core.tools import tool
from ...services.database import db

logger = logging.getLogger(__name__)


@tool
async def transfer_to_human(
    conversation_id: int,
    lead_id: int,
    reason: str,
    message_to_customer: str = "Vou transferir voce para um de nossos atendentes. Aguarde um momento.",
    priority: str = "normal"
) -> dict[str, Any]:
    """
    Transfer the conversation to a human agent.
    Use this when the customer needs human assistance, requests to speak with an agent,
    or when the AI cannot adequately handle the request.

    Args:
        conversation_id: The conversation ID in the database
        lead_id: The lead ID in the database
        reason: Reason for the transfer (e.g., "cliente solicitou", "problema complexo")
        message_to_customer: Message to send to the customer before transfer
        priority: Transfer priority - "low", "normal", "high", or "urgent"

    Returns:
        Dictionary with transfer confirmation and details

    Example:
        transfer_to_human(
            conversation_id=456,
            lead_id=123,
            reason="Cliente solicitou falar com vendedor",
            priority="high"
        )
    """
    try:
        logger.info(f"[TOOL] transfer_to_human - conv_id={conversation_id}, lead_id={lead_id}, reason={reason}")

        # Disable AI for the conversation
        await db.set_conversation_ai(conversation_id, False)

        # Disable AI for the lead
        await db.set_lead_ai(lead_id, False)

        # Save transfer info in lead data
        await db.update_lead_field(lead_id, "transfer_reason", reason)
        await db.update_lead_field(lead_id, "transfer_priority", priority)
        await db.update_lead_field(lead_id, "transfer_requested_at", datetime.utcnow().isoformat())

        logger.info(f"[TOOL] transfer_to_human - SUCCESS - AI disabled for conv {conversation_id}")

        return {
            "success": True,
            "message_to_customer": message_to_customer,
            "reason": reason,
            "priority": priority,
            "ai_disabled": True,
            "conversation_id": conversation_id,
            "lead_id": lead_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"[TOOL] transfer_to_human - ERROR - {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "conversation_id": conversation_id,
            "lead_id": lead_id
        }


@tool
async def notify_team(
    company_id: int,
    lead_id: int,
    notification_type: str,
    message: str,
    priority: str = "normal",
    data: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Send notification to the team about a lead or conversation.
    Use this to alert the team about important events like hot leads, urgent requests, etc.

    Args:
        company_id: The company ID
        lead_id: The lead ID
        notification_type: Type of notification - "new_lead", "hot_lead", "urgent", "follow_up", "closed"
        message: Notification message to send to the team
        priority: Notification priority - "low", "normal", "high", "urgent"
        data: Optional additional data to include in the notification

    Returns:
        Dictionary with notification confirmation

    Example:
        notify_team(
            company_id=1,
            lead_id=123,
            notification_type="hot_lead",
            message="Cliente interessado em fechar negocio hoje!",
            priority="urgent"
        )
    """
    try:
        logger.info(f"[TOOL] notify_team - company={company_id}, lead={lead_id}, type={notification_type}")

        # Save notification in lead data
        notification_info = {
            "type": notification_type,
            "message": message,
            "priority": priority,
            "created_at": datetime.utcnow().isoformat(),
            "data": data
        }

        await db.update_lead_field(lead_id, f"notification_{notification_type}", notification_info)

        # TODO: In production, implement actual notification delivery:
        # - Send email to team
        # - Send webhook to external systems
        # - Push notification to mobile app
        # - Post to Slack/Discord channel

        logger.info(f"[TOOL] notify_team - SUCCESS - {notification_type} notification created")

        return {
            "success": True,
            "message": f"Notificacao '{notification_type}' registrada para lead {lead_id}.",
            "notification_type": notification_type,
            "priority": priority,
            "company_id": company_id,
            "lead_id": lead_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"[TOOL] notify_team - ERROR - {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "company_id": company_id,
            "lead_id": lead_id
        }


@tool
async def enable_ai(conversation_id: int, lead_id: int) -> dict[str, Any]:
    """
    Re-enable AI for a conversation.
    Use this when a human agent wants to return control to the AI assistant.

    Args:
        conversation_id: The conversation ID
        lead_id: The lead ID

    Returns:
        Dictionary with confirmation

    Example:
        enable_ai(conversation_id=456, lead_id=123)
    """
    try:
        logger.info(f"[TOOL] enable_ai - conv_id={conversation_id}, lead_id={lead_id}")

        await db.set_conversation_ai(conversation_id, True)
        await db.set_lead_ai(lead_id, True)

        # Clear transfer info
        await db.update_lead_field(lead_id, "transfer_reason", None)
        await db.update_lead_field(lead_id, "ai_resumed_at", datetime.utcnow().isoformat())

        logger.info(f"[TOOL] enable_ai - SUCCESS - AI re-enabled")

        return {
            "success": True,
            "message": "IA reativada para esta conversa.",
            "conversation_id": conversation_id,
            "lead_id": lead_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"[TOOL] enable_ai - ERROR - {str(e)}")
        return {
            "success": False,
            "error": f"Erro ao reativar IA: {str(e)}",
            "conversation_id": conversation_id,
            "lead_id": lead_id
        }


@tool
async def mark_as_spam(
    conversation_id: int,
    lead_id: int,
    reason: str = "spam"
) -> dict[str, Any]:
    """
    Mark a conversation as spam and disable AI.
    Use this when the lead is clearly spam, irrelevant, or abusive.

    Args:
        conversation_id: The conversation ID
        lead_id: The lead ID
        reason: Reason for marking as spam

    Returns:
        Dictionary with confirmation

    Example:
        mark_as_spam(conversation_id=456, lead_id=123, reason="mensagens irrelevantes")
    """
    try:
        logger.info(f"[TOOL] mark_as_spam - conv_id={conversation_id}, lead_id={lead_id}, reason={reason}")

        # Disable AI
        await db.set_conversation_ai(conversation_id, False)
        await db.set_lead_ai(lead_id, False)

        # Mark as spam in lead data
        await db.update_lead_field(lead_id, "is_spam", True)
        await db.update_lead_field(lead_id, "spam_reason", reason)
        await db.update_lead_field(lead_id, "marked_spam_at", datetime.utcnow().isoformat())

        logger.info(f"[TOOL] mark_as_spam - SUCCESS - marked as spam")

        return {
            "success": True,
            "message": "Lead marcado como spam.",
            "reason": reason,
            "conversation_id": conversation_id,
            "lead_id": lead_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"[TOOL] mark_as_spam - ERROR - {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "conversation_id": conversation_id,
            "lead_id": lead_id
        }


# Export tools list
notification_tools = [
    transfer_to_human,
    notify_team,
    enable_ai,
    mark_as_spam
]

__all__ = [
    "notification_tools",
    "transfer_to_human",
    "notify_team",
    "enable_ai",
    "mark_as_spam"
]
