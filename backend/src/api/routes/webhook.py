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
        if not payload.is_inbound or not payload.message_text:
            logger.info(f"Skipping non-inbound or empty message")
            return

        sender_phone = payload.sender_phone
        if not sender_phone:
            logger.error("Could not extract sender phone")
            return

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

            # Send message
            send_result = await wa_service.send_text(
                to=sender_phone,
                message=result["response"]
            )

            # Save outbound message
            await db.save_outbound_message(
                conversation_id=conversation.id,
                lead_id=lead.id,
                content=result["response"],
                uazapi_message_id=send_result.get("message_id")
            )

            logger.info(f"Response sent to {sender_phone}")

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
        # Parse payload
        webhook = parse_webhook(payload)

        logger.info(f"Received webhook: event={webhook.event}, company={company_id}")

        # Only process message events
        if not webhook.is_message_event:
            return {"status": "ignored", "reason": "not a message event"}

        # Process in background to respond quickly
        background_tasks.add_task(process_message, company_id, webhook)

        return {"status": "received"}

    except Exception as e:
        logger.exception(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
