"""
Data collection tools for the agent.

Tools for collecting and updating lead information during conversations.
"""
import logging
from typing import Any, Optional
from datetime import datetime
from langchain_core.tools import tool
from ...services.database import db

logger = logging.getLogger(__name__)


@tool
async def update_field(lead_id: int, field_name: str, value: Any) -> dict[str, Any]:
    """
    Update a specific field in lead's collected data (dados_coletados).
    Use this to save any information collected from the customer.

    Args:
        lead_id: The lead ID in the database
        field_name: Name of the field to update (e.g., 'interesse', 'cidade', 'orcamento')
        value: Value to save (can be string, number, or boolean)

    Returns:
        Dictionary with success status and updated data

    Example:
        update_field(lead_id=123, field_name="interesse", value="comprar")
    """
    try:
        logger.info(f"[TOOL] update_field - lead_id={lead_id}, field={field_name}, value={value}")

        lead = await db.update_lead_field(lead_id, field_name, value)

        if lead:
            logger.info(f"[TOOL] update_field - SUCCESS - {field_name}={value}")
            return {
                "success": True,
                "message": f"Campo '{field_name}' atualizado com sucesso.",
                "field_name": field_name,
                "value": value,
                "lead_id": lead_id,
                "timestamp": datetime.utcnow().isoformat()
            }

        logger.warning(f"[TOOL] update_field - Lead {lead_id} not found")
        return {
            "success": False,
            "error": f"Lead {lead_id} nao encontrado.",
            "lead_id": lead_id
        }
    except Exception as e:
        logger.error(f"[TOOL] update_field - ERROR - {str(e)}")
        return {
            "success": False,
            "error": f"Erro ao atualizar campo: {str(e)}",
            "lead_id": lead_id
        }


@tool
async def update_lead_name(lead_id: int, name: str) -> dict[str, Any]:
    """
    Update the lead's name.
    Use this when the customer provides their name during conversation.

    Args:
        lead_id: The lead ID in the database
        name: The customer's full name

    Returns:
        Dictionary with success status and confirmation

    Example:
        update_lead_name(lead_id=123, name="Maria Silva")
    """
    try:
        logger.info(f"[TOOL] update_lead_name - lead_id={lead_id}, name={name}")

        # Clean the name
        clean_name = name.strip().title()

        lead = await db.update_lead_name(lead_id, clean_name)

        if lead:
            logger.info(f"[TOOL] update_lead_name - SUCCESS - {clean_name}")
            return {
                "success": True,
                "message": f"Nome atualizado para '{clean_name}'.",
                "name": clean_name,
                "lead_id": lead_id,
                "timestamp": datetime.utcnow().isoformat()
            }

        logger.warning(f"[TOOL] update_lead_name - Lead {lead_id} not found")
        return {
            "success": False,
            "error": f"Lead {lead_id} nao encontrado.",
            "lead_id": lead_id
        }
    except Exception as e:
        logger.error(f"[TOOL] update_lead_name - ERROR - {str(e)}")
        return {
            "success": False,
            "error": f"Erro ao atualizar nome: {str(e)}",
            "lead_id": lead_id
        }


@tool
async def get_lead_data(lead_id: int) -> dict[str, Any]:
    """
    Get all collected data for a lead.
    Use this to check what information has already been collected.

    Args:
        lead_id: The lead ID in the database

    Returns:
        Dictionary with lead's name, phone, email, and all collected data

    Example:
        data = get_lead_data(lead_id=123)
        # Returns: {"nome": "Maria", "celular": "11999...", "dados_coletados": {...}}
    """
    try:
        logger.info(f"[TOOL] get_lead_data - lead_id={lead_id}")

        lead = await db.get_lead(lead_id)

        if lead:
            data = {
                "success": True,
                "lead_id": lead_id,
                "nome": lead.nome,
                "celular": lead.celular,
                "email": lead.email,
                "dados_coletados": lead.dados_coletados or {},
                "ai_enabled": lead.ai_enabled,
                "origem": lead.origem,
                "created_at": lead.created_at.isoformat() if lead.created_at else None
            }
            logger.info(f"[TOOL] get_lead_data - SUCCESS - found lead data")
            return data

        logger.warning(f"[TOOL] get_lead_data - Lead {lead_id} not found")
        return {
            "success": False,
            "error": f"Lead {lead_id} nao encontrado.",
            "lead_id": lead_id
        }
    except Exception as e:
        logger.error(f"[TOOL] get_lead_data - ERROR - {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "lead_id": lead_id
        }


