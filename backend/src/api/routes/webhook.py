"""
Webhook routes for UAZAPI
"""
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Any

from ...models.webhook import WebhookPayload, parse_webhook
from ...services.database import db
from ...services.whatsapp import create_whatsapp_service
from ...agent import invoke_agent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])


async def process_message(
    company_id: int,
    payload: WebhookPayload
):
    """Background task to process incoming message"""
    try:
        # Get company
        company = await db.get_company(company_id)
        if not company:
            logger.error(f"Company {company_id} not found")
            return

        # Check if it's a valid inbound message
        logger.info(f"Processing: is_inbound={payload.is_inbound}, message_text={payload.message_text}, sender={payload.sender_phone}")

        if not payload.is_inbound or not payload.message_text:
            logger.info(f"Skipping: is_inbound={payload.is_inbound}, has_text={bool(payload.message_text)}")
            return

        sender_phone = payload.sender_phone
        if not sender_phone:
            logger.error("Could not extract sender phone")
            return

        logger.info(f"Processing message from {sender_phone}: {payload.message_text[:50]}...")

        # Get or create lead
        lead = await db.get_or_create_lead(
            company_id=company_id,
            celular=sender_phone,
            origem="whatsapp"
        )

        # Update lead name if provided
        if payload.sender_name and not lead.nome:
            await db.update_lead_name(lead.id, payload.sender_name)
            lead.nome = payload.sender_name

        # Get or create conversation
        thread_id = payload.thread_id or f"wa_{sender_phone}"
        start_node_id = None
        if company.flow_config:
            start_node_id = company.flow_config.get("start_node_id")

        conversation = await db.get_or_create_conversation(
            company_id=company_id,
            lead_id=lead.id,
            thread_id=thread_id,
            start_node_id=start_node_id
        )

        # Save inbound message
        await db.save_inbound_message(
            conversation_id=conversation.id,
            lead_id=lead.id,
            content=payload.message_text,
            message_type=payload.message_type,
            media_url=payload.media_url,
            uazapi_message_id=payload.message_id
        )

        # Check if AI is enabled
        if not conversation.ai_enabled or not lead.ai_enabled:
            logger.info(f"AI disabled for conversation {conversation.id}")
            return

        # Get message history
        messages = await db.list_messages(conversation.id, limit=10)
        message_history = [
            {"role": "user" if m.direction == "inbound" else "assistant", "content": m.content}
            for m in messages[:-1]  # Exclude current message
        ]

        # Invoke agent
        result = await invoke_agent(
            company=company,
            lead=lead,
            conversation=conversation,
            user_message=payload.message_text,
            message_history=message_history
        )

        # Send response if we have one
        if result.get("response"):
            # Create WhatsApp service for this company
            wa_service = create_whatsapp_service(
                instance=company.uazapi_instancia,
                token=company.uazapi_token
            )

            response_type = result.get("response_type", "text")
            audio_base64 = result.get("audio_base64")
            send_result = None

            # Handle audio response (ElevenLabs TTS)
            if response_type in ["audio", "both"] and audio_base64:
                try:
                    # Send audio as PTT (voice message)
                    # UAZAPI accepts base64 audio with data URI
                    audio_data = f"data:audio/ogg;base64,{audio_base64}"
                    send_result = await wa_service.send_ptt(
                        to=sender_phone,
                        audio_url=audio_data
                    )
                    logger.info(f"Audio response sent to {sender_phone}")

                    # For "both" mode, also send text
                    if response_type == "both":
                        text_result = await wa_service.send_text(
                            to=sender_phone,
                            message=result["response"]
                        )
                        logger.info(f"Text response also sent to {sender_phone}")

                except Exception as e:
                    logger.error(f"Error sending audio, falling back to text: {e}")
                    # Fall back to text on audio error
                    send_result = await wa_service.send_text(
                        to=sender_phone,
                        message=result["response"]
                    )
            else:
                # Send text message
                send_result = await wa_service.send_text(
                    to=sender_phone,
                    message=result["response"]
                )

            # Save outbound message
            message_type = "ptt" if response_type == "audio" and audio_base64 else "text"
            await db.save_outbound_message(
                conversation_id=conversation.id,
                lead_id=lead.id,
                content=result["response"],
                message_type=message_type,
                uazapi_message_id=send_result.get("message_id") if send_result else None
            )

            logger.info(f"Response sent to {sender_phone} (type: {response_type})")

    except Exception as e:
        logger.exception(f"Error processing message: {e}")


