"""
Lead Statuses API routes
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ...models import LeadStatus
from ...services.database import db

router = APIRouter(prefix="/lead-statuses", tags=["lead-statuses"])


@router.get("/{company_id}")
async def get_lead_statuses(company_id: int):
    """Get all lead statuses for a company - returns array directly"""
    statuses = await db.get_lead_statuses(company_id)
    return statuses  # Return array directly for frontend compatibility


@router.post("")
async def create_lead_status(
    company_id: int = Query(...),
    nome: str = Query(...),
    cor: str = Query("#6B7280"),
    ordem: int = Query(0)
):
    """Create a new lead status"""
    status = await db.create_lead_status(company_id, nome, cor, ordem)
    return status


@router.get("/{company_id}/default")
async def get_default_status(company_id: int):
    """Get default status for a company"""
    status = await db.get_default_status(company_id)
    if not status:
        raise HTTPException(status_code=404, detail="No default status found")
    return status