@tool
async def update_lead_status(lead_id: int, status_id: int, reason: Optional[str] = None) -> dict[str, Any]:
    """
    Update the lead's status in the kanban pipeline.
    Use this to move a lead to a different stage (e.g., qualified, proposal, closed).

    Args:
        lead_id: The lead ID in the database
        status_id: The new status ID to move the lead to
        reason: Optional reason for the status change

    Returns:
        Dictionary with success status and confirmation

    Example:
        update_lead_status(lead_id=123, status_id=2, reason="Lead qualificado")
    """
    try:
        logger.info(f"[TOOL] update_lead_status - lead_id={lead_id}, status_id={status_id}, reason={reason}")

        lead = await db.update_lead_status(lead_id, status_id)

        if lead:
            logger.info(f"[TOOL] update_lead_status - SUCCESS - moved to status {status_id}")

            # Also save the reason in dados_coletados if provided
            if reason:
                await db.update_lead_field(lead_id, "status_change_reason", reason)

            return {
                "success": True,
                "message": f"Status do lead atualizado para {status_id}.",
                "lead_id": lead_id,
                "new_status_id": status_id,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }

        logger.warning(f"[TOOL] update_lead_status - Lead {lead_id} not found")
        return {
            "success": False,
            "error": f"Lead {lead_id} nao encontrado.",
            "lead_id": lead_id
        }
    except Exception as e:
        logger.error(f"[TOOL] update_lead_status - ERROR - {str(e)}")
        return {
            "success": False,
            "error": f"Erro ao atualizar status: {str(e)}",
            "lead_id": lead_id
        }


@tool
async def update_lead_email(lead_id: int, email: str) -> dict[str, Any]:
    """
    Update the lead's email address.
    Use this when the customer provides their email.

    Args:
        lead_id: The lead ID in the database
        email: The customer's email address

    Returns:
        Dictionary with success status and confirmation

    Example:
        update_lead_email(lead_id=123, email="maria@email.com")
    """
    try:
        logger.info(f"[TOOL] update_lead_email - lead_id={lead_id}, email={email}")

        # Basic email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        clean_email = email.strip().lower()

        if not re.match(email_pattern, clean_email):
            return {
                "success": False,
                "error": "Email invalido.",
                "lead_id": lead_id
            }

        # Get current lead and update
        lead = await db.get_lead(lead_id)
        if not lead:
            return {
                "success": False,
                "error": f"Lead {lead_id} nao encontrado.",
                "lead_id": lead_id
            }

        # Update using the update method
        from ...models import LeadUpdate
        updated_lead = await db.update_lead(lead_id, LeadUpdate(email=clean_email))

        if updated_lead:
            logger.info(f"[TOOL] update_lead_email - SUCCESS - {clean_email}")
            return {
                "success": True,
                "message": f"Email atualizado para '{clean_email}'.",
                "email": clean_email,
                "lead_id": lead_id,
                "timestamp": datetime.utcnow().isoformat()
            }

        return {
            "success": False,
            "error": "Erro ao atualizar email.",
            "lead_id": lead_id
        }
    except Exception as e:
        logger.error(f"[TOOL] update_lead_email - ERROR - {str(e)}")
        return {
            "success": False,
            "error": f"Erro ao atualizar email: {str(e)}",
            "lead_id": lead_id
        }


# Export tools list
data_collection_tools = [
    update_field,
    update_lead_name,
    get_lead_data,
    update_lead_status,
    update_lead_email
]

__all__ = [
    "data_collection_tools",
    "update_field",
    "update_lead_name",
    "get_lead_data",
    "update_lead_status",
    "update_lead_email"
]
