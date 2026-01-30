"""
Enhanced Follow-up Service
Advanced follow-up scheduling with context preservation and multi-stage support.

Features:
- Database persistence (Supabase)
- Context preservation (last question, pending field)
- Multi-stage follow-ups (1h, 4h, 12h, 24h)
- Auto-cancel when lead responds
- Contextual templates
- Proposal follow-up integration
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from ..core.supabase_client import supabase
from ..models.followup import (
    Followup, FollowupCreate, FollowupUpdate,
    FollowupStatus, FollowupStage, FollowupReason,
    STAGE_HOURS, get_template, DEFAULT_TEMPLATES
)
from .database import db
from .whatsapp import create_whatsapp_service

logger = logging.getLogger(__name__)

# Table name
FOLLOWUPS_TABLE = "iagenericanexma_followups"


class EnhancedFollowupService:
    """
    Enhanced follow-up service with database persistence and context preservation.

    Key Features:
    - Persists follow-ups to database
    - Preserves conversation context
    - Multi-stage follow-ups
    - Auto-cancels when lead responds
    - Contextual message templates
    """

    def __init__(self, check_interval: int = 60):
        """
        Initialize the enhanced follow-up service.

        Args:
            check_interval: Seconds between checks for due follow-ups
        """
        self.check_interval = check_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    # ==================== CRUD Operations ====================

    async def get_followup(self, followup_id: int) -> Optional[Followup]:
        """Get a follow-up by ID"""
        try:
            response = supabase.table(FOLLOWUPS_TABLE).select("*").eq("id", followup_id).limit(1).execute()
            if response.data and len(response.data) > 0:
                return Followup(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error getting followup {followup_id}: {e}")
            return None

    async def list_followups(
        self,
        company_id: int,
        lead_id: Optional[int] = None,
        status: Optional[FollowupStatus] = None,
        pending_only: bool = False
    ) -> List[Followup]:
        """List follow-ups with optional filters"""
        try:
            query = supabase.table(FOLLOWUPS_TABLE).select("*").eq("company_id", company_id)

            if lead_id:
                query = query.eq("lead_id", lead_id)

            if status:
                query = query.eq("status", status.value if isinstance(status, FollowupStatus) else status)

            if pending_only:
                query = query.eq("status", FollowupStatus.PENDING.value)

            response = query.order("scheduled_for").execute()
            return [Followup(**f) for f in response.data] if response.data else []
        except Exception as e:
            logger.error(f"Error listing followups: {e}")
            return []

    async def create_followup(self, followup: FollowupCreate) -> Optional[Followup]:
        """Create a new follow-up"""
        try:
            data = followup.model_dump(exclude_none=True)

            # Convert enums to values
            if "stage" in data and isinstance(data["stage"], FollowupStage):
                data["stage"] = data["stage"].value
            if "reason" in data and isinstance(data["reason"], FollowupReason):
                data["reason"] = data["reason"].value
            if "status" in data and isinstance(data["status"], FollowupStatus):
                data["status"] = data["status"].value

            # Ensure scheduled_for is ISO format
            if isinstance(data.get("scheduled_for"), datetime):
                data["scheduled_for"] = data["scheduled_for"].isoformat()

            response = supabase.table(FOLLOWUPS_TABLE).insert(data).execute()

            if response.data and len(response.data) > 0:
                created = Followup(**response.data[0])
                logger.info(f"Followup {created.id} created for lead {followup.lead_id}, scheduled for {followup.scheduled_for}")
                return created
            return None
        except Exception as e:
            logger.error(f"Error creating followup: {e}")
            return None

    async def update_followup(
        self,
        followup_id: int,
        update: FollowupUpdate
    ) -> Optional[Followup]:
        """Update a follow-up"""
        try:
            data = update.model_dump(exclude_none=True)

            # Convert enums
            if "stage" in data and isinstance(data["stage"], FollowupStage):
                data["stage"] = data["stage"].value
            if "reason" in data and isinstance(data["reason"], FollowupReason):
                data["reason"] = data["reason"].value
            if "status" in data and isinstance(data["status"], FollowupStatus):
                data["status"] = data["status"].value

            if not data:
                return await self.get_followup(followup_id)

            response = supabase.table(FOLLOWUPS_TABLE).update(data).eq("id", followup_id).execute()

            if response.data:
                return Followup(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error updating followup {followup_id}: {e}")
            return None

    async def delete_followup(self, followup_id: int) -> bool:
        """Delete a follow-up"""
        try:
            response = supabase.table(FOLLOWUPS_TABLE).delete().eq("id", followup_id).execute()
            return len(response.data) > 0 if response.data else False
        except Exception as e:
            logger.error(f"Error deleting followup {followup_id}: {e}")
            return False

    # ==================== Scheduling Methods ====================

    async def schedule_followup(
        self,
        company_id: int,
        lead_id: int,
        reason: FollowupReason = FollowupReason.INACTIVITY,
        stage: FollowupStage = FollowupStage.FIRST,
        delay_hours: Optional[float] = None,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Followup]:
        """
        Schedule a follow-up with context preservation.

        Args:
            company_id: Company ID
            lead_id: Lead ID
            reason: Reason for the follow-up
            stage: Stage of the follow-up (determines default timing)
            delay_hours: Custom delay in hours (overrides stage default)
            message: Custom message (uses template if not provided)
            context: Context to preserve for the follow-up

        Returns:
            Created Followup or None
        """
        # Calculate scheduled time
        if delay_hours is None:
            delay_hours = STAGE_HOURS.get(stage, 1)

        scheduled_for = datetime.utcnow() + timedelta(hours=delay_hours)

        # Get lead info for context
        lead = await db.get_lead(lead_id)
        lead_name = lead.nome if lead else ""

        # Build context with lead info
        full_context = context or {}
        if lead_name:
            full_context["lead_name"] = lead_name

        # Get message from template if not provided
        if not message:
            template = get_template(stage, reason)
            if template:
                message = template.render(full_context)
            else:
                message = f"Oi{' ' + lead_name if lead_name else ''}! Podemos continuar nossa conversa?"

        # Create the follow-up
        followup_create = FollowupCreate(
            company_id=company_id,
            lead_id=lead_id,
            scheduled_for=scheduled_for,
            stage=stage,
            reason=reason,
            message=message,
            context=full_context
        )

        return await self.create_followup(followup_create)

    async def schedule_inactivity_followup(
        self,
        company_id: int,
        lead_id: int,
        last_question: Optional[str] = None,
        pending_field: Optional[str] = None,
        conversation_summary: Optional[str] = None
    ) -> Optional[Followup]:
        """
        Schedule a follow-up due to lead inactivity.

        This preserves the conversation context so the follow-up
        can naturally continue the conversation.

        Args:
            company_id: Company ID
            lead_id: Lead ID
            last_question: Last question asked by the agent
            pending_field: Field waiting for response
            conversation_summary: Brief summary of conversation

        Returns:
            Created Followup or None
        """
        context = {}
        if last_question:
            context["last_question"] = last_question
        if pending_field:
            context["pending_field"] = pending_field
        if conversation_summary:
            context["conversation_summary"] = conversation_summary

        # Check if there's already a pending followup for this lead
        existing = await self.get_pending_for_lead(lead_id)
        if existing:
            logger.info(f"Lead {lead_id} already has {len(existing)} pending followups, skipping")
            return existing[0]  # Return first existing

        return await self.schedule_followup(
            company_id=company_id,
            lead_id=lead_id,
            reason=FollowupReason.FIELD_PENDING if pending_field else FollowupReason.INACTIVITY,
            stage=FollowupStage.FIRST,
            context=context
        )

    async def schedule_proposal_followup(
        self,
        company_id: int,
        lead_id: int,
        proposal_id: int,
        proposal_titulo: str,
        dias_restantes: Optional[int] = None
    ) -> Optional[Followup]:
        """
        Schedule a follow-up for a sent proposal.

        Args:
            company_id: Company ID
            lead_id: Lead ID
            proposal_id: Proposal ID
            proposal_titulo: Proposal title
            dias_restantes: Days until proposal expires

        Returns:
            Created Followup or None
        """
        context = {
            "proposal_id": proposal_id,
            "proposal_titulo": proposal_titulo,
            "dias_restantes": dias_restantes
        }

        return await self.schedule_followup(
            company_id=company_id,
            lead_id=lead_id,
            reason=FollowupReason.PROPOSAL_SENT,
            stage=FollowupStage.FIRST,
            delay_hours=4,  # 4 hours after proposal sent
            context=context
        )

    async def schedule_multi_stage(
        self,
        company_id: int,
        lead_id: int,
        reason: FollowupReason = FollowupReason.INACTIVITY,
        context: Optional[Dict[str, Any]] = None,
        stages: List[FollowupStage] = None
    ) -> List[Followup]:
        """
        Schedule multiple follow-ups in sequence.

        Args:
            company_id: Company ID
            lead_id: Lead ID
            reason: Reason for follow-ups
            context: Context to preserve
            stages: List of stages to schedule (default: first three)

        Returns:
            List of created Followups
        """
        if stages is None:
            stages = [FollowupStage.FIRST, FollowupStage.SECOND, FollowupStage.THIRD]

        followups = []
        cumulative_hours = 0

        for stage in stages:
            stage_hours = STAGE_HOURS.get(stage, 1)
            cumulative_hours += stage_hours

            followup = await self.schedule_followup(
                company_id=company_id,
                lead_id=lead_id,
                reason=reason,
                stage=stage,
                delay_hours=cumulative_hours,
                context=context
            )

            if followup:
                followups.append(followup)

        logger.info(f"Scheduled {len(followups)} multi-stage followups for lead {lead_id}")
        return followups

    # ==================== Cancellation Methods ====================

    async def cancel_followup(
        self,
        followup_id: int,
        reason: str = "Manually cancelled"
    ) -> bool:
        """Cancel a specific follow-up"""
        try:
            response = supabase.table(FOLLOWUPS_TABLE).update({
                "status": FollowupStatus.CANCELLED.value,
                "cancelled_at": datetime.utcnow().isoformat(),
                "cancelled_reason": reason
            }).eq("id", followup_id).eq("status", FollowupStatus.PENDING.value).execute()

            if response.data:
                logger.info(f"Followup {followup_id} cancelled: {reason}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error cancelling followup {followup_id}: {e}")
            return False

    async def cancel_for_lead(
        self,
        lead_id: int,
        reason: str = "Lead responded"
    ) -> int:
        """
        Cancel all pending follow-ups for a lead.

        Call this when a lead responds to automatically cancel scheduled follow-ups.

        Args:
            lead_id: Lead ID
            reason: Cancellation reason

        Returns:
            Number of follow-ups cancelled
        """
        try:
            # Get pending followups for this lead
            response = supabase.table(FOLLOWUPS_TABLE).select("id").eq(
                "lead_id", lead_id
            ).eq("status", FollowupStatus.PENDING.value).execute()

            if not response.data:
                return 0

            # Cancel each one
            count = 0
            for row in response.data:
                cancel_response = supabase.table(FOLLOWUPS_TABLE).update({
                    "status": FollowupStatus.CANCELLED.value,
                    "cancelled_at": datetime.utcnow().isoformat(),
                    "cancelled_reason": reason
                }).eq("id", row["id"]).execute()

                if cancel_response.data:
                    count += 1

            if count > 0:
                logger.info(f"Cancelled {count} followups for lead {lead_id}: {reason}")

            return count
        except Exception as e:
            logger.error(f"Error cancelling followups for lead {lead_id}: {e}")
            return 0

    # ==================== Processing Methods ====================

    async def get_due_followups(self) -> List[Followup]:
        """Get all follow-ups that are due to be sent"""
        try:
            now = datetime.utcnow().isoformat()
            response = supabase.table(FOLLOWUPS_TABLE).select("*").eq(
                "status", FollowupStatus.PENDING.value
            ).lte("scheduled_for", now).order("scheduled_for").execute()

            return [Followup(**f) for f in response.data] if response.data else []
        except Exception as e:
            logger.error(f"Error getting due followups: {e}")
            return []

    async def process_due_followups(self) -> int:
        """
        Process all follow-ups that are due.

        Returns:
            Number of follow-ups processed
        """
        due_followups = await self.get_due_followups()
        processed = 0

        for followup in due_followups:
            success = await self._send_followup(followup)
            if success:
                processed += 1

        return processed

    async def _send_followup(self, followup: Followup) -> bool:
        """Send a follow-up message"""
        try:
            logger.info(f"Sending followup {followup.id} to lead {followup.lead_id}")

            # Get company and lead
            company = await db.get_company(followup.company_id)
            lead = await db.get_lead(followup.lead_id)

            if not company:
                await self._mark_failed(followup.id, "Company not found")
                return False

            if not lead:
                await self._mark_failed(followup.id, "Lead not found")
                return False

            # Check if AI is disabled for lead
            if not lead.ai_enabled:
                await self.cancel_followup(followup.id, "AI disabled for lead")
                return False

            # Check WhatsApp configuration
            if not company.uazapi_instancia or not company.uazapi_token:
                await self._mark_failed(followup.id, "WhatsApp not configured")
                return False

            # Get message (use stored or generate from template)
            message = followup.message
            if not message:
                # Try to render from template
                template = get_template(
                    FollowupStage(followup.stage) if isinstance(followup.stage, str) else followup.stage,
                    FollowupReason(followup.reason) if isinstance(followup.reason, str) else followup.reason
                )
                if template:
                    context = followup.context or {}
                    context["lead_name"] = lead.nome or ""
                    message = template.render(context)
                else:
                    message = f"Oi{' ' + lead.nome if lead.nome else ''}! Ainda posso ajudar?"

            # Send via WhatsApp
            wa_service = create_whatsapp_service(
                instance=company.uazapi_instancia,
                token=company.uazapi_token
            )

            result = await wa_service.send_text(
                to=lead.celular,
                message=message
            )

            # Check result
            if result and (result.get("message_id") or result.get("success")):
                # Mark as sent
                supabase.table(FOLLOWUPS_TABLE).update({
                    "status": FollowupStatus.SENT.value,
                    "sent_at": datetime.utcnow().isoformat()
                }).eq("id", followup.id).execute()

                # Save outbound message
                conversation = await db.get_active_conversation(lead.id)
                if conversation:
                    await db.save_outbound_message(
                        conversation_id=conversation.id,
                        lead_id=lead.id,
                        content=message,
                        message_type="text"
                    )

                logger.info(f"Followup {followup.id} sent successfully")
                return True
            else:
                error = result.get("error", "Unknown error") if result else "No response"
                await self._mark_failed(followup.id, error)
                return False

        except Exception as e:
            logger.exception(f"Error sending followup {followup.id}: {e}")
            await self._mark_failed(followup.id, str(e))
            return False

    async def _mark_failed(self, followup_id: int, error: str):
        """Mark a follow-up as failed"""
        try:
            followup = await self.get_followup(followup_id)
            if not followup:
                return

            metadata = followup.metadata or {}
            metadata["error"] = error

            supabase.table(FOLLOWUPS_TABLE).update({
                "status": FollowupStatus.FAILED.value,
                "metadata": metadata
            }).eq("id", followup_id).execute()

            logger.error(f"Followup {followup_id} failed: {error}")
        except Exception as e:
            logger.error(f"Error marking followup {followup_id} as failed: {e}")

    # ==================== Query Methods ====================

    async def get_pending_for_lead(self, lead_id: int) -> List[Followup]:
        """Get all pending follow-ups for a lead"""
        return await self.list_followups(
            company_id=0,  # Will be filtered by lead_id
            lead_id=lead_id,
            pending_only=True
        )

    async def has_pending_followups(self, lead_id: int) -> bool:
        """Check if lead has any pending follow-ups"""
        pending = await self.get_pending_for_lead(lead_id)
        return len(pending) > 0

    async def get_next_scheduled(self, lead_id: int) -> Optional[Followup]:
        """Get the next scheduled follow-up for a lead"""
        pending = await self.get_pending_for_lead(lead_id)
        return pending[0] if pending else None

    # ==================== Background Scheduler ====================

    async def start_scheduler(self):
        """Start the background scheduler"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Enhanced followup scheduler started")

    async def stop_scheduler(self):
        """Stop the background scheduler"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Enhanced followup scheduler stopped")

    async def _scheduler_loop(self):
        """Background loop that processes due follow-ups"""
        while self._running:
            try:
                processed = await self.process_due_followups()
                if processed > 0:
                    logger.debug(f"Processed {processed} follow-ups")
            except Exception as e:
                logger.exception(f"Error in scheduler loop: {e}")

            await asyncio.sleep(self.check_interval)

    # ==================== Statistics ====================

    async def get_stats(self, company_id: int) -> Dict[str, Any]:
        """Get follow-up statistics for a company"""
        try:
            all_followups = await self.list_followups(company_id)

            stats = {
                "total": len(all_followups),
                "by_status": {},
                "by_reason": {},
                "pending_count": 0,
                "sent_today": 0
            }

            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            for followup in all_followups:
                # Count by status
                status = followup.status.value if isinstance(followup.status, FollowupStatus) else followup.status
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

                # Count by reason
                reason = followup.reason.value if isinstance(followup.reason, FollowupReason) else followup.reason
                stats["by_reason"][reason] = stats["by_reason"].get(reason, 0) + 1

                # Count pending
                if status == FollowupStatus.PENDING.value:
                    stats["pending_count"] += 1

                # Count sent today
                if followup.sent_at and followup.sent_at >= today_start:
                    stats["sent_today"] += 1

            return stats
        except Exception as e:
            logger.error(f"Error getting followup stats: {e}")
            return {}


# Singleton instance
enhanced_followup = EnhancedFollowupService()


# Convenience functions

async def schedule_inactivity_followup(
    company_id: int,
    lead_id: int,
    last_question: Optional[str] = None,
    pending_field: Optional[str] = None
) -> Optional[Followup]:
    """Convenience function to schedule inactivity followup"""
    return await enhanced_followup.schedule_inactivity_followup(
        company_id=company_id,
        lead_id=lead_id,
        last_question=last_question,
        pending_field=pending_field
    )


async def cancel_followups_for_lead(lead_id: int, reason: str = "Lead responded") -> int:
    """Convenience function to cancel followups when lead responds"""
    return await enhanced_followup.cancel_for_lead(lead_id, reason)
