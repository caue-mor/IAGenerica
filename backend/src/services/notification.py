"""
Notification Service
Sends notifications to team members about important events via WhatsApp

Enhanced with:
- Supabase persistence
- Retry with exponential backoff
- Multiple delivery channels
- Notification queue management
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import httpx

from .database import db
from ..core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Types of notifications"""
    NEW_LEAD = "new_lead"
    LEAD_QUALIFIED = "lead_qualified"
    HANDOFF_REQUEST = "handoff_request"
    FOLLOW_UP_NEEDED = "follow_up_needed"
    PROPOSAL_REQUESTED = "proposal_requested"
    DOCUMENT_RECEIVED = "document_received"
    APPOINTMENT_SCHEDULED = "appointment_scheduled"
    URGENT = "urgent"
    ERROR = "error"
    INFO = "info"


class NotificationPriority(str, Enum):
    """Priority levels for notifications"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(str, Enum):
    """Delivery channels for notifications"""
    IN_APP = "in_app"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SLACK = "slack"
    WEBHOOK = "webhook"


class NotificationStatus(str, Enum):
    """Status of a notification"""
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"


@dataclass
class Notification:
    """Represents a notification"""
    id: int
    company_id: int
    notification_type: NotificationType
    title: str
    message: str
    lead_id: Optional[int] = None
    conversation_id: Optional[int] = None
    data: Dict[str, Any] = field(default_factory=dict)
    priority: NotificationPriority = NotificationPriority.NORMAL
    channels: List[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.IN_APP])
    status: NotificationStatus = NotificationStatus.PENDING
    delivery_attempts: int = 0
    max_delivery_attempts: int = 3
    last_error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None

    @property
    def read(self) -> bool:
        return self.status == NotificationStatus.READ

    @property
    def delivered(self) -> bool:
        return self.status in [NotificationStatus.DELIVERED, NotificationStatus.READ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "type": self.notification_type.value,
            "title": self.title,
            "message": self.message,
            "lead_id": self.lead_id,
            "conversation_id": self.conversation_id,
            "metadata": self.data,
            "priority": self.priority.value,
            "channels": [c.value for c in self.channels],
            "status": self.status.value,
            "delivery_attempts": self.delivery_attempts,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }


class NotificationService:
    """
    Service for sending and managing notifications.

    Supports:
    - Supabase persistence
    - Multiple delivery channels
    - Retry with exponential backoff
    - External webhooks
    """

    TABLE_NAME = "iagenericanexma_notifications"

    def __init__(self, use_persistence: bool = True):
        """
        Initialize the notification service.

        Args:
            use_persistence: Whether to persist notifications to Supabase
        """
        self.use_persistence = use_persistence
        self.notifications: Dict[int, Notification] = {}  # In-memory cache
        self._next_id = 1
        self.webhooks: Dict[int, str] = {}  # company_id -> webhook_url
        self.webhook_secrets: Dict[int, str] = {}  # company_id -> secret
        self._supabase = None
        self._processing_queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None

    @property
    def supabase(self):
        """Lazy load Supabase client."""
        if self._supabase is None:
            self._supabase = get_supabase_client()
        return self._supabase

    async def start_worker(self):
        """Start the notification delivery worker."""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._delivery_worker())

    async def stop_worker(self):
        """Stop the notification delivery worker."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    async def _delivery_worker(self):
        """Background worker that processes notification delivery."""
        while True:
            try:
                notification = await self._processing_queue.get()
                await self._process_delivery(notification)
                self._processing_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in notification worker: {e}")

    async def send_notification(
        self,
        company_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        lead_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: List[NotificationChannel] = None
    ) -> Notification:
        """
        Send a notification with persistence and multi-channel support.

        Args:
            company_id: Company ID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            lead_id: Related lead ID (optional)
            conversation_id: Related conversation ID (optional)
            data: Additional data (optional)
            priority: Priority level
            channels: Delivery channels (default: based on priority)

        Returns:
            Created Notification
        """
        # Determine channels based on priority if not specified
        if channels is None:
            channels = [NotificationChannel.IN_APP]
            if priority in [NotificationPriority.HIGH, NotificationPriority.URGENT]:
                channels.append(NotificationChannel.WHATSAPP)
            if company_id in self.webhooks:
                channels.append(NotificationChannel.WEBHOOK)

        # Create notification object
        notification = Notification(
            id=self._next_id,
            company_id=company_id,
            notification_type=notification_type,
            title=title,
            message=message,
            lead_id=lead_id,
            conversation_id=conversation_id,
            data=data or {},
            priority=priority,
            channels=channels,
            status=NotificationStatus.PENDING
        )

        # Persist to database if enabled
        if self.use_persistence:
            try:
                notification = await self._persist_notification(notification)
            except Exception as e:
                logger.error(f"Failed to persist notification: {e}")
                # Continue with in-memory only

        # Store in memory cache
        self.notifications[notification.id] = notification
        self._next_id = max(self._next_id + 1, notification.id + 1)

        logger.info(
            f"Notification {notification.id} created: {title} "
            f"(Type: {notification_type.value}, Priority: {priority.value}, "
            f"Channels: {[c.value for c in channels]})"
        )

        # Queue for delivery
        await self._enqueue_delivery(notification)

        return notification

    async def _persist_notification(self, notification: Notification) -> Notification:
        """Persist notification to Supabase."""
        data = {
            "company_id": notification.company_id,
            "lead_id": notification.lead_id,
            "conversation_id": notification.conversation_id,
            "type": notification.notification_type.value,
            "title": notification.title,
            "message": notification.message,
            "channels": [c.value for c in notification.channels],
            "metadata": notification.data,
            "priority": notification.priority.value,
            "status": notification.status.value,
            "delivery_attempts": notification.delivery_attempts,
            "created_at": datetime.utcnow().isoformat()
        }

        result = self.supabase.table(self.TABLE_NAME).insert(data).execute()

        if result.data and len(result.data) > 0:
            notification.id = result.data[0]["id"]

        return notification

    async def _enqueue_delivery(self, notification: Notification):
        """Enqueue notification for delivery."""
        # For immediate delivery, process directly
        # In production, this would use a proper queue like Bull/Redis
        asyncio.create_task(self._process_delivery(notification))

    async def _process_delivery(self, notification: Notification):
        """Process notification delivery with retry."""
        max_retries = notification.max_delivery_attempts
        success = False

        for attempt in range(max_retries):
            try:
                notification.delivery_attempts = attempt + 1
                notification.status = NotificationStatus.PROCESSING

                # Update status in DB
                if self.use_persistence:
                    await self._update_notification_status(
                        notification.id,
                        NotificationStatus.PROCESSING,
                        delivery_attempts=notification.delivery_attempts
                    )

                # Deliver to each channel
                channel_results = []
                for channel in notification.channels:
                    result = await self._deliver_to_channel(notification, channel)
                    channel_results.append(result)

                # Check if at least one channel succeeded
                if any(channel_results):
                    success = True
                    notification.status = NotificationStatus.SENT
                    notification.sent_at = datetime.utcnow()

                    if self.use_persistence:
                        await self._update_notification_status(
                            notification.id,
                            NotificationStatus.SENT,
                            sent_at=notification.sent_at
                        )

                    logger.info(f"Notification {notification.id} sent successfully")
                    return

            except Exception as e:
                notification.last_error = str(e)
                logger.warning(f"Notification {notification.id} attempt {attempt + 1} failed: {e}")

                if attempt < max_retries - 1:
                    # Exponential backoff: 2^attempt seconds
                    await asyncio.sleep(2 ** attempt)

        # All retries failed
        if not success:
            notification.status = NotificationStatus.FAILED
            if self.use_persistence:
                await self._update_notification_status(
                    notification.id,
                    NotificationStatus.FAILED,
                    last_error=notification.last_error
                )
            logger.error(f"Notification {notification.id} failed after {max_retries} attempts")

    async def _deliver_to_channel(
        self,
        notification: Notification,
        channel: NotificationChannel
    ) -> bool:
        """Deliver notification to a specific channel."""
        try:
            if channel == NotificationChannel.WEBHOOK:
                return await self._send_to_webhook(notification.company_id, notification)
            elif channel == NotificationChannel.WHATSAPP:
                return await self._send_whatsapp_notification(notification.company_id, notification)
            elif channel == NotificationChannel.IN_APP:
                # In-app notifications are already stored in DB
                return True
            else:
                logger.warning(f"Unsupported channel: {channel}")
                return False
        except Exception as e:
            logger.error(f"Failed to deliver to {channel}: {e}")
            return False

    async def _update_notification_status(
        self,
        notification_id: int,
        status: NotificationStatus,
        delivery_attempts: int = None,
        sent_at: datetime = None,
        delivered_at: datetime = None,
        last_error: str = None
    ):
        """Update notification status in database."""
        try:
            update_data = {"status": status.value}
            if delivery_attempts is not None:
                update_data["delivery_attempts"] = delivery_attempts
            if sent_at:
                update_data["sent_at"] = sent_at.isoformat()
            if delivered_at:
                update_data["delivered_at"] = delivered_at.isoformat()
            if last_error:
                update_data["last_error"] = last_error

            self.supabase.table(self.TABLE_NAME).update(update_data).eq(
                "id", notification_id
            ).execute()
        except Exception as e:
            logger.error(f"Failed to update notification status: {e}")

    async def _send_to_webhook(
        self,
        company_id: int,
        notification: Notification
    ) -> bool:
        """
        Send notification to external webhook.

        Args:
            company_id: Company ID
            notification: Notification to send

        Returns:
            True if sent successfully
        """
        webhook_url = self.webhooks.get(company_id)
        if not webhook_url:
            return False

        payload = {
            "id": notification.id,
            "type": notification.notification_type.value,
            "title": notification.title,
            "message": notification.message,
            "lead_id": notification.lead_id,
            "data": notification.data,
            "priority": notification.priority.value,
            "timestamp": notification.created_at.isoformat()
        }

        # Add signature if secret is configured
        headers = {"Content-Type": "application/json"}
        if company_id in self.webhook_secrets:
            import hmac
            import hashlib
            import json
            secret = self.webhook_secrets[company_id]
            signature = hmac.new(
                secret.encode(),
                json.dumps(payload).encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = signature

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers=headers
                )

                if response.status_code in [200, 201, 202, 204]:
                    notification.delivered = True
                    notification.delivered_at = datetime.now()
                    logger.debug(f"Notification {notification.id} delivered to webhook")
                    return True
                else:
                    logger.warning(
                        f"Webhook returned {response.status_code} for "
                        f"notification {notification.id}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error sending notification to webhook: {e}")
            return False

    async def _send_whatsapp_notification(
        self,
        company_id: int,
        notification: Notification
    ) -> bool:
        """
        Send notification via WhatsApp to admin/team.

        Args:
            company_id: Company ID
            notification: Notification to send

        Returns:
            True if sent successfully
        """
        try:
            # Get company info
            company = await db.get_company(company_id)
            if not company:
                logger.error(f"Company {company_id} not found for WhatsApp notification")
                return False

            # Check if we have WhatsApp configured
            if not company.uazapi_instancia or not company.uazapi_token:
                logger.warning(f"Company {company_id} has no UAZAPI configured")
                return False

            # Get admin phone from company config or use company's own number
            admin_phone = getattr(company, 'notification_phone', None) or company.whatsapp_numero
            if not admin_phone:
                logger.warning(f"Company {company_id} has no notification phone configured")
                return False

            # Create WhatsApp service
            from .whatsapp import create_whatsapp_service
            wa = create_whatsapp_service(
                instance=company.uazapi_instancia,
                token=company.uazapi_token
            )

            # Format message based on notification type
            emoji_map = {
                NotificationType.NEW_LEAD: "🆕",
                NotificationType.LEAD_QUALIFIED: "⭐",
                NotificationType.HANDOFF_REQUEST: "🚨",
                NotificationType.FOLLOW_UP_NEEDED: "⏰",
                NotificationType.PROPOSAL_REQUESTED: "📋",
                NotificationType.DOCUMENT_RECEIVED: "📎",
                NotificationType.APPOINTMENT_SCHEDULED: "📅",
                NotificationType.URGENT: "⚠️",
                NotificationType.ERROR: "❌",
                NotificationType.INFO: "ℹ️",
            }

            emoji = emoji_map.get(notification.notification_type, "📢")
            priority_text = ""
            if notification.priority == NotificationPriority.URGENT:
                priority_text = " *[URGENTE]*"
            elif notification.priority == NotificationPriority.HIGH:
                priority_text = " *[IMPORTANTE]*"

            message = f"""{emoji}{priority_text} *{notification.title}*

{notification.message}

_Notificação automática do sistema_"""

            # Send the message
            result = await wa.send_text(to=admin_phone, message=message)

            # Check if message was sent successfully (result contains message_id on success)
            if result and (result.get("message_id") or result.get("success")):
                notification.delivered = True
                notification.delivered_at = datetime.now()
                logger.info(f"WhatsApp notification sent to {admin_phone}: {notification.title}")
                return True
            else:
                logger.warning(f"Failed to send WhatsApp notification to {admin_phone}: {result}")
                return False

        except Exception as e:
            logger.error(f"Error sending WhatsApp notification: {e}")
            return False

    def configure_webhook(
        self,
        company_id: int,
        webhook_url: str,
        secret: Optional[str] = None
    ) -> None:
        """
        Configure webhook for a company.

        Args:
            company_id: Company ID
            webhook_url: Webhook URL
            secret: Optional secret for signing
        """
        self.webhooks[company_id] = webhook_url
        if secret:
            self.webhook_secrets[company_id] = secret

        logger.info(f"Webhook configured for company {company_id}: {webhook_url}")

    def remove_webhook(self, company_id: int) -> bool:
        """
        Remove webhook configuration.

        Args:
            company_id: Company ID

        Returns:
            True if removed
        """
        removed = company_id in self.webhooks
        self.webhooks.pop(company_id, None)
        self.webhook_secrets.pop(company_id, None)
        return removed

    # ==================== Convenience Methods ====================

    async def notify_new_lead(
        self,
        company_id: int,
        lead_id: int,
        lead_name: str,
        lead_phone: str,
        origem: Optional[str] = None
    ) -> Notification:
        """
        Notify about a new lead.

        Args:
            company_id: Company ID
            lead_id: Lead ID
            lead_name: Lead name
            lead_phone: Lead phone
            origem: Lead source

        Returns:
            Created Notification
        """
        return await self.send_notification(
            company_id=company_id,
            notification_type=NotificationType.NEW_LEAD,
            title="Novo Lead",
            message=f"Novo lead cadastrado: {lead_name or 'Sem nome'} ({lead_phone})",
            lead_id=lead_id,
            data={
                "name": lead_name,
                "phone": lead_phone,
                "origem": origem
            }
        )

    async def notify_handoff(
        self,
        company_id: int,
        lead_id: int,
        lead_name: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Notification:
        """
        Notify about handoff request (human attention needed).

        Args:
            company_id: Company ID
            lead_id: Lead ID
            lead_name: Lead name
            reason: Reason for handoff

        Returns:
            Created Notification
        """
        return await self.send_notification(
            company_id=company_id,
            notification_type=NotificationType.HANDOFF_REQUEST,
            title="Atendimento Humano Solicitado",
            message=f"Lead {lead_name or lead_id} solicita atendimento humano. Motivo: {reason or 'Nao informado'}",
            lead_id=lead_id,
            data={"reason": reason, "lead_name": lead_name},
            priority=NotificationPriority.HIGH
        )

    async def notify_qualified_lead(
        self,
        company_id: int,
        lead_id: int,
        lead_name: Optional[str] = None,
        qualification_score: Optional[int] = None,
        qualification_data: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """
        Notify about a qualified lead.

        Args:
            company_id: Company ID
            lead_id: Lead ID
            lead_name: Lead name
            qualification_score: Qualification score
            qualification_data: Additional qualification data

        Returns:
            Created Notification
        """
        score_text = f" (Score: {qualification_score})" if qualification_score else ""

        return await self.send_notification(
            company_id=company_id,
            notification_type=NotificationType.LEAD_QUALIFIED,
            title="Lead Qualificado",
            message=f"Lead {lead_name or lead_id} foi qualificado{score_text}",
            lead_id=lead_id,
            data={
                "score": qualification_score,
                "lead_name": lead_name,
                **(qualification_data or {})
            },
            priority=NotificationPriority.HIGH
        )

    async def notify_document_received(
        self,
        company_id: int,
        lead_id: int,
        document_type: str,
        lead_name: Optional[str] = None
    ) -> Notification:
        """
        Notify about document received.

        Args:
            company_id: Company ID
            lead_id: Lead ID
            document_type: Type of document
            lead_name: Lead name

        Returns:
            Created Notification
        """
        return await self.send_notification(
            company_id=company_id,
            notification_type=NotificationType.DOCUMENT_RECEIVED,
            title="Documento Recebido",
            message=f"Lead {lead_name or lead_id} enviou um documento: {document_type}",
            lead_id=lead_id,
            data={"document_type": document_type, "lead_name": lead_name}
        )

    async def notify_proposal_requested(
        self,
        company_id: int,
        lead_id: int,
        lead_name: Optional[str] = None,
        proposal_details: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """
        Notify about proposal request.

        Args:
            company_id: Company ID
            lead_id: Lead ID
            lead_name: Lead name
            proposal_details: Proposal details

        Returns:
            Created Notification
        """
        return await self.send_notification(
            company_id=company_id,
            notification_type=NotificationType.PROPOSAL_REQUESTED,
            title="Proposta Solicitada",
            message=f"Lead {lead_name or lead_id} solicitou uma proposta",
            lead_id=lead_id,
            data={"lead_name": lead_name, **(proposal_details or {})},
            priority=NotificationPriority.HIGH
        )

    async def notify_error(
        self,
        company_id: int,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        lead_id: Optional[int] = None
    ) -> Notification:
        """
        Notify about an error.

        Args:
            company_id: Company ID
            error_message: Error message
            error_details: Additional details
            lead_id: Related lead ID

        Returns:
            Created Notification
        """
        return await self.send_notification(
            company_id=company_id,
            notification_type=NotificationType.ERROR,
            title="Erro no Sistema",
            message=error_message,
            lead_id=lead_id,
            data=error_details or {},
            priority=NotificationPriority.URGENT
        )

    # ==================== Query Methods ====================

    def get_unread(self, company_id: int) -> List[Notification]:
        """
        Get unread notifications for a company.

        Args:
            company_id: Company ID

        Returns:
            List of unread notifications
        """
        return [
            n for n in self.notifications.values()
            if n.company_id == company_id and not n.read
        ]

    def get_all(
        self,
        company_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """
        Get all notifications for a company.

        Args:
            company_id: Company ID
            limit: Maximum notifications to return
            offset: Offset for pagination

        Returns:
            List of notifications
        """
        notifications = sorted(
            [n for n in self.notifications.values() if n.company_id == company_id],
            key=lambda x: x.created_at,
            reverse=True
        )
        return notifications[offset:offset + limit]

    def get_for_lead(self, lead_id: int) -> List[Notification]:
        """
        Get notifications related to a lead.

        Args:
            lead_id: Lead ID

        Returns:
            List of notifications
        """
        return [
            n for n in self.notifications.values()
            if n.lead_id == lead_id
        ]

    def mark_as_read(self, notification_id: int) -> bool:
        """
        Mark a notification as read.

        Args:
            notification_id: Notification ID

        Returns:
            True if marked
        """
        if notification_id in self.notifications:
            self.notifications[notification_id].read = True
            self.notifications[notification_id].read_at = datetime.now()
            return True
        return False

    def mark_all_as_read(self, company_id: int) -> int:
        """
        Mark all notifications for a company as read.

        Args:
            company_id: Company ID

        Returns:
            Number of notifications marked
        """
        count = 0
        now = datetime.now()
        for n in self.notifications.values():
            if n.company_id == company_id and not n.read:
                n.read = True
                n.read_at = now
                count += 1
        return count

    def get_notification(self, notification_id: int) -> Optional[Notification]:
        """
        Get a specific notification.

        Args:
            notification_id: Notification ID

        Returns:
            Notification or None
        """
        return self.notifications.get(notification_id)

    def delete_notification(self, notification_id: int) -> bool:
        """
        Delete a notification.

        Args:
            notification_id: Notification ID

        Returns:
            True if deleted
        """
        if notification_id in self.notifications:
            del self.notifications[notification_id]
            return True
        return False

    def get_stats(self, company_id: int) -> Dict[str, Any]:
        """
        Get notification statistics for a company.

        Args:
            company_id: Company ID

        Returns:
            Statistics dictionary
        """
        company_notifications = [
            n for n in self.notifications.values()
            if n.company_id == company_id
        ]

        type_counts = {}
        for ntype in NotificationType:
            type_counts[ntype.value] = sum(
                1 for n in company_notifications
                if n.notification_type == ntype
            )

        return {
            "total": len(company_notifications),
            "unread": sum(1 for n in company_notifications if not n.read),
            "by_type": type_counts,
            "webhook_configured": company_id in self.webhooks
        }


# Singleton instance
notification_service = NotificationService()
