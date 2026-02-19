"""
Scheduling tools for the agent.

Tools for scheduling follow-ups, visits, and other time-based actions.
"""
import logging
from typing import Any, Optional
from datetime import datetime, timedelta
from langchain_core.tools import tool
from ...services.database import db
from ...services.enhanced_followup import enhanced_followup
from ...models.followup import FollowupReason, FollowupStage

logger = logging.getLogger(__name__)


def parse_datetime(date_str: str) -> Optional[datetime]:
    """
    Parse a datetime string in various formats.

    Supports:
    - ISO format: 2025-01-26T14:30:00
    - Date only: 2025-01-26
    - Brazilian format: 26/01/2025 14:30
    - Relative: amanha, proxima_semana, em_X_dias
    """
    try:
        # ISO format
        if "T" in date_str:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        # Brazilian format with time
        if "/" in date_str and ":" in date_str:
            return datetime.strptime(date_str, "%d/%m/%Y %H:%M")

        # Brazilian format date only
        if "/" in date_str:
            return datetime.strptime(date_str, "%d/%m/%Y")

        # ISO date only
        if "-" in date_str:
            return datetime.strptime(date_str, "%Y-%m-%d")

        # Relative dates
        now = datetime.utcnow()
        date_str_lower = date_str.lower()

        if date_str_lower == "amanha":
            return now + timedelta(days=1)
        elif date_str_lower == "proxima_semana":
            return now + timedelta(weeks=1)
        elif date_str_lower.startswith("em_") and date_str_lower.endswith("_dias"):
            days = int(date_str_lower.replace("em_", "").replace("_dias", ""))
            return now + timedelta(days=days)
        elif date_str_lower.startswith("em_") and date_str_lower.endswith("_horas"):
            hours = int(date_str_lower.replace("em_", "").replace("_horas", ""))
            return now + timedelta(hours=hours)

        return None
    except Exception:
        return None


@tool
async def schedule_followup(
    lead_id: int,
    scheduled_for: str,
    message: str,
    followup_type: str = "general",
    notes: Optional[str] = None
) -> dict[str, Any]:
    """
    Schedule a follow-up for a lead at a future date/time.
    Use this to remind the team to contact the lead later.

    Args:
        lead_id: The lead ID in the database
        scheduled_for: When to follow up - supports formats:
            - ISO: "2025-01-26T14:30:00"
            - Date: "2025-01-26"
            - Brazilian: "26/01/2025 14:30"
            - Relative: "amanha", "proxima_semana", "em_3_dias", "em_2_horas"
        message: Message to include in the follow-up reminder
        followup_type: Type of follow-up - "general", "proposal", "negotiation", "check_in"
        notes: Optional additional notes for the team

    Returns:
        Dictionary with follow-up scheduling confirmation

    Example:
        schedule_followup(
            lead_id=123,
            scheduled_for="amanha",
            message="Ligar para confirmar interesse",
            followup_type="check_in"
        )
    """
    try:
        logger.info(f"[TOOL] schedule_followup - lead_id={lead_id}, scheduled_for={scheduled_for}")

        # Parse the scheduled date
        scheduled_datetime = parse_datetime(scheduled_for)

        if not scheduled_datetime:
            return {
                "success": False,
                "error": f"Formato de data invalido: {scheduled_for}. Use formatos como: '2025-01-26', 'amanha', 'em_3_dias'",
                "lead_id": lead_id
            }

        # Ensure the date is in the future
        if scheduled_datetime < datetime.utcnow():
            return {
                "success": False,
                "error": "A data do follow-up deve ser no futuro.",
                "lead_id": lead_id
            }

        # Create follow-up record
        followup_data = {
            "scheduled_for": scheduled_datetime.isoformat(),
            "message": message,
            "type": followup_type,
            "notes": notes,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }

        # Get existing follow-ups and append
        lead = await db.get_lead(lead_id)
        if not lead:
            return {
                "success": False,
                "error": f"Lead {lead_id} nao encontrado.",
                "lead_id": lead_id
            }

        existing_followups = lead.dados_coletados.get("followups", []) if lead.dados_coletados else []
        existing_followups.append(followup_data)

        await db.update_lead_field(lead_id, "followups", existing_followups)
        await db.update_lead_field(lead_id, "next_followup_at", scheduled_datetime.isoformat())

        # Register with enhanced follow-up service (database persistence)
        reason_map = {
            "general": FollowupReason.INACTIVITY,
            "reminder": FollowupReason.INACTIVITY,
            "proposal": FollowupReason.PROPOSAL_SENT,
            "negotiation": FollowupReason.CUSTOM,
            "check_in": FollowupReason.INACTIVITY,
            "reengagement": FollowupReason.INACTIVITY,
            "qualification": FollowupReason.FIELD_PENDING
        }

        # Calculate delay in hours from now to scheduled time
        delay_hours = max(0.1, (scheduled_datetime - datetime.utcnow()).total_seconds() / 3600)

        scheduled_followup = await enhanced_followup.schedule_followup(
            company_id=lead.company_id,
            lead_id=lead_id,
            reason=reason_map.get(followup_type, FollowupReason.CUSTOM),
            stage=FollowupStage.FIRST,
            delay_hours=delay_hours,
            message=message,
            context={"notes": notes, "tool_scheduled": True}
        )

        if scheduled_followup:
            followup_data["scheduler_id"] = scheduled_followup.id

        logger.info(f"[TOOL] schedule_followup - SUCCESS - scheduled for {scheduled_datetime.isoformat()} (scheduler ID: {scheduled_followup.id})")

        return {
            "success": True,
            "message": f"Follow-up agendado para {scheduled_datetime.strftime('%d/%m/%Y %H:%M')}.",
            "lead_id": lead_id,
            "scheduled_for": scheduled_datetime.isoformat(),
            "followup_type": followup_type,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"[TOOL] schedule_followup - ERROR - {str(e)}")
        return {
            "success": False,
            "error": f"Erro ao agendar follow-up: {str(e)}",
            "lead_id": lead_id
        }


