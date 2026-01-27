"""
UAZAPI webhook payload parser

Handles multiple UAZAPI webhook payload formats:
1. Message events: { event: "messages", instance: "id", data: {...} }
2. Connection events: { BaseUrl: "...", instance: { name, status, ... } }
"""
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, model_validator


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


class WebhookInstance(BaseModel):
    """Instance information from webhook"""
    name: Optional[str] = None
    token: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    profileName: Optional[str] = None
    profilePicUrl: Optional[str] = None
    adminField01: Optional[str] = None
    adminField02: Optional[str] = None

    class Config:
        extra = "allow"  # Allow extra fields


class WebhookPayload(BaseModel):
    """
    UAZAPI webhook payload - flexible model that handles multiple formats
    """
    # Standard format fields
    event: Optional[str] = None
    instance: Optional[Any] = None  # Can be string or dict
    sender: Optional[WebhookSender] = None
    message: Optional[WebhookMessage] = None
    chat: Optional[dict] = None
    data: Optional[dict] = None

    # Alternative format fields (connection events)
    BaseUrl: Optional[str] = None

    # Parsed instance data
    instance_data: Optional[WebhookInstance] = None

    class Config:
        extra = "allow"  # Allow any extra fields

    @model_validator(mode='after')
    def parse_instance(self):
        """Parse instance field which can be string or dict"""
        if isinstance(self.instance, dict):
            self.instance_data = WebhookInstance(**self.instance)
            # Detect connection event
            if not self.event and self.instance_data.status:
                self.event = "connection.update"
        elif isinstance(self.instance, str):
            self.instance_data = WebhookInstance(name=self.instance)
        return self

    @property
    def is_message_event(self) -> bool:
        """Check if this is a message event"""
        # If we have message data, it's likely a message event
        if self.message or (self.data and self.data.get("message")):
            return True
        if not self.event:
            return False
        event_lower = self.event.lower()
        return any(x in event_lower for x in ["message", "messages", "chat", "text"])

    @property
    def is_connection_event(self) -> bool:
        """Check if this is a connection event"""
        if not self.event:
            # Check if instance has status (connection update)
            if self.instance_data and self.instance_data.status:
                return True
            return False
        return self.event.lower() in ["connection", "connection.update"]

    @property
    def is_inbound(self) -> bool:
        """Check if message is inbound (from user)"""
        if self.message:
            return not self.message.fromMe
        # Check in data field
        if self.data:
            msg = self.data.get("message", {})
            return not msg.get("fromMe", True)
        return False

    @property
    def sender_phone(self) -> Optional[str]:
        """Extract sender phone number"""
        # Try sender field
        if self.sender:
            phone = self.sender.phone or self.sender.id
            if phone:
                return extract_phone_from_jid(phone)

        # Try data.key.remoteJid
        if self.data:
            key = self.data.get("key", {})
            remote_jid = key.get("remoteJid")
            if remote_jid:
                return extract_phone_from_jid(remote_jid)

        return None

    @property
    def sender_name(self) -> Optional[str]:
        """Extract sender name"""
        if self.sender:
            return self.sender.pushName or self.sender.name
        # Try data field
        if self.data:
            return self.data.get("pushName")
        return None

    @property
    def message_text(self) -> Optional[str]:
        """Extract message text content"""
        # Try message field
        if self.message:
            if self.message.body:
                return self.message.body
            if self.message.caption:
                return self.message.caption

        # Try data.message field
        if self.data:
            msg = self.data.get("message", {})
            # Text message
            if "conversation" in msg:
                return msg["conversation"]
            # Extended text
            if "extendedTextMessage" in msg:
                return msg["extendedTextMessage"].get("text")
            # Image/video caption
            for media_type in ["imageMessage", "videoMessage", "documentMessage"]:
                if media_type in msg:
                    return msg[media_type].get("caption")

        return None

    @property
    def message_type(self) -> str:
        """Get message type"""
        if self.message:
            msg_type = self.message.type or "text"
        elif self.data:
            msg = self.data.get("message", {})
            # Detect type from message structure
            if "conversation" in msg or "extendedTextMessage" in msg:
                msg_type = "text"
            elif "imageMessage" in msg:
                msg_type = "image"
            elif "videoMessage" in msg:
                msg_type = "video"
            elif "audioMessage" in msg:
                msg_type = "audio"
            elif "documentMessage" in msg:
                msg_type = "document"
            elif "stickerMessage" in msg:
                msg_type = "sticker"
            elif "locationMessage" in msg:
                msg_type = "location"
            elif "contactMessage" in msg or "contactsArrayMessage" in msg:
                msg_type = "contact"
            else:
                msg_type = "text"
        else:
            msg_type = "text"

        # Normalize type
        type_mapping = {
            "chat": "text",
            "text": "text",
            "image": "image",
            "video": "video",
            "audio": "audio",
            "ptt": "audio",
            "document": "document",
            "sticker": "sticker",
            "location": "location",
            "contact": "contact",
            "contacts": "contact"
        }
        return type_mapping.get(msg_type.lower(), "text")

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
        if self.data:
            key = self.data.get("key", {})
            return key.get("id")
        return None

    @property
    def thread_id(self) -> Optional[str]:
        """Generate thread ID from sender phone"""
        phone = self.sender_phone
        if phone:
            return f"wa_{phone}"
        return None

    @property
    def connection_status(self) -> Optional[str]:
        """Get connection status for connection events"""
        if self.instance_data:
            return self.instance_data.status
        return None

    @property
    def company_id_from_instance(self) -> Optional[int]:
        """Try to extract company_id from instance adminField02 or name"""
        if self.instance_data:
            # Try adminField02
            if self.instance_data.adminField02:
                try:
                    return int(self.instance_data.adminField02)
                except (ValueError, TypeError):
                    pass
            # Try instance name (format: iagenerica-{company_id})
            if self.instance_data.name and self.instance_data.name.startswith("iagenerica-"):
                try:
                    return int(self.instance_data.name.replace("iagenerica-", ""))
                except (ValueError, TypeError):
                    pass
        return None


def parse_webhook(payload: dict) -> WebhookPayload:
    """Parse raw webhook payload into WebhookPayload model"""
    return WebhookPayload(**payload)


def extract_phone_from_jid(jid: str) -> str:
    """Extract phone number from WhatsApp JID"""
    # JID format: 5511999999999@c.us or 5511999999999@s.whatsapp.net
    return jid.split("@")[0].replace("+", "").replace("-", "").replace(" ", "")
