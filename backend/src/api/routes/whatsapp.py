"""
WhatsApp/UAZAPI management routes
Automatic instance creation, QR code connection, and webhook configuration
Based on SAAS-SOLAR pattern
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Any
from pydantic import BaseModel

from ...services.database import db
from ...services.whatsapp import create_whatsapp_service, WhatsAppService
from ...core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


# ==========================================
# REQUEST MODELS
# ==========================================

class ConnectRequest(BaseModel):
    """Request to connect WhatsApp"""
    phone: str  # Phone number (required)
    connection_type: str = "qrcode"  # qrcode or paircode


class SendMessageRequest(BaseModel):
    """Request to send a message"""
    to: str
    message: str
    humanized: bool = False


# ==========================================
# MAIN CONNECTION ENDPOINT
# ==========================================

@router.post("/{company_id}/connect")
async def connect_whatsapp(company_id: int, request: ConnectRequest):
    """
    Connect WhatsApp - AUTOMATIC flow.

    This single endpoint handles EVERYTHING:
    1. Validates existing token (if any)
    2. Creates new instance if needed
    3. Configures webhook automatically
    4. Saves all data to database
    5. Generates and returns QR code

    User only needs to provide: phone number
    """
    try:
        # Get company
        company = await db.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        service = create_whatsapp_service(admin_token=settings.UAZAPI_ADMIN_TOKEN)

        token = None
        instance_id = None
        reusing_existing = False

        # ==========================================
        # STEP 1: Check existing token
        # ==========================================
        if company.uazapi_token:
            logger.info(f"Company {company_id} has existing token, checking validity...")

            status_check = await service.get_instance_status(token=company.uazapi_token)

            if status_check.get("success"):
                token = company.uazapi_token
                reusing_existing = True
                current_status = status_check.get("status")

                logger.info(f"Existing token valid, status: {current_status}")

                # If already connected, return immediately
                if current_status == "connected":
                    return {
                        "success": True,
                        "status": "connected",
                        "message": "WhatsApp ja esta conectado",
                        "reusing_existing": True,
                        "profile_name": status_check.get("profile_name"),
                        "owner": status_check.get("owner")
                    }
            else:
                # Token is invalid - clear from database
                logger.info(f"Token invalid, clearing from database...")
                await db.update_company(company_id, {
                    "uazapi_token": None,
                    "uazapi_instancia": None,
                    "whatsapp_numero": None
                })

        # ==========================================
        # STEP 2: Create new instance if needed
        # ==========================================
        if not token:
            logger.info(f"Creating new instance for company {company_id}...")

            instance_name = f"iagenericanexma_{company_id}"

            create_result = await service.create_instance(
                name=instance_name,
                admin_field_01=company.email,
                admin_field_02=str(company_id)
            )

            if not create_result.get("success"):
                logger.error(f"Failed to create instance: {create_result.get('error')}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Erro ao criar instancia: {create_result.get('error')}"
                )

            token = create_result.get("token")
            instance_data = create_result.get("instance")
            instance_id = instance_data.get("id") if isinstance(instance_data, dict) else instance_data

            logger.info(f"Instance created: {instance_id}, token: {token[:20]}...")

        # ==========================================
        # STEP 3: Configure webhook automatically
        # ==========================================
        webhook_url = f"{settings.WEBHOOK_BASE_URL}/webhook/{company_id}"

        logger.info(f"Configuring webhook: {webhook_url}")

        webhook_result = await service.set_webhook(
            webhook_url=webhook_url,
            token=token,
            events=["messages", "messages.upsert", "connection", "connection.update"],
            exclude_messages=["wasSentByApi", "isGroupYes"]
        )

        if not webhook_result.get("success"):
            logger.warning(f"Webhook configuration warning: {webhook_result.get('error')}")

        # ==========================================
        # STEP 4: Save all data to database
        # ==========================================
        logger.info(f"Saving data to database...")

        update_data = {
            "uazapi_token": token,
            "uazapi_instancia": instance_id or token,
        }

        await db.update_company(company_id, update_data)

        # ==========================================
        # STEP 5: Generate QR Code or Paircode
        # ==========================================
        logger.info(f"Generating {request.connection_type}...")

        if request.connection_type == "paircode":
            connect_result = await service.connect_paircode(
                phone=request.phone,
                token=token
            )
        else:
            connect_result = await service.connect_qrcode(token=token)

        if not connect_result.get("success"):
            logger.error(f"Failed to generate QR: {connect_result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao gerar QR Code: {connect_result.get('error')}"
            )

        # Extract QR code from response
        qrcode = connect_result.get("qrcode")
        paircode = connect_result.get("paircode")

        # Also check nested data
        data = connect_result.get("data", {})
        if not qrcode:
            qrcode = data.get("qrcode")
            if isinstance(data.get("instance"), dict):
                qrcode = qrcode or data.get("instance", {}).get("qrcode")
        if not paircode:
            paircode = data.get("paircode")
            if isinstance(data.get("instance"), dict):
                paircode = paircode or data.get("instance", {}).get("paircode")

        logger.info(f"Connection initiated, QR code: {'yes' if qrcode else 'no'}, Paircode: {'yes' if paircode else 'no'}")

        return {
            "success": True,
            "status": "connecting",
            "qrcode": qrcode,
            "paircode": paircode,
            "connection_type": request.connection_type,
            "reusing_existing": reusing_existing,
            "message": "Escaneie o QR Code com seu WhatsApp"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in connect_whatsapp: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# STATUS ENDPOINT (for polling)
# ==========================================

@router.get("/{company_id}/status")
async def get_status(company_id: int):
    """
    Get WhatsApp connection status.

    Frontend polls this every 3 seconds to detect when connection is established.
    """
    try:
        company = await db.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        if not company.uazapi_token:
            return {
                "success": True,
                "status": "not_configured",
                "connected": False,
                "message": "WhatsApp nao configurado"
            }

        service = create_whatsapp_service(token=company.uazapi_token)
        result = await service.get_instance_status()

        # If connected, update database with phone number
        if result.get("connected") and result.get("owner"):
            owner = result.get("owner", "").replace("@s.whatsapp.net", "")

            if owner and owner != company.whatsapp_numero:
                await db.update_company(company_id, {
                    "whatsapp_numero": owner
                })

        return {
            "success": True,
            "status": result.get("status", "unknown"),
            "connected": result.get("connected", False),
            "qrcode": result.get("qrcode"),
            "paircode": result.get("paircode"),
            "profile_name": result.get("profile_name"),
            "owner": result.get("owner"),
            "whatsapp_numero": company.whatsapp_numero
        }

    except Exception as e:
        logger.exception(f"Error getting status: {e}")
        return {
            "success": False,
            "status": "error",
            "connected": False,
            "message": str(e)
        }


# ==========================================
# DISCONNECT ENDPOINT
# ==========================================

@router.post("/{company_id}/disconnect")
async def disconnect_whatsapp(company_id: int):
    """
    Disconnect WhatsApp.
    """
    company = await db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not company.uazapi_token:
        raise HTTPException(status_code=400, detail="WhatsApp nao configurado")

    service = create_whatsapp_service(token=company.uazapi_token)
    result = await service.disconnect()

    if result.get("success"):
        await db.update_company(company_id, {
            "whatsapp_numero": None
        })

    return result


# ==========================================
# MESSAGE SENDING ENDPOINTS
# ==========================================

@router.post("/{company_id}/send/text")
async def send_text_message(company_id: int, request: SendMessageRequest):
    """
    Send a text message via WhatsApp.
    """
    company = await db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not company.uazapi_token:
        raise HTTPException(status_code=400, detail="WhatsApp nao configurado")

    service = create_whatsapp_service(token=company.uazapi_token)

    if request.humanized:
        result = await service.send_humanized_text(
            to=request.to,
            message=request.message
        )
    else:
        result = await service.send_text(
            to=request.to,
            message=request.message
        )

    return result


@router.post("/{company_id}/send/typing")
async def send_typing_indicator(
    company_id: int,
    to: str = Query(..., description="Phone number"),
    duration: int = Query(3, description="Duration in seconds")
):
    """
    Send typing indicator.
    """
    company = await db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not company.uazapi_token:
        raise HTTPException(status_code=400, detail="WhatsApp nao configurado")

    service = create_whatsapp_service(token=company.uazapi_token)

    return await service.send_typing(to=to, duration=duration)
