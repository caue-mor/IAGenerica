"""
UAZAPI webhook payload parser

Based on UAZAPI OpenAPI spec, webhooks are sent in this format:
{
  "event": "messages" or "type": "message",
  "instance": "instance_id",
  "data": {
    "id": "message_id",
    "chatid": "5511999999999@s.whatsapp.net",
    "sender": "5511999999999",
    "senderName": "Name",
    "fromMe": false,
    "text": "Hello",
    "messageType": "conversation",
    "messageTimestamp": 1672531200000,
    ...
  }
}
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
    """Message information from webhook - legacy format"""
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
    UAZAPI webhook payload - flexible model that handles the actual format:

    {
      "BaseUrl": "https://xxx.uazapi.com",
      "EventType": "messages",
      "instanceName": "instance-name",
      "chat": {...},
      "message": {
        "chatid": "558599673669@s.whatsapp.net",
        "sender_pn": "558599673669@s.whatsapp.net",
        "senderName": "Name",
        "text": "Hello",
        "fromMe": false,
        ...
      },
      "owner": "558596681498",
      "token": "..."
    }
    """
    # UAZAPI actual format fields
    EventType: Optional[str] = None  # "messages", "connection", etc.
    BaseUrl: Optional[str] = None
    instanceName: Optional[str] = None
    owner: Optional[str] = None
    token: Optional[str] = None
    chatSource: Optional[str] = None

    # Alternative format fields (for compatibility)
    event: Optional[str] = None
    type: Optional[str] = None

    # Instance can be string or dict
    instance: Optional[Any] = None

    # Message and chat data
    message: Optional[dict] = None  # Changed to dict for flexibility
    chat: Optional[dict] = None
    data: Optional[dict] = None

    # Legacy format
    sender: Optional[WebhookSender] = None

    # Parsed instance data
    instance_data: Optional[WebhookInstance] = None

    class Config:
        extra = "allow"  # Allow any extra fields

    @model_validator(mode='after')
    def parse_instance(self):
        """Parse instance field and normalize data"""
        # Handle instance as dict or string
        if isinstance(self.instance, dict):
            self.instance_data = WebhookInstance(**self.instance)
            # Detect connection event from instance status
            if self.instance_data.status:
                if not self.EventType and not self.event:
                    self.event = "connection.update"
        elif isinstance(self.instance, str):
            self.instance_data = WebhookInstance(name=self.instance)

        # Create instance_data from instanceName if not set
        if not self.instance_data and self.instanceName:
            self.instance_data = WebhookInstance(
                name=self.instanceName,
                token=self.token
            )

        return self

    @property
    def is_message_event(self) -> bool:
        """Check if this is a message event"""
        # Check EventType first (actual UAZAPI format)
        if self.EventType:
            return self.EventType.lower() in ["messages", "message"]

        # If we have message data with text, it's a message event
        if self.message and (self.message.get("text") or self.message.get("content")):
            return True

        # Check legacy event field
        if self.event:
            event_lower = self.event.lower()
            return any(x in event_lower for x in ["message", "messages", "chat", "text"])

        # Check data field
        if self.data and self.data.get("message"):
            return True

        return False

    @property
    def is_connection_event(self) -> bool:
        """Check if this is a connection event"""
        # Check EventType first
        if self.EventType:
            return self.EventType.lower() in ["connection", "connection.update"]

        if self.event:
            return self.event.lower() in ["connection", "connection.update"]

        # Check if instance has status (connection update)
        if self.instance_data and self.instance_data.status:
            return True

        return False

    @property
    def is_inbound(self) -> bool:
        """Check if message is inbound (from user)"""
        # Check message dict (actual UAZAPI format)
        if self.message and isinstance(self.message, dict):
            return not self.message.get("fromMe", True)

        # Check in data field
        if self.data:
            msg = self.data.get("message", {})
            return not msg.get("fromMe", True)

        return False

    @property
    def sender_phone(self) -> Optional[str]:
        """Extract sender phone number"""
        # UAZAPI format: message.sender_pn = "558599673669@s.whatsapp.net"
        if self.message and isinstance(self.message, dict):
            # Try sender_pn first (most reliable)
            sender_pn = self.message.get("sender_pn")
            if sender_pn:
                return extract_phone_from_jid(sender_pn)

            # Try chatid
            chatid = self.message.get("chatid")
            if chatid:
                return extract_phone_from_jid(chatid)

            # Try sender (might be LID format)
            sender = self.message.get("sender")
            if sender and "@s.whatsapp.net" in sender:
                return extract_phone_from_jid(sender)

        # Try chat field
        if self.chat and isinstance(self.chat, dict):
            wa_chatid = self.chat.get("wa_chatid")
            if wa_chatid:
                return extract_phone_from_jid(wa_chatid)

            phone = self.chat.get("phone")
            if phone:
                # Clean phone format like "+55 85 9967-3669"
                return phone.replace("+", "").replace(" ", "").replace("-", "")

        # Try legacy sender field
        if self.sender:
            phone = self.sender.phone or self.sender.id
            if phone:
                return extract_phone_from_jid(phone)

        # Try data field
        if self.data:
            key = self.data.get("key", {})
            remote_jid = key.get("remoteJid")
            if remote_jid:
                return extract_phone_from_jid(remote_jid)

        return None

    @property
    def sender_name(self) -> Optional[str]:
        """Extract sender name"""
        # UAZAPI format: message.senderName
        if self.message and isinstance(self.message, dict):
            sender_name = self.message.get("senderName")
            if sender_name:
                return sender_name

        # Try chat field
        if self.chat and isinstance(self.chat, dict):
            name = self.chat.get("name") or self.chat.get("wa_name") or self.chat.get("wa_contactName")
            if name:
                return name

        # Try legacy sender field
        if self.sender:
            return self.sender.pushName or self.sender.name

        # Try data field
        if self.data:
            return self.data.get("pushName") or self.data.get("senderName")

        return None

    @property
    def message_text(self) -> Optional[str]:
        """Extract message text content"""
        # UAZAPI format: message.text or message.content
        if self.message and isinstance(self.message, dict):
            # Try text first (most common)
            text = self.message.get("text")
            if text:
                return text

            # Try content
            content = self.message.get("content")
            if content and isinstance(content, str):
                return content

            # Try body
            body = self.message.get("body")
            if body:
                return body

        # Try data.message field (legacy format)
        if self.data:
            msg = self.data.get("message", {})
            if isinstance(msg, dict):
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
        msg_type = "text"

        # UAZAPI format: message.messageType or message.type
        if self.message and isinstance(self.message, dict):
            msg_type = self.message.get("messageType") or self.message.get("type") or "text"
        elif self.data:
            msg = self.data.get("message", {})
            if isinstance(msg, dict):
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

        # Normalize type
        type_mapping = {
            "chat": "text",
            "text": "text",
            "conversation": "text",
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
        # UAZAPI format: message.fileURL or message.mediaUrl
        if self.message and isinstance(self.message, dict):
            return self.message.get("fileURL") or self.message.get("mediaUrl")
        return None

    @property
    def message_id(self) -> Optional[str]:
        """Get message ID"""
        # UAZAPI format: message.messageid or message.id
        if self.message and isinstance(self.message, dict):
            return self.message.get("messageid") or self.message.get("id")
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
        """Try to extract company_id from instance name or adminField02"""
        # Try instanceName first (actual UAZAPI format: iagenerica-1)
        if self.instanceName and self.instanceName.startswith("iagenerica-"):
            try:
                return int(self.instanceName.replace("iagenerica-", ""))
            except (ValueError, TypeError):
                pass

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
