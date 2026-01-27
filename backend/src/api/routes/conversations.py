"""
Conversations API routes
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ...services.database import db

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(
    company_id: int = Query(..., description="Company ID"),
    lead_id: Optional[int] = Query(None, description="Filter by lead")
):
    """List all conversations for a company - returns array directly"""
    conversations = await db.list_conversations(company_id, lead_id)

    # Enrich with lead data
    enriched = []
    for conv in conversations:
        conv_dict = conv.model_dump()
        lead = await db.get_lead(conv.lead_id)
        if lead:
            conv_dict["lead"] = lead.model_dump()
        enriched.append(conv_dict)

    return enriched  # Return array directly


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: int):
    """Get a specific conversation"""
    conversation = await db.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Enrich with lead data
    conv_dict = conversation.model_dump()
    lead = await db.get_lead(conversation.lead_id)
    if lead:
        conv_dict["lead"] = lead.model_dump()

    return conv_dict


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    limit: int = Query(50, le=200)
):
    """Get messages for a conversation - returns array directly"""
    conversation = await db.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await db.list_messages(conversation_id, limit)
    return [msg.model_dump() for msg in messages]  # Return array directly


@router.patch("/{conversation_id}/ai")
async def toggle_conversation_ai(
    conversation_id: int,
    enabled: bool = Query(...)
):
    """Enable/disable AI for a conversation"""
    conversation = await db.set_conversation_ai(conversation_id, enabled)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.patch("/{conversation_id}/close")
async def close_conversation(conversation_id: int):
    """Close a conversation"""
    conversation = await db.close_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation
