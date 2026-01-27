"""
WhatsApp Connection Management Routes

API routes for UAZAPI instance management:
- GET /api/whatsapp/status/{company_id} - Get connection status
- POST /api/whatsapp/connect - Create/connect instance with QR code
- POST /api/whatsapp/disconnect - Disconnect instance

Based on SAAS-SOLAR implementation patterns.
"""
import logging
from fastapi import APIRouter, HTTPException, Path, Body
from typing import Optional, List
from pydantic import BaseModel, Field

from ...services.uazapi import create_uazapi_service, UazapiService
from ...services.database import db
from ...core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp-connect"])


# ==========================================
# REQUEST/RESPONSE MODELS
# ==========================================

class ConnectInstanceRequest(BaseModel):
    """Request to connect/create WhatsApp instance"""
    company_id: int = Field(..., description="Company ID to connect")
    phone: Optional[str] = Field(None, description="Phone number (required for paircode)")
    connection_type: str = Field("qrcode", description="Connection type: qrcode or paircode")


class DisconnectRequest(BaseModel):
    """Request to disconnect WhatsApp instance"""
    company_id: int = Field(..., description="Company ID to disconnect")


class ConnectionStatusResponse(BaseModel):
    """Response for connection status"""
    success: bool
    connected: bool
    status: str
    qrcode: Optional[str] = None
    paircode: Optional[str] = None
    profile_name: Optional[str] = None
    owner: Optional[str] = None
    whatsapp_numero: Optional[str] = None
    message: Optional[str] = None


class ConnectResponse(BaseModel):
    """Response for connect request"""
    success: bool
    status: str
    qrcode: Optional[str] = None
    paircode: Optional[str] = None
    connection_type: str
    instance_created: bool = False
    webhook_configured: bool = False
    message: Optional[str] = None


# ==========================================
# GET CONNECTION STATUS
# ==========================================

