"""
Webhook routes for UAZAPI with message buffering
"""
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Any, Dict

from ...core.config import settings
from ...models.webhook import WebhookPayload, parse_webhook
from ...services.database import db
from ...services.whatsapp import create_whatsapp_service
from ...services.buffer import message_buffer, MessageBufferService
from ...services.notification import notification_service
from ...agent import invoke_agent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])

# Initialize buffer with settings
buffer_service = MessageBufferService(
    debounce_seconds=settings.BUFFER_DEBOUNCE_SECONDS,
    max_buffer_size=settings.BUFFER_MAX_SIZE
)


async def process_buffered_message(
    company_id: int,
    lead_id: int,
    combined_message: str,
    metadata: Dict[str, Any]
):
    """
    Process messages after buffer is ready.

    This is called by the buffer service after debounce period.
    """
    try:
        # Get company
        company = await db.get_company(company_id)
        if not company:
            logger.error(f"Company {company_id} not found")
            return

        # Get lead
        lead = await db.get_lead(lead_id)
        if not lead:
            logger.error(f"Lead {lead_id} not found")
            return

        sender_phone = lead.celular
        logger.info(f"[BUFFER] Processing {metadata.get('message_count', 1)} messages from {sender_phone}: {combined_message[:50]}...")

        # Get or create conversation
        thread_id = f"wa_{sender_phone}"
        start_node_id = None
        if company.flow_config:
            start_node_id = company.flow_config.get("start_node_id")

        conversation = await db.get_or_create_conversation(
            company_id=company_id,
            lead_id=lead.id,
            thread_id=thread_id,
            start_node_id=start_node_id
        )

        # Check if AI is enabled
        if not conversation.ai_enabled or not lead.ai_enabled:
            logger.info(f"AI disabled for conversation {conversation.id}")
            return

        # Get message history (increased to 40 for better context)
        messages = await db.list_messages(conversation.id, limit=40)
        message_history = [
            {"role": "user" if m.direction == "inbound" else "assistant", "content": m.content}
            for m in messages[:-1]  # Exclude messages just saved
        ]

        # Invoke agent with combined message
        result = await invoke_agent(
            company=company,
            lead=lead,
            conversation=conversation,
            user_message=combined_message,
            message_history=message_history
        )

        # Send response if we have one
        if result.get("response"):
            await send_response(
                company=company,
                lead=lead,
                conversation=conversation,
                sender_phone=sender_phone,
                result=result
            )

    except Exception as e:
        logger.exception(f"[BUFFER] Error processing buffered message: {e}")


async def send_response(
    company,
    lead,
    conversation,
    sender_phone: str,
    result: Dict[str, Any]
):
    """Send response to user via WhatsApp"""
    try:
        # Create WhatsApp service for this company
        wa_service = create_whatsapp_service(
            instance=company.uazapi_instancia,
            token=company.uazapi_token
        )

        response_type = result.get("response_type", "text")
        audio_base64 = result.get("audio_base64")
        send_result = None

        # Handle audio response
        if response_type in ["audio", "both"] and audio_base64:
            try:
                # Send audio as PTT (voice message)
                audio_data = f"data:audio/ogg;base64,{audio_base64}"
                send_result = await wa_service.send_ptt(
                    to=sender_phone,
                    audio_url=audio_data,
                    delay=500  # Show "Recording audio..." for 500ms
                )
                logger.info(f"Audio response sent to {sender_phone}")

                # For "both" mode, also send text
                if response_type == "both":
                    await wa_service.send_text(
                        to=sender_phone,
                        message=result["response"]
                    )
                    logger.info(f"Text response also sent to {sender_phone}")

            except Exception as e:
                logger.error(f"Error sending audio, falling back to text: {e}")
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
        logger.exception(f"Error sending response: {e}")


