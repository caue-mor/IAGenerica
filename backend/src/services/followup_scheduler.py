"""
Follow-up Scheduler Service
Schedules and manages automated follow-up messages
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from .database import db
from .whatsapp import create_whatsapp_service

logger = logging.getLogger(__name__)


class FollowupStatus(str, Enum):
    """Status of a scheduled follow-up"""
    PENDING = "pending"
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"
    EXPIRED = "expired"


class FollowupType(str, Enum):
    """Type of follow-up"""
    REMINDER = "reminder"
    REENGAGEMENT = "reengagement"
    QUALIFICATION = "qualification"
    PROPOSAL = "proposal"
    CONFIRMATION = "confirmation"
    CUSTOM = "custom"


@dataclass
class ScheduledFollowup:
    """Represents a scheduled follow-up message"""
    id: int
    company_id: int
    lead_id: int
    scheduled_for: datetime
    message: str
    status: FollowupStatus = FollowupStatus.PENDING
    followup_type: FollowupType = FollowupType.CUSTOM
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class FollowupSchedulerService:
    """
    Service for scheduling and sending follow-up messages.

    Manages automated follow-ups to leads based on time delays
    or specific scheduled times.
    """

    def __init__(self, check_interval: int = 60):
        """
        Initialize the follow-up scheduler.

        Args:
            check_interval: Seconds between checks for pending follow-ups
        """
        self.scheduled: Dict[int, ScheduledFollowup] = {}
        self._next_id = 1
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.check_interval = check_interval
        self._lock = asyncio.Lock()

    async def schedule_followup(
        self,
        company_id: int,
        lead_id: int,
        message: str,
        delay_hours: Optional[int] = None,
        delay_minutes: Optional[int] = None,
        scheduled_for: Optional[datetime] = None,
        followup_type: FollowupType = FollowupType.CUSTOM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ScheduledFollowup:
        """
        Schedule a follow-up message.

        Args:
            company_id: Company ID
            lead_id: Lead ID
            message: Message to send
            delay_hours: Hours to wait before sending
            delay_minutes: Minutes to wait before sending
            scheduled_for: Specific datetime to send
            followup_type: Type of follow-up
            metadata: Additional metadata

        Returns:
            Created ScheduledFollowup
        """
        async with self._lock:
            # Calculate scheduled time
            if scheduled_for:
                send_time = scheduled_for
            elif delay_hours:
                send_time = datetime.now() + timedelta(hours=delay_hours)
            elif delay_minutes:
                send_time = datetime.now() + timedelta(minutes=delay_minutes)
            else:
                send_time = datetime.now() + timedelta(hours=24)  # Default: 24 hours

            followup = ScheduledFollowup(
                id=self._next_id,
                company_id=company_id,
                lead_id=lead_id,
                scheduled_for=send_time,
                message=message,
                followup_type=followup_type,
                metadata=metadata or {}
            )

            self.scheduled[followup.id] = followup
            self._next_id += 1

            logger.info(
                f"Follow-up {followup.id} scheduled for {send_time.isoformat()} "
                f"(Lead {lead_id}, Type: {followup_type.value})"
            )

            return followup

    async def schedule_reminder(
        self,
        company_id: int,
        lead_id: int,
        delay_hours: int = 24,
        custom_message: Optional[str] = None
    ) -> ScheduledFollowup:
        """
        Schedule a reminder follow-up.

        Args:
            company_id: Company ID
            lead_id: Lead ID
            delay_hours: Hours to wait
            custom_message: Optional custom message

        Returns:
            Created ScheduledFollowup
        """
        message = custom_message or (
            "Ola! Notamos que nossa conversa ficou em aberto. "
            "Posso ajudar com mais alguma informacao?"
        )

        return await self.schedule_followup(
            company_id=company_id,
            lead_id=lead_id,
            message=message,
            delay_hours=delay_hours,
            followup_type=FollowupType.REMINDER
        )

    async def schedule_reengagement(
        self,
        company_id: int,
        lead_id: int,
        delay_hours: int = 48,
        custom_message: Optional[str] = None
    ) -> ScheduledFollowup:
        """
        Schedule a re-engagement follow-up for inactive leads.

        Args:
            company_id: Company ID
            lead_id: Lead ID
            delay_hours: Hours to wait
            custom_message: Optional custom message

        Returns:
            Created ScheduledFollowup
        """
        message = custom_message or (
            "Oi! Passando para saber se ainda tem interesse. "
            "Estamos a disposicao para ajudar!"
        )

        return await self.schedule_followup(
            company_id=company_id,
            lead_id=lead_id,
            message=message,
            delay_hours=delay_hours,
            followup_type=FollowupType.REENGAGEMENT
        )

    async def cancel_followup(self, followup_id: int) -> bool:
        """
        Cancel a scheduled follow-up.

        Args:
            followup_id: Follow-up ID

        Returns:
            True if cancelled successfully
        """
        async with self._lock:
            if followup_id in self.scheduled:
                followup = self.scheduled[followup_id]
                if followup.status == FollowupStatus.PENDING:
                    followup.status = FollowupStatus.CANCELLED
                    logger.info(f"Follow-up {followup_id} cancelled")
                    return True
        return False

    async def cancel_all_for_lead(self, lead_id: int) -> int:
        """
        Cancel all pending follow-ups for a lead.

        Args:
            lead_id: Lead ID

        Returns:
            Number of follow-ups cancelled
        """
        count = 0
        async with self._lock:
            for followup in self.scheduled.values():
                if (
                    followup.lead_id == lead_id and
                    followup.status == FollowupStatus.PENDING
                ):
                    followup.status = FollowupStatus.CANCELLED
                    count += 1

        if count > 0:
            logger.info(f"Cancelled {count} follow-ups for lead {lead_id}")
        return count

    async def process_pending_followups(self) -> int:
        """
        Process all pending follow-ups that are due.

        Returns:
            Number of follow-ups processed
        """
        now = datetime.now()
        processed = 0

        # Get pending follow-ups that are due
        due_followups = [
            f for f in self.scheduled.values()
            if f.status == FollowupStatus.PENDING and f.scheduled_for <= now
        ]

        for followup in due_followups:
            success = await self._send_followup(followup)
            if success:
                processed += 1

        return processed

    async def _send_followup(self, followup: ScheduledFollowup) -> bool:
        """
        Send a follow-up message.

        Args:
            followup: Follow-up to send

        Returns:
            True if sent successfully
        """
        try:
            logger.info(f"Sending follow-up {followup.id} to lead {followup.lead_id}")

            # Get company and lead data
            company = await db.get_company(followup.company_id)
            lead = await db.get_lead(followup.lead_id)

            if not company:
                logger.error(f"Company {followup.company_id} not found")
                followup.status = FollowupStatus.FAILED
                followup.metadata["error"] = "Company not found"
                return False

            if not lead:
                logger.error(f"Lead {followup.lead_id} not found")
                followup.status = FollowupStatus.FAILED
                followup.metadata["error"] = "Lead not found"
                return False

            # Check if lead has AI disabled
            if not lead.ai_enabled:
                logger.info(f"Lead {lead.id} has AI disabled, skipping follow-up")
                followup.status = FollowupStatus.CANCELLED
                followup.metadata["reason"] = "AI disabled for lead"
                return False

            # Get UAZAPI token
            uazapi_token = company.uazapi_token
            if not uazapi_token:
                logger.error(f"Company {company.id} has no UAZAPI token")
                followup.status = FollowupStatus.FAILED
                followup.metadata["error"] = "No UAZAPI token"
                return False

            # Send message
            whatsapp = create_whatsapp_service(token=uazapi_token)
            result = await whatsapp.send_humanized_text(
                to=lead.celular,
                message=followup.message
            )

            if result.get("success"):
                followup.status = FollowupStatus.SENT
                followup.sent_at = datetime.now()
                followup.metadata["message_id"] = result.get("message_id")

                logger.info(f"Follow-up {followup.id} sent successfully")

                # Save outbound message to database
                conversation = await db.get_active_conversation(lead.id)
                if conversation:
                    await db.save_outbound_message(
                        conversation_id=conversation.id,
                        lead_id=lead.id,
                        content=followup.message,
                        message_type="text"
                    )

                return True
            else:
                followup.retry_count += 1
                error = result.get("error", "Unknown error")

                if followup.retry_count >= followup.max_retries:
                    followup.status = FollowupStatus.FAILED
                    followup.metadata["error"] = error
                    logger.error(
                        f"Follow-up {followup.id} failed after "
                        f"{followup.retry_count} retries: {error}"
                    )
                else:
                    # Reschedule for retry in 5 minutes
                    followup.scheduled_for = datetime.now() + timedelta(minutes=5)
                    logger.warning(
                        f"Follow-up {followup.id} failed, retrying in 5 minutes "
                        f"(attempt {followup.retry_count}/{followup.max_retries})"
                    )

                return False

        except Exception as e:
            logger.exception(f"Error sending follow-up {followup.id}: {e}")
            followup.status = FollowupStatus.FAILED
            followup.metadata["error"] = str(e)
            return False

    async def get_pending_for_lead(self, lead_id: int) -> List[ScheduledFollowup]:
        """
        Get all pending follow-ups for a lead.

        Args:
            lead_id: Lead ID

        Returns:
            List of pending follow-ups
        """
        return [
            f for f in self.scheduled.values()
            if f.lead_id == lead_id and f.status == FollowupStatus.PENDING
        ]

    async def get_followup(self, followup_id: int) -> Optional[ScheduledFollowup]:
        """
        Get a specific follow-up.

        Args:
            followup_id: Follow-up ID

        Returns:
            ScheduledFollowup or None
        """
        return self.scheduled.get(followup_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get follow-up service statistics.

        Returns:
            Statistics dictionary
        """
        status_counts = {}
        for status in FollowupStatus:
            status_counts[status.value] = sum(
                1 for f in self.scheduled.values() if f.status == status
            )

        return {
            "total": len(self.scheduled),
            "by_status": status_counts,
            "running": self._running,
        }

    async def start_scheduler(self) -> None:
        """Start the background scheduler"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Follow-up scheduler started")

    async def stop_scheduler(self) -> None:
        """Stop the background scheduler"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Follow-up scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Background loop that processes pending follow-ups"""
        while self._running:
            try:
                processed = await self.process_pending_followups()
                if processed > 0:
                    logger.debug(f"Processed {processed} follow-ups")
            except Exception as e:
                logger.exception(f"Error in scheduler loop: {e}")

            await asyncio.sleep(self.check_interval)

    def cleanup_old_followups(self, days: int = 30) -> int:
        """
        Remove old completed/failed follow-ups.

        Args:
            days: Remove follow-ups older than this many days

        Returns:
            Number of follow-ups removed
        """
        cutoff = datetime.now() - timedelta(days=days)
        to_remove = []

        for fid, followup in self.scheduled.items():
            if (
                followup.status in [FollowupStatus.SENT, FollowupStatus.FAILED, FollowupStatus.CANCELLED] and
                followup.created_at < cutoff
            ):
                to_remove.append(fid)

        for fid in to_remove:
            del self.scheduled[fid]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old follow-ups")

        return len(to_remove)


# Singleton instance
followup_scheduler = FollowupSchedulerService()
