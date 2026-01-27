"""
Leads API routes
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ...models import Lead, LeadCreate, LeadUpdate, LeadStatus, Conversation, Message
from ...services.database import db

router = APIRouter(prefix="/leads", tags=["leads"])


# ==================== LEADS ====================

@router.get("")
async def list_leads(
    company_id: int = Query(..., description="Company ID"),
    status_id: Optional[int] = Query(None, description="Filter by status")
):
    """List all leads for a company - returns array directly"""
    leads = await db.list_leads(company_id, status_id)
    return leads  # Return array directly for frontend compatibility


@router.get("/{lead_id}")
async def get_lead(lead_id: int):
    """Get a specific lead"""
    lead = await db.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("")
async def create_lead(lead: LeadCreate):
    """Create a new lead"""
    # Check if lead already exists
    existing = await db.get_lead_by_phone(lead.company_id, lead.celular)
    if existing:
        raise HTTPException(status_code=400, detail="Lead with this phone already exists")

    new_lead = await db.create_lead(lead)
    return new_lead


@router.patch("/{lead_id}")
async def update_lead(lead_id: int, lead: LeadUpdate):
    """Update a lead"""
    existing = await db.get_lead(lead_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Lead not found")

    updated = await db.update_lead(lead_id, lead)
    return updated


@router.delete("/{lead_id}")
async def delete_lead(lead_id: int):
    """Delete a lead"""
    existing = await db.get_lead(lead_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Lead not found")

    await db.delete_lead(lead_id)
    return {"status": "deleted"}


@router.patch("/{lead_id}/status/{status_id}")
async def update_lead_status(lead_id: int, status_id: int):
    """Update lead status (kanban move)"""
    lead = await db.update_lead_status(lead_id, status_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/{lead_id}/ai")
async def toggle_lead_ai(lead_id: int, enabled: bool = Query(...)):
    """Enable/disable AI for a lead"""
    lead = await db.set_lead_ai(lead_id, enabled)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


# ==================== LEAD STATUSES ====================

@router.get("/statuses/{company_id}")
async def get_lead_statuses(company_id: int):
    """Get all lead statuses for a company"""
    statuses = await db.get_lead_statuses(company_id)
    return {"statuses": statuses}


@router.post("/statuses")
async def create_lead_status(
    company_id: int = Query(...),
    nome: str = Query(...),
    cor: str = Query("#6B7280"),
    ordem: int = Query(0)
):
    """Create a new lead status"""
    status = await db.create_lead_status(company_id, nome, cor, ordem)
    return status


# ==================== CONVERSATIONS ====================

@router.get("/{lead_id}/conversations")
async def get_lead_conversations(lead_id: int):
    """Get all conversations for a lead"""
    lead = await db.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    conversations = await db.list_conversations(lead.company_id, lead_id)
    return {"conversations": conversations}


@router.get("/{lead_id}/conversations/active")
async def get_active_conversation(lead_id: int):
    """Get the active conversation for a lead"""
    conversation = await db.get_active_conversation(lead_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="No active conversation")
    return conversation


# ==================== MESSAGES ====================

@router.get("/{lead_id}/messages")
async def get_lead_messages(
    lead_id: int,
    limit: int = Query(50, le=200)
):
    """Get messages for a lead's active conversation"""
    conversation = await db.get_active_conversation(lead_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="No active conversation")

    messages = await db.list_messages(conversation.id, limit)
    return {"messages": messages, "conversation_id": conversation.id}


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    limit: int = Query(50, le=200)
):
    """Get messages for a specific conversation"""
    conversation = await db.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await db.list_messages(conversation_id, limit)
    return {"messages": messages}
