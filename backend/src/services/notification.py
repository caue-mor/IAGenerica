"""
Notification Service
Sends notifications to team members about important events
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import httpx

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


@dataclass
class Notification:
    """Represents a notification"""
    id: int
    company_id: int
    notification_type: NotificationType
    title: str
    message: str
    lead_id: Optional[int] = None
    data: Dict[str, Any] = field(default_factory=dict)
    priority: NotificationPriority = NotificationPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    read: bool = False
    read_at: Optional[datetime] = None
    delivered: bool = False
    delivered_at: Optional[datetime] = None


class NotificationService:
    """
    Service for sending and managing notifications.

    Supports internal notifications and external webhooks.
    """

    def __init__(self):
        """Initialize the notification service"""
        self.notifications: Dict[int, Notification] = {}
        self._next_id = 1
        self.webhooks: Dict[int, str] = {}  # company_id -> webhook_url
        self.webhook_secrets: Dict[int, str] = {}  # company_id -> secret

    async def send_notification(
        self,
        company_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        lead_id: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> Notification:
        """
        Send a notification.

        Args:
            company_id: Company ID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            lead_id: Related lead ID (optional)
            data: Additional data (optional)
            priority: Priority level

        Returns:
            Created Notification
        """
        notification = Notification(
            id=self._next_id,
            company_id=company_id,
            notification_type=notification_type,
            title=title,
            message=message,
            lead_id=lead_id,
            data=data or {},
            priority=priority
        )

        self.notifications[notification.id] = notification
        self._next_id += 1

        logger.info(
            f"Notification {notification.id} created: {title} "
            f"(Type: {notification_type.value}, Priority: {priority.value})"
        )

        # Send to webhook if configured
        if company_id in self.webhooks:
            await self._send_to_webhook(company_id, notification)

        return notification

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