async def add_to_buffer(
    company_id: int,
    payload: WebhookPayload
):
    """Add message to buffer and set up processing callback"""
    try:
        # Get company
        company = await db.get_company(company_id)
        if not company:
            logger.error(f"Company {company_id} not found")
            return

        # Check if it's a valid inbound message
        if not payload.is_inbound or not payload.message_text:
            logger.info(f"Skipping: is_inbound={payload.is_inbound}, has_text={bool(payload.message_text)}")
            return

        sender_phone = payload.sender_phone
        if not sender_phone:
            logger.error("Could not extract sender phone")
            return

        # Check if lead exists (for new lead notification)
        existing_lead = await db.get_lead_by_phone(company_id, sender_phone)
        is_new_lead = existing_lead is None

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

        # Send notification for new leads
        if is_new_lead:
            await notification_service.notify_new_lead(
                company_id=company_id,
                lead_id=lead.id,
                lead_name=payload.sender_name or lead.nome,
                lead_phone=sender_phone,
                origem="whatsapp"
            )
            logger.info(f"[NOTIFICATION] New lead notification sent for {sender_phone}")

        # Get or create conversation for saving message
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

        # Save inbound message immediately
        await db.save_inbound_message(
            conversation_id=conversation.id,
            lead_id=lead.id,
            content=payload.message_text,
            message_type=payload.message_type,
            media_url=payload.media_url,
            uazapi_message_id=payload.message_id
        )

        # Check if AI is enabled - if not, don't buffer
        if not conversation.ai_enabled or not lead.ai_enabled:
            logger.info(f"AI disabled for conversation {conversation.id}, not buffering")
            return

        # Create callback for when buffer is ready
        async def buffer_callback(combined_text: str, metadata: Dict[str, Any]):
            await process_buffered_message(
                company_id=company_id,
                lead_id=lead.id,
                combined_message=combined_text,
                metadata=metadata
            )

        # Add to buffer
        await buffer_service.add_message(
            company_id=company_id,
            lead_id=lead.id,
            content=payload.message_text,
            message_type=payload.message_type,
            media_url=payload.media_url,
            metadata={
                "sender_phone": sender_phone,
                "sender_name": payload.sender_name,
                "message_id": payload.message_id,
            },
            callback=buffer_callback
        )

        pending_count = buffer_service.get_pending_count(company_id, lead.id)
        logger.info(f"[BUFFER] Message added for {sender_phone}, pending: {pending_count} (debounce: {settings.BUFFER_DEBOUNCE_SECONDS}s)")

    except Exception as e:
        logger.exception(f"Error adding to buffer: {e}")


@router.post("/webhook/{company_id}")
async def receive_webhook(
    company_id: int,
    payload: dict[str, Any],
    background_tasks: BackgroundTasks
):
    """
    Receive webhook from UAZAPI.

    Messages are buffered for 7 seconds to combine rapid messages
    before processing with the AI agent.
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

        # Add to buffer instead of processing immediately
        background_tasks.add_task(add_to_buffer, company_id, webhook)

        return {"status": "received", "buffered": True}

    except Exception as e:
        logger.exception(f"Webhook error: {e}")
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
        "uazapi_configured": bool(company.uazapi_instancia and company.uazapi_token),
        "buffer_debounce_seconds": settings.BUFFER_DEBOUNCE_SECONDS
    }


@router.get("/webhook/buffer/stats")
async def get_buffer_stats():
    """Get buffer statistics"""
    return buffer_service.get_stats()


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

    Messages are buffered for 7 seconds to combine rapid messages
    before processing with the AI agent.
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

        # Add to buffer instead of processing immediately
        background_tasks.add_task(add_to_buffer, company_id, webhook)

        return {"status": "received", "company_id": company_id, "buffered": True}

    except Exception as e:
        logger.exception(f"Global webhook error: {e}")
        return {"status": "error", "message": str(e)}


async def handle_connection_event(company_id: int, webhook: WebhookPayload):
    """Handle connection status change events"""
    try:
        status = webhook.connection_status or ""
        owner = webhook.instance_data.owner if webhook.instance_data else ""

        # Extract phone number from owner (format: 5511999999999@s.whatsapp.net)
        phone = owner.replace("@s.whatsapp.net", "") if owner else None

        logger.info(f"Connection event for company {company_id}: status={status}, phone={phone}")

        # Only update phone number when connected
        if status == "connected" and phone:
            await db.update_company(company_id, {"whatsapp_numero": phone})
            logger.info(f"Updated company {company_id} phone: {phone}")

    except Exception as e:
        logger.exception(f"Error handling connection event: {e}")
