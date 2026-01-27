"""
UAZAPI Instance Management Service

Dedicated service for UAZAPI instance lifecycle:
- Create new instances
- Connect instances (QR code / Paircode)
- Get instance status
- Configure webhooks
- Manage instance tokens

Based on SAAS-SOLAR implementation patterns.
"""
import logging
from typing import Optional, Any, List, Dict
import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)


class UazapiService:
    """
    UAZAPI Instance Management Service

    Handles all UAZAPI instance operations including:
    - Instance creation with admin token
    - QR code and paircode connection
    - Status monitoring
    - Webhook configuration
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        admin_token: Optional[str] = None,
        instance_token: Optional[str] = None
    ):
        """
        Initialize UAZAPI service.

        Args:
            base_url: UAZAPI base URL (defaults to env UAZAPI_BASE_URL)
            admin_token: Admin token for instance creation (defaults to env UAZAPI_ADMIN_TOKEN)
            instance_token: Instance token for instance operations
        """
        self.base_url = (base_url or settings.UAZAPI_BASE_URL).rstrip("/")
        self.admin_token = admin_token or settings.UAZAPI_ADMIN_TOKEN
        self.instance_token = instance_token

    def _get_admin_headers(self) -> Dict[str, str]:
        """Get headers with admin token for instance creation"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "admintoken": self.admin_token or ""
        }

    def _get_instance_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        """Get headers with instance token for instance operations"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "token": token or self.instance_token or ""
        }

    # ==========================================
    # INSTANCE CREATION
    # ==========================================

    async def create_instance(
        self,
        name: str,
        admin_email: Optional[str] = None,
        webhook_url: Optional[str] = None,
        admin_field_01: Optional[str] = None,
        admin_field_02: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new UAZAPI instance.

        UAZAPI Endpoint: POST /instance/init
        Requires: admintoken header

        Args:
            name: Instance name (e.g., 'iagenerica-{company_id}')
            admin_email: Admin email for notifications
            webhook_url: Initial webhook URL (can be configured later)
            admin_field_01: Custom admin field (e.g., email)
            admin_field_02: Custom admin field (e.g., company_id)

        Returns:
            {
                "success": bool,
                "instance_id": str,
                "token": str,  # Instance token for future operations
                "name": str,
                "data": dict  # Full response data
            }
        """
        url = f"{self.base_url}/instance/init"

        payload = {
            "name": name
        }

        # Add optional fields
        if admin_email:
            payload["adminField01"] = admin_email
        elif admin_field_01:
            payload["adminField01"] = admin_field_01

        if admin_field_02:
            payload["adminField02"] = admin_field_02

        if webhook_url:
            payload["webhookUrl"] = webhook_url

        logger.info(f"Creating UAZAPI instance: {name}")

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_admin_headers()
                )

                logger.debug(f"Create instance response: {response.status_code} - {response.text[:500]}")

                if response.status_code == 200:
                    data = response.json()

                    # Handle different response formats
                    instance_data = data.get("instance", data)
                    token = data.get("token") or instance_data.get("token")
                    instance_id = (
                        instance_data.get("id") or
                        instance_data.get("instance") or
                        data.get("id")
                    )

                    logger.info(f"Instance created successfully: {instance_id}")

                    return {
                        "success": True,
                        "instance_id": instance_id,
                        "token": token,
                        "name": name,
                        "data": data
                    }
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"Failed to create instance: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code
                    }

        except httpx.TimeoutException:
            logger.error("Timeout creating instance")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.exception(f"Error creating instance: {e}")
            return {"success": False, "error": str(e)}

    # ==========================================
    # INSTANCE CONNECTION
    # ==========================================

    async def connect_instance(
        self,
        token: str,
        phone: Optional[str] = None,
        connection_type: str = "qrcode"
    ) -> Dict[str, Any]:
        """
        Connect instance and get QR code or paircode.

        UAZAPI Endpoint: POST /instance/connect
        Requires: token header

        Args:
            token: Instance token
            phone: Phone number (required for paircode type)
            connection_type: "qrcode" or "paircode"

        Returns:
            {
                "success": bool,
                "qrcode": str,  # Base64 encoded QR code image
                "paircode": str,  # XXXX-XXXX format pairing code
                "status": str,
                "data": dict
            }
        """
        url = f"{self.base_url}/instance/connect"

        payload = {}
        if connection_type == "paircode" and phone:
            # Format phone for paircode connection
            clean_phone = "".join(filter(str.isdigit, phone))
            if not clean_phone.startswith("55") and len(clean_phone) <= 11:
                clean_phone = "55" + clean_phone
            payload["phone"] = clean_phone

        logger.info(f"Connecting instance with {connection_type}")

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    json=payload if payload else None,
                    headers=self._get_instance_headers(token)
                )

                logger.debug(f"Connect response: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()

                    # Extract QR code and paircode from various response formats
                    qrcode = self._extract_qrcode(data)
                    paircode = self._extract_paircode(data)
                    status = data.get("status", "connecting")

                    logger.info(f"Connection initiated - QR: {'yes' if qrcode else 'no'}, Paircode: {'yes' if paircode else 'no'}")

                    return {
                        "success": True,
                        "qrcode": qrcode,
                        "paircode": paircode,
                        "status": status,
                        "connection_type": connection_type,
                        "data": data
                    }
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"Failed to connect: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code
                    }

        except httpx.TimeoutException:
            logger.error("Timeout connecting instance")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.exception(f"Error connecting instance: {e}")
            return {"success": False, "error": str(e)}

    def _extract_qrcode(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract QR code from various response formats"""
        # Direct qrcode field
        if data.get("qrcode"):
            return data["qrcode"]

        # Nested in instance object
        instance = data.get("instance", {})
        if isinstance(instance, dict) and instance.get("qrcode"):
            return instance["qrcode"]

        # Nested in data object
        nested_data = data.get("data", {})
        if isinstance(nested_data, dict) and nested_data.get("qrcode"):
            return nested_data["qrcode"]

        return None

    def _extract_paircode(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract paircode from various response formats"""
        # Direct paircode field
        if data.get("paircode"):
            return data["paircode"]

        # Nested in instance object
        instance = data.get("instance", {})
        if isinstance(instance, dict) and instance.get("paircode"):
            return instance["paircode"]

        # Nested in data object
        nested_data = data.get("data", {})
        if isinstance(nested_data, dict) and nested_data.get("paircode"):
            return nested_data["paircode"]

        return None

    # ==========================================
    # INSTANCE STATUS
    # ==========================================

    async def get_instance_status(
        self,
        token: str
    ) -> Dict[str, Any]:
        """
        Get instance connection status.

        UAZAPI Endpoint: GET /instance/status
        Requires: token header

        Args:
            token: Instance token

        Returns:
            {
                "success": bool,
                "connected": bool,
                "status": str,  # "connected", "disconnected", "connecting"
                "qrcode": str,  # If disconnected, may contain new QR
                "paircode": str,
                "profile_name": str,
                "profile_pic": str,
                "owner": str,  # Connected phone number
                "is_business": bool,
                "data": dict
            }
        """
        url = f"{self.base_url}/instance/status"

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    url,
                    headers=self._get_instance_headers(token)
                )

                if response.status_code == 200:
                    data = response.json()

                    # Handle multiple response formats
                    status = self._normalize_status(data)
                    connected = status == "connected"

                    return {
                        "success": True,
                        "connected": connected,
                        "status": status,
                        "qrcode": self._extract_qrcode(data),
                        "paircode": self._extract_paircode(data),
                        "profile_name": data.get("profileName") or data.get("profile_name"),
                        "profile_pic": data.get("profilePicUrl") or data.get("profile_pic"),
                        "owner": data.get("owner") or data.get("number"),
                        "is_business": data.get("isBusiness") or data.get("is_business", False),
                        "data": data
                    }
                else:
                    # Non-200 response - instance may be invalid
                    return {
                        "success": False,
                        "connected": False,
                        "status": "error",
                        "error": f"HTTP {response.status_code}",
                        "status_code": response.status_code
                    }

        except httpx.TimeoutException:
            return {
                "success": False,
                "connected": False,
                "status": "timeout",
                "error": "Request timeout"
            }
        except Exception as e:
            logger.exception(f"Error getting status: {e}")
            return {
                "success": False,
                "connected": False,
                "status": "error",
                "error": str(e)
            }

    def _normalize_status(self, data: Dict[str, Any]) -> str:
        """Normalize status from different response formats"""
        # Direct status field
        status = data.get("status")

        # Check for connected boolean
        if data.get("connected") is True:
            return "connected"
        if data.get("connected") is False:
            return "disconnected"

        # Check for state field
        state = data.get("state")
        if state:
            if state.lower() in ["open", "connected"]:
                return "connected"
            elif state.lower() in ["close", "closed", "disconnected"]:
                return "disconnected"

        # Normalize status string
        if status:
            status_lower = status.lower()
            if status_lower in ["open", "connected", "online"]:
                return "connected"
            elif status_lower in ["close", "closed", "disconnected", "offline"]:
                return "disconnected"
            elif status_lower in ["connecting", "opening"]:
                return "connecting"

        return status or "unknown"

    # ==========================================
    # WEBHOOK CONFIGURATION
    # ==========================================

    async def configure_webhook(
        self,
        token: str,
        url: str,
        events: Optional[List[str]] = None,
        exclude_messages: Optional[List[str]] = None,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Configure webhook for the instance.

        UAZAPI Endpoint: POST /webhook
        Requires: token header

        Args:
            token: Instance token
            url: Webhook URL to receive events
            events: List of events to subscribe (default: common events)
            exclude_messages: Message types to exclude (default: bot messages)
            enabled: Whether webhook is enabled

        Returns:
            {
                "success": bool,
                "webhook_url": str,
                "events": list,
                "data": dict
            }
        """
        webhook_url = f"{self.base_url}/webhook"

        # Default events for typical use case
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

        # Default exclusions to avoid loops
        if exclude_messages is None:
            exclude_messages = [
                "wasSentByApi",  # Exclude our own sent messages
                "isGroupYes"     # Exclude group messages
            ]

        payload = {
            "enabled": enabled,
            "url": url,
            "events": events,
            "excludeMessages": exclude_messages
        }

        logger.info(f"Configuring webhook: {url}")

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers=self._get_instance_headers(token)
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Webhook configured successfully")
                    return {
                        "success": True,
                        "webhook_url": url,
                        "events": events,
                        "data": data
                    }
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"Failed to configure webhook: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code
                    }

        except Exception as e:
            logger.exception(f"Error configuring webhook: {e}")
            return {"success": False, "error": str(e)}

    async def get_webhook_config(self, token: str) -> Dict[str, Any]:
        """
        Get current webhook configuration.

        UAZAPI Endpoint: GET /webhook
        Requires: token header

        Args:
            token: Instance token

        Returns:
            Current webhook configuration
        """
        url = f"{self.base_url}/webhook"

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    url,
                    headers=self._get_instance_headers(token)
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
            logger.exception(f"Error getting webhook config: {e}")
            return {"success": False, "error": str(e)}

    # ==========================================
    # INSTANCE MANAGEMENT
    # ==========================================

    async def disconnect_instance(self, token: str) -> Dict[str, Any]:
        """
        Disconnect WhatsApp from instance.

        UAZAPI Endpoint: POST /instance/disconnect
        Requires: token header

        Args:
            token: Instance token

        Returns:
            Disconnection result
        """
        url = f"{self.base_url}/instance/disconnect"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    headers=self._get_instance_headers(token)
                )

                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.exception(f"Error disconnecting: {e}")
            return {"success": False, "error": str(e)}

    async def restart_instance(self, token: str) -> Dict[str, Any]:
        """
        Restart instance.

        UAZAPI Endpoint: POST /instance/restart
        Requires: token header

        Args:
            token: Instance token

        Returns:
            Restart result
        """
        url = f"{self.base_url}/instance/restart"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    headers=self._get_instance_headers(token)
                )

                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.exception(f"Error restarting: {e}")
            return {"success": False, "error": str(e)}

    async def delete_instance(self, token: str) -> Dict[str, Any]:
        """
        Delete instance completely.

        UAZAPI Endpoint: DELETE /instance
        Requires: token header

        Args:
            token: Instance token

        Returns:
            Deletion result
        """
        url = f"{self.base_url}/instance"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.delete(
                    url,
                    headers=self._get_instance_headers(token)
                )

                return {
                    "success": response.status_code in [200, 204],
                    "status_code": response.status_code
                }

        except Exception as e:
            logger.exception(f"Error deleting instance: {e}")
            return {"success": False, "error": str(e)}

    async def list_all_instances(self) -> Dict[str, Any]:
        """
        List all UAZAPI instances (admin operation).

        UAZAPI Endpoint: GET /instance/all
        Requires: admintoken header

        Returns:
            List of all instances
        """
        url = f"{self.base_url}/instance/all"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    url,
                    headers=self._get_admin_headers()
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
                        "error": f"HTTP {response.status_code}"
                    }

        except Exception as e:
            logger.exception(f"Error listing instances: {e}")
            return {"success": False, "error": str(e)}


# Factory function
def create_uazapi_service(
    admin_token: Optional[str] = None,
    instance_token: Optional[str] = None
) -> UazapiService:
    """Create UAZAPI service instance"""
    return UazapiService(
        admin_token=admin_token,
        instance_token=instance_token
    )


# Default service instance
uazapi = UazapiService()