@router.post("/webhook/{company_id}")
async def receive_webhook(
    company_id: int,
    payload: dict[str, Any],
    background_tasks: BackgroundTasks
):
    """
    Receive webhook from UAZAPI.

    Args:
        company_id: Company ID
        payload: Raw webhook payload

    Returns:
        Acknowledgment
    """
    try:
        # Log raw payload for debugging
        logger.info(f"Raw webhook payload for company {company_id}: {payload}")

        # Parse payload
        webhook = parse_webhook(payload)

        logger.info(f"Parsed webhook: EventType={webhook.EventType}, is_message={webhook.is_message_event}, is_inbound={webhook.is_inbound}, sender={webhook.sender_phone}, name={webhook.sender_name}, text={webhook.message_text}")

        # Handle connection events
        if webhook.is_connection_event:
            await handle_connection_event(company_id, webhook)
            return {"status": "received", "event": "connection"}

        # Only process message events
        if not webhook.is_message_event:
            return {"status": "ignored", "reason": "not a message event"}

        # Process in background to respond quickly
        background_tasks.add_task(process_message, company_id, webhook)

        return {"status": "received"}

    except Exception as e:
        logger.exception(f"Webhook error: {e}")
        # Always return 200 to avoid retries
        return {"status": "error", "message": str(e)}


@router.get("/webhook/{company_id}/test")
async def test_webhook(company_id: int):
    """Test webhook endpoint"""
    company = await db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return {
        "status": "ok",
        "company": company.empresa,
        "uazapi_configured": bool(company.uazapi_instancia and company.uazapi_token)
    }


# ==========================================
# GLOBAL WEBHOOK (for all instances)
# ==========================================

@router.post("/webhook/global")
async def receive_global_webhook(
    payload: dict[str, Any],
    background_tasks: BackgroundTasks
):
    """
    Global webhook endpoint for all UAZAPI instances.

    This endpoint receives webhooks from any instance and routes them
    to the correct company based on:
    1. adminField02 (company_id stored during instance creation)
    2. Instance token lookup in database

    Configure this URL in UAZAPI webhook settings:
    https://your-domain.com/webhook/global

    Events to enable: connection, messages
    Exclude: wasSentByApi, isGroupYes
    """
    try:
        logger.info(f"Global webhook received: {payload.get('event', 'unknown')}")

        # Extract company_id from payload
        company_id = None

        # Try adminField02 first (set during instance creation)
        instance_data = payload.get("instance", {})
        admin_field_02 = instance_data.get("adminField02")

        if admin_field_02:
            try:
                company_id = int(admin_field_02)
                logger.info(f"Company ID from adminField02: {company_id}")
            except (ValueError, TypeError):
                pass

        # Try to find by token if adminField02 not available
        if not company_id:
            token = instance_data.get("token")
            if token:
                # Look up company by token
                company = await db.get_company_by_token(token)
                if company:
                    company_id = company.id
                    logger.info(f"Company ID from token lookup: {company_id}")

        # Try to find by instance name (iagenerica-{company_id})
        if not company_id:
            instance_name = instance_data.get("name", "")
            if instance_name.startswith("iagenerica-"):
                try:
                    company_id = int(instance_name.replace("iagenerica-", ""))
                    logger.info(f"Company ID from instance name: {company_id}")
                except (ValueError, TypeError):
                    pass

        # Parse webhook payload early
        webhook = parse_webhook(payload)

        # Try to get company_id from webhook if not found yet
        if not company_id:
            company_id = webhook.company_id_from_instance

        if not company_id:
            logger.warning(f"Could not determine company_id from payload")
            return {"status": "ignored", "reason": "company_id not found"}

        # Handle connection events
        if webhook.is_connection_event:
            await handle_connection_event(company_id, webhook)
            return {"status": "received", "event": "connection"}

        if not webhook.is_message_event:
            return {"status": "ignored", "reason": "not a message event"}

        # Process in background
        background_tasks.add_task(process_message, company_id, webhook)

        return {"status": "received", "company_id": company_id}

    except Exception as e:
        logger.exception(f"Global webhook error: {e}")
        # Don't raise - always return 200 to avoid UAZAPI retries
        return {"status": "error", "message": str(e)}


async def handle_connection_event(company_id: int, webhook: WebhookPayload):
    """Handle connection status change events"""
    try:
        status = webhook.connection_status or ""
        owner = webhook.instance_data.owner if webhook.instance_data else ""

        # Extract phone number from owner (format: 5511999999999@s.whatsapp.net)
        phone = owner.replace("@s.whatsapp.net", "") if owner else None

        logger.info(f"Connection event for company {company_id}: status={status}, phone={phone}")

        # Only update phone number when connected (status is checked via UAZAPI API in real-time)
        if status == "connected" and phone:
            await db.update_company(company_id, {"whatsapp_numero": phone})
            logger.info(f"Updated company {company_id} phone: {phone}")

    except Exception as e:
        logger.exception(f"Error handling connection event: {e}")