@tool
async def schedule_visit(
    lead_id: int,
    scheduled_for: str,
    visit_type: str,
    address: Optional[str] = None,
    notes: Optional[str] = None,
    duration_minutes: int = 60
) -> dict[str, Any]:
    """
    Schedule a visit or meeting for a lead.
    Use this to schedule technical visits, sales meetings, or consultations.

    Args:
        lead_id: The lead ID in the database
        scheduled_for: When the visit is scheduled - supports multiple formats
        visit_type: Type of visit - "tecnica", "comercial", "consultoria", "instalacao"
        address: Address for the visit (optional, can use lead's address)
        notes: Optional notes about the visit
        duration_minutes: Expected duration in minutes (default: 60)

    Returns:
        Dictionary with visit scheduling confirmation

    Example:
        schedule_visit(
            lead_id=123,
            scheduled_for="26/01/2025 14:00",
            visit_type="tecnica",
            address="Rua das Flores, 123",
            duration_minutes=90
        )
    """
    try:
        logger.info(f"[TOOL] schedule_visit - lead_id={lead_id}, type={visit_type}, scheduled_for={scheduled_for}")

        # Parse the scheduled date
        scheduled_datetime = parse_datetime(scheduled_for)

        if not scheduled_datetime:
            return {
                "success": False,
                "error": f"Formato de data invalido: {scheduled_for}",
                "lead_id": lead_id
            }

        # Ensure the date is in the future
        if scheduled_datetime < datetime.utcnow():
            return {
                "success": False,
                "error": "A data da visita deve ser no futuro.",
                "lead_id": lead_id
            }

        # Get lead info for address if not provided
        lead = await db.get_lead(lead_id)
        if not lead:
            return {
                "success": False,
                "error": f"Lead {lead_id} nao encontrado.",
                "lead_id": lead_id
            }

        # Use provided address or try to get from lead data
        visit_address = address
        if not visit_address and lead.dados_coletados:
            visit_address = lead.dados_coletados.get("endereco") or lead.dados_coletados.get("address")

        # Create visit record
        visit_data = {
            "scheduled_for": scheduled_datetime.isoformat(),
            "type": visit_type,
            "address": visit_address,
            "notes": notes,
            "duration_minutes": duration_minutes,
            "status": "scheduled",
            "created_at": datetime.utcnow().isoformat()
        }

        # Get existing visits and append
        existing_visits = lead.dados_coletados.get("visits", []) if lead.dados_coletados else []
        existing_visits.append(visit_data)

        await db.update_lead_field(lead_id, "visits", existing_visits)
        await db.update_lead_field(lead_id, "next_visit_at", scheduled_datetime.isoformat())
        await db.update_lead_field(lead_id, "visit_scheduled", True)

        logger.info(f"[TOOL] schedule_visit - SUCCESS - {visit_type} scheduled for {scheduled_datetime.isoformat()}")

        return {
            "success": True,
            "message": f"Visita {visit_type} agendada para {scheduled_datetime.strftime('%d/%m/%Y %H:%M')}.",
            "lead_id": lead_id,
            "scheduled_for": scheduled_datetime.isoformat(),
            "visit_type": visit_type,
            "address": visit_address,
            "duration_minutes": duration_minutes,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"[TOOL] schedule_visit - ERROR - {str(e)}")
        return {
            "success": False,
            "error": f"Erro ao agendar visita: {str(e)}",
            "lead_id": lead_id
        }


