"""
WhatsApp service - UAZAPI integration
Complete implementation with QR Code, Paircode, Webhook configuration, and Instance management
"""
import logging
import asyncio
from typing import Optional, Any, List
import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service for WhatsApp integration via UAZAPI"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        instance: Optional[str] = None,
        token: Optional[str] = None,
        admin_token: Optional[str] = None
    ):
        self.base_url = base_url or settings.UAZAPI_BASE_URL
        self.instance = instance
        self.token = token or settings.UAZAPI_TOKEN
        self.admin_token = admin_token or settings.UAZAPI_ADMIN_TOKEN

    def _get_headers(self, token: Optional[str] = None) -> dict[str, str]:
        """Get request headers with instance token"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "token": token or self.token or ""
        }

    def _get_admin_headers(self) -> dict[str, str]:
        """Get request headers with admin token"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "admintoken": self.admin_token or ""
        }

    def _format_phone(self, phone: str) -> str:
        """Format phone number for UAZAPI (Brazilian format)"""
        # Remove non-numeric characters
        clean = "".join(filter(str.isdigit, phone))

        # Remove @s.whatsapp.net if present
        clean = clean.replace("@s.whatsapp.net", "")

        # Add Brazil code if not present
        if not clean.startswith("55") and len(clean) <= 11:
            clean = "55" + clean

        return clean

    # ==========================================
    # INSTANCE MANAGEMENT
    # ==========================================

    async def create_instance(
        self,
        name: str,
        admin_field_01: Optional[str] = None,
        admin_field_02: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Create a new UAZAPI instance.

        Args:
            name: Instance name
            admin_field_01: Custom field (e.g., email)
            admin_field_02: Custom field (e.g., company_id)

        Returns:
            Instance data with token
        """
        url = f"{self.base_url}/instance/init"
        payload = {"name": name}

        if admin_field_01:
            payload["adminField01"] = admin_field_01
        if admin_field_02:
            payload["adminField02"] = admin_field_02

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_admin_headers(),
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "instance": data.get("instance"),
                        "token": data.get("token"),
                        "data": data
                    }
                else:
                    logger.error(f"Create instance error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }

        except Exception as e:
            logger.error(f"Error creating instance: {e}")
            return {"success": False, "error": str(e)}

    async def get_instance_status(
        self,
        instance: Optional[str] = None,
        token: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Get instance connection status.

        Args:
            instance: Instance ID
            token: Instance token

        Returns:
            Connection status with QR code if disconnected
        """
        token = token or self.token
        if not token:
            return {"success": False, "error": "Token not configured"}

        url = f"{self.base_url}/instance/status"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(token),
                    timeout=15
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "connected": data.get("status") == "connected",
                        "status": data.get("status"),  # connected, disconnected, connecting
                        "qrcode": data.get("qrcode"),
                        "paircode": data.get("paircode"),
                        "profile_name": data.get("profileName"),
                        "profile_pic": data.get("profilePicUrl"),
                        "owner": data.get("owner"),  # Phone number
                        "is_business": data.get("isBusiness"),
                        "data": data
                    }
                else:
                    return {
                        "success": False,
                        "connected": False,
                        "error": f"HTTP {response.status_code}"
                    }

        except Exception as e:
            logger.error(f"Error getting instance status: {e}")
            return {"success": False, "connected": False, "error": str(e)}

    async def list_instances(self) -> dict[str, Any]:
        """
        List all UAZAPI instances (requires admin token).

        Returns:
            List of all instances
        """
        url = f"{self.base_url}/instance/all"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self._get_admin_headers(),
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    instances = data if isinstance(data, list) else data.get("instances", [])
                    return {
                        "success": True,
                        "instances": instances,
                        "total": len(instances)
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }

        except Exception as e:
            logger.error(f"Error listing instances: {e}")
            return {"success": False, "error": str(e)}

    async def delete_instance(
        self,
        token: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Delete an instance.

        Args:
            token: Instance token

        Returns:
            Deletion result
        """
        token = token or self.token
        if not token:
            return {"success": False, "error": "Token not configured"}

        url = f"{self.base_url}/instance"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url,
                    headers=self._get_headers(token),
                    timeout=30
                )

                return {
                    "success": response.status_code in [200, 204],
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.error(f"Error deleting instance: {e}")
            return {"success": False, "error": str(e)}

    # ==========================================
    # QR CODE & PAIRING CODE CONNECTION
    # ==========================================

    async def connect_qrcode(
        self,
        token: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Start connection and get QR Code for scanning.

        Args:
            token: Instance token

        Returns:
            QR code data (base64 image)
        """
        token = token or self.token
        if not token:
            return {"success": False, "error": "Token not configured"}

        url = f"{self.base_url}/instance/connect"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(token),
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "qrcode": data.get("qrcode"),
                        "status": data.get("status"),
                        "data": data
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }

        except Exception as e:
            logger.error(f"Error getting QR code: {e}")
            return {"success": False, "error": str(e)}

    async def connect_paircode(
        self,
        phone: str,
        token: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Start connection with pairing code (alternative to QR).

        Args:
            phone: Phone number to pair
            token: Instance token

        Returns:
            Pairing code (XXXX-XXXX format)
        """
        token = token or self.token
        if not token:
            return {"success": False, "error": "Token not configured"}

        url = f"{self.base_url}/instance/connect"
        payload = {"phone": self._format_phone(phone)}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(token),
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "paircode": data.get("paircode"),
                        "status": data.get("status"),
                        "data": data
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }

        except Exception as e:
            logger.error(f"Error getting pair code: {e}")
            return {"success": False, "error": str(e)}

    async def disconnect(
        self,
        token: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Disconnect the WhatsApp instance.

        Args:
            token: Instance token

        Returns:
            Disconnection result
        """
        token = token or self.token
        if not token:
            return {"success": False, "error": "Token not configured"}

        url = f"{self.base_url}/instance/disconnect"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(token),
                    timeout=30
                )

                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
            return {"success": False, "error": str(e)}

    async def restart(
        self,
        token: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Restart the WhatsApp instance.

        Args:
            token: Instance token

        Returns:
            Restart result
        """
        token = token or self.token
        if not token:
            return {"success": False, "error": "Token not configured"}

        url = f"{self.base_url}/instance/restart"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(token),
                    timeout=30
                )

                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.error(f"Error restarting: {e}")
            return {"success": False, "error": str(e)}

    # ==========================================
    # WEBHOOK CONFIGURATION
    # ==========================================

    async def get_webhook_config(
        self,
        token: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Get current webhook configuration.

        Args:
            token: Instance token

        Returns:
            Webhook configuration
        """
        token = token or self.token
        if not token:
            return {"success": False, "error": "Token not configured"}

        url = f"{self.base_url}/webhook"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(token),
                    timeout=15
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "config": data
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    }

        except Exception as e:
            logger.error(f"Error getting webhook config: {e}")
            return {"success": False, "error": str(e)}

    async def set_webhook(
        self,
        webhook_url: str,
        token: Optional[str] = None,
        events: Optional[List[str]] = None,
        exclude_messages: Optional[List[str]] = None
    ) -> dict[str, Any]:
        """
        Configure webhook for the instance.

        Args:
            webhook_url: URL to receive webhook events
            token: Instance token
            events: List of events to subscribe (default: all)
            exclude_messages: List of message types to exclude

        Returns:
            Configuration result
        """
        token = token or self.token
        if not token:
            return {"success": False, "error": "Token not configured"}

        url = f"{self.base_url}/webhook"

        # Default events
        if events is None:
            events = [
                "messages",
                "messages.upsert",
                "messages.update",
                "connection",
                "connection.update",
                "qrcode.updated",
                "presence.update"
            ]

        # Default exclusions (avoid loops)
        if exclude_messages is None:
            exclude_messages = ["wasSentByApi", "isGroupYes"]

        payload = {
            "enabled": True,
            "url": webhook_url,
            "events": events,
            "excludeMessages": exclude_messages
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(token),
                    timeout=30
                )

                if response.status_code == 200:
                    return {
                        "success": True,
                        "webhook_url": webhook_url
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }

        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return {"success": False, "error": str(e)}

    async def disable_webhook(
        self,
        token: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Disable webhook for the instance.

        Args:
            token: Instance token

        Returns:
            Result
        """
        token = token or self.token
        if not token:
            return {"success": False, "error": "Token not configured"}

        url = f"{self.base_url}/webhook"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    url,
                    headers=self._get_headers(token),
                    timeout=30
                )

                return {
                    "success": response.status_code in [200, 204],
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.error(f"Error disabling webhook: {e}")
            return {"success": False, "error": str(e)}

    # ==========================================
    # MESSAGE SENDING
    # ==========================================

    async def send_text(
        self,
        to: str,
        message: str,
        instance: Optional[str] = None,
        token: Optional[str] = None,
        delay: int = 300,
        link_preview: bool = True
    ) -> dict[str, Any]:
        """
        Send a text message.

        Args:
            to: Phone number to send to
            message: Message text
            instance: UAZAPI instance (optional)
            token: UAZAPI token (optional)
            delay: Delay in ms before sending
            link_preview: Show link previews

        Returns:
            API response
        """
        token = token or self.token
        if not token:
            return {"success": False, "error": "Token not configured"}

        url = f"{self.base_url}/send/text"
        payload = {
            "number": self._format_phone(to),
            "text": message,
            "delay": delay,
            "linkPreview": link_preview
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(token),
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "message_id": data.get("key", {}).get("id"),
                        "data": data
                    }
                else:
                    logger.error(f"UAZAPI error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }

        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return {"success": False, "error": str(e)}

    async def send_typing(
        self,
        to: str,
        token: Optional[str] = None,
        duration: int = 3
    ) -> dict[str, Any]:
        """
        Send typing indicator.

        Args:
            to: Phone number
            token: Instance token
            duration: Duration in seconds

        Returns:
            Result
        """
        token = token or self.token
        if not token:
            return {"success": False, "error": "Token not configured"}

        url = f"{self.base_url}/message/presence"
        payload = {
            "number": self._format_phone(to),
            "presence": "composing",
            "duration": duration
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(token),
                    timeout=15
                )

                return {"success": response.status_code == 200}

        except Exception as e:
            logger.error(f"Error sending typing: {e}")
            return {"success": False, "error": str(e)}

    async def send_humanized_text(
        self,
        to: str,
        message: str,
        token: Optional[str] = None,
        show_typing: bool = True,
        split_by_newline: bool = True,
        delay_between: int = 2000
    ) -> dict[str, Any]:
        """
        Send text message with humanized behavior (typing, delays).

        Args:
            to: Phone number
            message: Message text
            token: Instance token
            show_typing: Show typing indicator
            split_by_newline: Split message by newlines
            delay_between: Delay between parts in ms

        Returns:
            Result
        """
        token = token or self.token
        if not token:
            return {"success": False, "error": "Token not configured"}

        # Split message if enabled
        parts = message.split("\n") if split_by_newline else [message]
        parts = [p.strip() for p in parts if p.strip()]

        results = []
        for i, part in enumerate(parts):
            # Show typing before each message
            if show_typing:
                await self.send_typing(to, token, duration=2)
                await asyncio.sleep(1.5)

            # Send the message part
            result = await self.send_text(to, part, token=token)
            results.append(result)

            # Delay between parts
            if i < len(parts) - 1:
                await asyncio.sleep(delay_between / 1000)

        return {
            "success": all(r.get("success") for r in results),
            "parts_sent": len(results),
            "results": results
        }

    async def send_image(
        self,
        to: str,
        image_url: str,
        caption: Optional[str] = None,
        token: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Send an image message.

        Args:
            to: Phone number to send to
            image_url: URL of the image
            caption: Optional caption
            token: UAZAPI token

        Returns:
            API response
        """
        token = token or self.token
        if not token:
            return {"success": False, "error": "Token not configured"}

        url = f"{self.base_url}/send/media"
        payload = {
            "number": self._format_phone(to),
            "type": "image",
            "media": image_url
        }
        if caption:
            payload["caption"] = caption

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(token),
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "message_id": data.get("key", {}).get("id"),
                        "data": data
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }

        except Exception as e:
            logger.error(f"Error sending WhatsApp image: {e}")
            return {"success": False, "error": str(e)}

    async def send_document(
        self,
        to: str,
        document_url: str,
        filename: str,
        caption: Optional[str] = None,
        token: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Send a document message.

        Args:
            to: Phone number to send to
            document_url: URL of the document
            filename: File name
            caption: Optional caption
            token: UAZAPI token

        Returns:
            API response
        """
        token = token or self.token
        if not token:
            return {"success": False, "error": "Token not configured"}

        url = f"{self.base_url}/send/media"
        payload = {
            "number": self._format_phone(to),
            "type": "document",
            "media": document_url,
            "filename": filename
        }
        if caption:
            payload["caption"] = caption

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(token),
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "message_id": data.get("key", {}).get("id"),
                        "data": data
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }

        except Exception as e:
            logger.error(f"Error sending WhatsApp document: {e}")
            return {"success": False, "error": str(e)}

    async def send_audio(
        self,
        to: str,
        audio_url: str,
        token: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Send an audio message.

        Args:
            to: Phone number to send to
            audio_url: URL of the audio file
            token: UAZAPI token

        Returns:
            API response
        """
        token = token or self.token
        if not token:
            return {"success": False, "error": "Token not configured"}

        url = f"{self.base_url}/send/media"
        payload = {
            "number": self._format_phone(to),
            "type": "audio",
            "media": audio_url
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(token),
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "message_id": data.get("key", {}).get("id"),
                        "data": data
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }

        except Exception as e:
            logger.error(f"Error sending WhatsApp audio: {e}")
            return {"success": False, "error": str(e)}

    async def mark_as_read(
        self,
        phone: str,
        token: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Mark chat as read.

        Args:
            phone: Phone number
            token: Instance token

        Returns:
            Result
        """
        token = token or self.token
        if not token:
            return {"success": False, "error": "Token not configured"}

        url = f"{self.base_url}/message/markread"
        payload = {"number": self._format_phone(phone)}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(token),
                    timeout=15
                )

                return {"success": response.status_code == 200}

        except Exception as e:
            logger.error(f"Error marking as read: {e}")
            return {"success": False, "error": str(e)}

    # ==========================================
    # LEGACY COMPATIBILITY
    # ==========================================

    async def check_connection(
        self,
        instance: Optional[str] = None,
        token: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Check UAZAPI instance connection status.
        Legacy method - use get_instance_status instead.
        """
        return await self.get_instance_status(instance, token)


# Factory function
def create_whatsapp_service(
    instance: Optional[str] = None,
    token: Optional[str] = None,
    admin_token: Optional[str] = None
) -> WhatsAppService:
    """Create WhatsApp service instance"""
    return WhatsAppService(instance=instance, token=token, admin_token=admin_token)


# Default service (will need instance/token set per company)
whatsapp = WhatsAppService()
