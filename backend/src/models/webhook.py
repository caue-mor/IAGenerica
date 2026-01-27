"""
UAZAPI webhook payload parser
"""
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class WebhookSender(BaseModel):
    """Sender information from webhook"""
    id: Optional[str] = None
    name: Optional[str] = None
    pushName: Optional[str] = None
    phone: Optional[str] = None


class WebhookMessage(BaseModel):
    """Message information from webhook"""
    id: Optional[str] = None
    body: Optional[str] = None
    type: Optional[str] = None
    timestamp: Optional[int] = None
    fromMe: Optional[bool] = None
    isForwarded: Optional[bool] = None
    quotedMsg: Optional[dict] = None
    # Media fields
    mimetype: Optional[str] = None
    filename: Optional[str] = None
    caption: Optional[str] = None
    mediaUrl: Optional[str] = None
    # Location
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    # Contact
    vcard: Optional[str] = None


class WebhookPayload(BaseModel):
    """UAZAPI webhook payload"""
    event: str
    instance: Optional[str] = None
    sender: Optional[WebhookSender] = None
    message: Optional[WebhookMessage] = None
    chat: Optional[dict] = None
    data: Optional[dict] = None  # For other event types

    @property
    def is_message_event(self) -> bool:
        """Check if this is a message event"""
        return self.event in ["message", "messages.upsert", "message.any"]

    @property
    def is_inbound(self) -> bool:
        """Check if message is inbound (from user)"""
        if self.message:
            return not self.message.fromMe
        return False

    @property
    def sender_phone(self) -> Optional[str]:
        """Extract sender phone number"""
        if self.sender:
            # Try different fields
            phone = self.sender.phone or self.sender.id
            if phone:
                # Clean phone number (remove @c.us, etc)
                return phone.split("@")[0].replace("+", "").replace("-", "").replace(" ", "")
        return None

    @property
    def sender_name(self) -> Optional[str]:
        """Extract sender name"""
        if self.sender:
            return self.sender.pushName or self.sender.name
        return None

    @property
    def message_text(self) -> Optional[str]:
        """Extract message text content"""
        if self.message:
            # Text message
            if self.message.body:
                return self.message.body
            # Media with caption
            if self.message.caption:
                return self.message.caption
        return None

    @property
    def message_type(self) -> str:
        """Get message type"""
        if self.message:
            msg_type = self.message.type or "text"
            # Normalize type
            type_mapping = {
                "chat": "text",
                "text": "text",
                "image": "image",
                "video": "video",
                "audio": "audio",
                "ptt": "audio",  # push-to-talk (voice message)
                "document": "document",
                "sticker": "sticker",
                "location": "location",
                "contact": "contact",
                "contacts": "contact"
            }
            return type_mapping.get(msg_type.lower(), "text")
        return "text"

    @property
    def media_url(self) -> Optional[str]:
        """Get media URL if present"""
        if self.message:
            return self.message.mediaUrl
        return None

    @property
    def message_id(self) -> Optional[str]:
        """Get message ID"""
        if self.message:
            return self.message.id
        return None

    @property
    def thread_id(self) -> Optional[str]:
        """Generate thread ID from sender phone"""
        phone = self.sender_phone
        if phone:
            return f"wa_{phone}"
        return None


def parse_webhook(payload: dict) -> WebhookPayload:
    """Parse raw webhook payload into WebhookPayload model"""
    return WebhookPayload(**payload)


def extract_phone_from_jid(jid: str) -> str:
    """Extract phone number from WhatsApp JID"""
    # JID format: 5511999999999@c.us or 5511999999999@s.whatsapp.net
    return jid.split("@")[0].replace("+", "").replace("-", "").replace(" ", "")