@tool
async def cancel_scheduled_event(
    lead_id: int,
    event_type: str,
    reason: Optional[str] = None
) -> dict[str, Any]:
    """
    Cancel the next scheduled event (follow-up or visit) for a lead.
    Use this when a scheduled event needs to be cancelled.

    Args:
        lead_id: The lead ID in the database
        event_type: Type of event to cancel - "followup" or "visit"
        reason: Optional reason for cancellation

    Returns:
        Dictionary with cancellation confirmation

    Example:
        cancel_scheduled_event(lead_id=123, event_type="visit", reason="Cliente remarcou")
    """
    try:
        logger.info(f"[TOOL] cancel_scheduled_event - lead_id={lead_id}, type={event_type}")

        lead = await db.get_lead(lead_id)
        if not lead:
            return {
                "success": False,
                "error": f"Lead {lead_id} nao encontrado.",
                "lead_id": lead_id
            }

        if event_type == "followup":
            # Cancel the next follow-up
            followups = lead.dados_coletados.get("followups", []) if lead.dados_coletados else []

            if not followups:
                return {
                    "success": False,
                    "error": "Nenhum follow-up agendado para este lead.",
                    "lead_id": lead_id
                }

            # Mark the most recent pending follow-up as cancelled
            for followup in reversed(followups):
                if followup.get("status") == "pending":
                    followup["status"] = "cancelled"
                    followup["cancelled_at"] = datetime.utcnow().isoformat()
                    followup["cancel_reason"] = reason
                    break

            await db.update_lead_field(lead_id, "followups", followups)
            await db.update_lead_field(lead_id, "next_followup_at", None)

        elif event_type == "visit":
            # Cancel the next visit
            visits = lead.dados_coletados.get("visits", []) if lead.dados_coletados else []

            if not visits:
                return {
                    "success": False,
                    "error": "Nenhuma visita agendada para este lead.",
                    "lead_id": lead_id
                }

            # Mark the most recent scheduled visit as cancelled
            for visit in reversed(visits):
                if visit.get("status") == "scheduled":
                    visit["status"] = "cancelled"
                    visit["cancelled_at"] = datetime.utcnow().isoformat()
                    visit["cancel_reason"] = reason
                    break

            await db.update_lead_field(lead_id, "visits", visits)
            await db.update_lead_field(lead_id, "next_visit_at", None)
            await db.update_lead_field(lead_id, "visit_scheduled", False)

        else:
            return {
                "success": False,
                "error": f"Tipo de evento invalido: {event_type}. Use 'followup' ou 'visit'.",
                "lead_id": lead_id
            }

        logger.info(f"[TOOL] cancel_scheduled_event - SUCCESS - {event_type} cancelled")

        return {
            "success": True,
            "message": f"{event_type.capitalize()} cancelado com sucesso.",
            "lead_id": lead_id,
            "event_type": event_type,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"[TOOL] cancel_scheduled_event - ERROR - {str(e)}")
        return {
            "success": False,
            "error": f"Erro ao cancelar evento: {str(e)}",
            "lead_id": lead_id
        }


# Export tools list
scheduling_tools = [
    schedule_followup,
    schedule_visit,
    cancel_scheduled_event
]

__all__ = [
    "scheduling_tools",
    "schedule_followup",
    "schedule_visit",
    "cancel_scheduled_event"
]