@router.get("/status/{company_id}", response_model=ConnectionStatusResponse)
async def get_whatsapp_status(
    company_id: int = Path(..., description="Company ID")
):
    """
    Get WhatsApp connection status for a company.

    This endpoint:
    1. Checks if company has a configured UAZAPI token
    2. Queries UAZAPI for current connection status
    3. Updates database if phone number changes
    4. Returns current status with profile info if connected

    Poll this endpoint every 3-5 seconds after initiating connection
    to detect when QR code is scanned and connection is established.
    """
    try:
        # Get company from database
        company = await db.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # Check if UAZAPI is configured
        if not company.uazapi_token:
            return ConnectionStatusResponse(
                success=True,
                connected=False,
                status="not_configured",
                message="WhatsApp not configured for this company"
            )

        # Get status from UAZAPI
        service = create_uazapi_service(instance_token=company.uazapi_token)
        result = await service.get_instance_status(token=company.uazapi_token)

        if not result.get("success"):
            # Token may be invalid - return error status
            return ConnectionStatusResponse(
                success=True,
                connected=False,
                status="error",
                message=result.get("error", "Failed to get status")
            )

        # If connected, update phone number in database if changed
        if result.get("connected") and result.get("owner"):
            owner = result.get("owner", "").replace("@s.whatsapp.net", "")
            if owner and owner != company.whatsapp_numero:
                await db.update_company(company_id, {"whatsapp_numero": owner})
                logger.info(f"Updated phone number for company {company_id}: {owner}")

        return ConnectionStatusResponse(
            success=True,
            connected=result.get("connected", False),
            status=result.get("status", "unknown"),
            qrcode=result.get("qrcode"),
            paircode=result.get("paircode"),
            profile_name=result.get("profile_name"),
            owner=result.get("owner"),
            whatsapp_numero=company.whatsapp_numero
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting WhatsApp status: {e}")
        return ConnectionStatusResponse(
            success=False,
            connected=False,
            status="error",
            message=str(e)
        )


# ==========================================
# CONNECT WHATSAPP
# ==========================================

@router.post("/connect", response_model=ConnectResponse)
async def connect_whatsapp(
    request: ConnectInstanceRequest = Body(...)
):
    """
    Create and/or connect WhatsApp instance for a company.

    This endpoint handles the complete flow:
    1. Validates company exists
    2. Checks if existing token is valid
    3. Creates new instance if needed (with name: iagenerica-{company_id})
    4. Configures webhook automatically
    5. Saves token and instance_id to companies table
    6. Returns QR code (base64 image) or paircode for connection

    After calling this endpoint, poll GET /status/{company_id} to detect
    when the user scans the QR code and connection is established.
    """
    company_id = request.company_id

    try:
        # Get company from database
        company = await db.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        service = create_uazapi_service()
        token = None
        instance_created = False
        webhook_configured = False

        # ==========================================
        # STEP 1: Check existing token validity
        # ==========================================
        if company.uazapi_token:
            logger.info(f"Company {company_id} has existing token, validating...")

            status_check = await service.get_instance_status(token=company.uazapi_token)

            if status_check.get("success"):
                token = company.uazapi_token
                current_status = status_check.get("status")
                logger.info(f"Existing token valid, status: {current_status}")

                # If already connected, return immediately
                if current_status == "connected":
                    return ConnectResponse(
                        success=True,
                        status="connected",
                        connection_type=request.connection_type,
                        instance_created=False,
                        webhook_configured=False,
                        message="WhatsApp already connected"
                    )
            else:
                # Token is invalid - clear from database
                logger.info(f"Token invalid for company {company_id}, clearing...")
                await db.update_company(company_id, {
                    "uazapi_token": None,
                    "uazapi_instancia": None,
                    "whatsapp_numero": None
                })
                token = None

        # ==========================================
        # STEP 2: Create new instance if needed
        # ==========================================
        if not token:
            logger.info(f"Creating new UAZAPI instance for company {company_id}")

            # Instance name format: iagenerica-{company_id}
            instance_name = f"iagenerica-{company_id}"

            create_result = await service.create_instance(
                name=instance_name,
                admin_email=company.email if hasattr(company, 'email') else None,
                admin_field_02=str(company_id)
            )

            if not create_result.get("success"):
                error_msg = create_result.get("error", "Unknown error")
                logger.error(f"Failed to create instance: {error_msg}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create UAZAPI instance: {error_msg}"
                )

            token = create_result.get("token")
            instance_id = create_result.get("instance_id")
            instance_created = True

            logger.info(f"Instance created: {instance_id}, token: {token[:20] if token else 'None'}...")

            # Save token to database immediately
            await db.update_company(company_id, {
                "uazapi_token": token,
                "uazapi_instancia": instance_id or token
            })

        # ==========================================
        # STEP 3: Configure webhook
        # ==========================================
        if settings.WEBHOOK_BASE_URL:
            webhook_url = f"{settings.WEBHOOK_BASE_URL}/webhook/{company_id}"
            logger.info(f"Configuring webhook: {webhook_url}")

            webhook_result = await service.configure_webhook(
                token=token,
                url=webhook_url,
                events=["messages", "messages.upsert", "connection", "connection.update"]
            )

            webhook_configured = webhook_result.get("success", False)

            if not webhook_configured:
                logger.warning(f"Webhook configuration warning: {webhook_result.get('error')}")
        else:
            logger.warning("WEBHOOK_BASE_URL not configured, skipping webhook setup")

        # ==========================================
        # STEP 4: Connect and get QR code / paircode
        # ==========================================
        logger.info(f"Connecting instance with {request.connection_type}")

        connect_result = await service.connect_instance(
            token=token,
            phone=request.phone,
            connection_type=request.connection_type
        )

        if not connect_result.get("success"):
            error_msg = connect_result.get("error", "Unknown error")
            logger.error(f"Failed to connect: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to connect instance: {error_msg}"
            )

        qrcode = connect_result.get("qrcode")
        paircode = connect_result.get("paircode")

        logger.info(f"Connection initiated - QR: {'yes' if qrcode else 'no'}, Paircode: {'yes' if paircode else 'no'}")

        return ConnectResponse(
            success=True,
            status="connecting",
            qrcode=qrcode,
            paircode=paircode,
            connection_type=request.connection_type,
            instance_created=instance_created,
            webhook_configured=webhook_configured,
            message="Scan the QR code with WhatsApp" if qrcode else "Enter the pairing code in WhatsApp"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error connecting WhatsApp: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# DISCONNECT WHATSAPP
# ==========================================

@router.post("/disconnect")
async def disconnect_whatsapp(
    request: DisconnectRequest = Body(...)
):
    """
    Disconnect WhatsApp instance for a company.

    This endpoint:
    1. Validates company has a configured token
    2. Calls UAZAPI disconnect endpoint
    3. Clears phone number from database (keeps token for reconnection)

    After disconnecting, the instance remains available for reconnection
    using the existing token. Call /connect again to get a new QR code.
    """
    company_id = request.company_id

    try:
        # Get company from database
        company = await db.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        if not company.uazapi_token:
            raise HTTPException(status_code=400, detail="WhatsApp not configured for this company")

        # Disconnect via UAZAPI
        service = create_uazapi_service(instance_token=company.uazapi_token)
        result = await service.disconnect_instance(token=company.uazapi_token)

        if result.get("success"):
            # Clear phone number but keep token for reconnection
            await db.update_company(company_id, {
                "whatsapp_numero": None
            })
            logger.info(f"WhatsApp disconnected for company {company_id}")

            return {
                "success": True,
                "status": "disconnected",
                "message": "WhatsApp disconnected successfully"
            }
        else:
            return {
                "success": False,
                "status": "error",
                "message": result.get("error", "Failed to disconnect")
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error disconnecting WhatsApp: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# ADDITIONAL MANAGEMENT ENDPOINTS
# ==========================================

@router.post("/restart/{company_id}")
async def restart_whatsapp(
    company_id: int = Path(..., description="Company ID")
):
    """
    Restart WhatsApp instance for a company.

    Useful when the instance is in an inconsistent state.
    """
    try:
        company = await db.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        if not company.uazapi_token:
            raise HTTPException(status_code=400, detail="WhatsApp not configured")

        service = create_uazapi_service(instance_token=company.uazapi_token)
        result = await service.restart_instance(token=company.uazapi_token)

        return {
            "success": result.get("success", False),
            "message": "Instance restarted" if result.get("success") else "Failed to restart"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error restarting WhatsApp: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhook/{company_id}")
async def get_webhook_config(
    company_id: int = Path(..., description="Company ID")
):
    """
    Get current webhook configuration for a company's instance.
    """
    try:
        company = await db.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        if not company.uazapi_token:
            raise HTTPException(status_code=400, detail="WhatsApp not configured")

        service = create_uazapi_service(instance_token=company.uazapi_token)
        result = await service.get_webhook_config(token=company.uazapi_token)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting webhook config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/{company_id}/configure")
async def configure_webhook(
    company_id: int = Path(..., description="Company ID"),
    webhook_url: Optional[str] = Body(None, embed=True),
    events: Optional[List[str]] = Body(None, embed=True)
):
    """
    Configure or update webhook for a company's instance.

    If webhook_url is not provided, uses the default:
    {WEBHOOK_BASE_URL}/webhook/{company_id}
    """
    try:
        company = await db.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        if not company.uazapi_token:
            raise HTTPException(status_code=400, detail="WhatsApp not configured")

        # Use default webhook URL if not provided
        if not webhook_url:
            if not settings.WEBHOOK_BASE_URL:
                raise HTTPException(
                    status_code=400,
                    detail="webhook_url required (WEBHOOK_BASE_URL not configured)"
                )
            webhook_url = f"{settings.WEBHOOK_BASE_URL}/webhook/{company_id}"

        service = create_uazapi_service(instance_token=company.uazapi_token)
        result = await service.configure_webhook(
            token=company.uazapi_token,
            url=webhook_url,
            events=events
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error configuring webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
