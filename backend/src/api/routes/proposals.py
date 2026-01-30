"""
Proposals API Routes
CRUD operations and status management for proposals.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from ...models.proposal import (
    Proposal, ProposalCreate, ProposalUpdate,
    ProposalStatus, ProposalSend, ProposalResponse
)
from ...services.proposal_service import proposal_service
from ...services.enhanced_followup import enhanced_followup
from ...services.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proposals", tags=["proposals"])


# ==================== CRUD Endpoints ====================

@router.get("")
async def list_proposals(
    company_id: int = Query(..., description="Company ID"),
    lead_id: Optional[int] = Query(None, description="Filter by lead ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    active_only: bool = Query(False, description="Only return active proposals")
):
    """
    List proposals for a company.

    - **company_id**: Required company ID
    - **lead_id**: Optional filter by lead
    - **status**: Optional filter by status (draft, sent, viewed, accepted, rejected, expired)
    - **active_only**: If true, exclude expired/rejected/accepted proposals
    """
    status_enum = None
    if status:
        try:
            status_enum = ProposalStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    proposals = await proposal_service.list_proposals(
        company_id=company_id,
        lead_id=lead_id,
        status=status_enum,
        active_only=active_only
    )

    return proposals


@router.get("/{proposal_id}")
async def get_proposal(proposal_id: int):
    """Get a specific proposal by ID"""
    proposal = await proposal_service.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


@router.post("")
async def create_proposal(proposal: ProposalCreate):
    """
    Create a new proposal.

    The proposal is created in **draft** status and won't be sent until
    the `/send` endpoint is called.
    """
    # Verify lead exists
    lead = await db.get_lead(proposal.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Verify company exists
    company = await db.get_company(proposal.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    created = await proposal_service.create_proposal(proposal)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create proposal")

    return created


@router.put("/{proposal_id}")
async def update_proposal(proposal_id: int, update: ProposalUpdate):
    """Update a proposal (only allowed in draft status)"""
    existing = await proposal_service.get_proposal(proposal_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Only allow updates to draft proposals
    if existing.status not in [ProposalStatus.DRAFT, "draft"]:
        raise HTTPException(
            status_code=400,
            detail="Can only update proposals in draft status"
        )

    updated = await proposal_service.update_proposal(proposal_id, update)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update proposal")

    return updated


@router.delete("/{proposal_id}")
async def delete_proposal(proposal_id: int):
    """Delete a proposal"""
    existing = await proposal_service.get_proposal(proposal_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Proposal not found")

    success = await proposal_service.delete_proposal(proposal_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete proposal")

    return {"status": "deleted", "id": proposal_id}


# ==================== Status Transition Endpoints ====================

@router.post("/{proposal_id}/send")
async def send_proposal(
    proposal_id: int,
    send_data: Optional[ProposalSend] = None,
    background_tasks: BackgroundTasks = None
):
    """
    Send a proposal to the lead.

    This:
    1. Changes status from **draft** to **sent**
    2. Sets the proposal as the lead's active proposal
    3. Schedules follow-up reminders
    4. Sends notification to the company
    """
    existing = await proposal_service.get_proposal(proposal_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if existing.status not in [ProposalStatus.DRAFT, "draft"]:
        raise HTTPException(
            status_code=400,
            detail=f"Can only send proposals in draft status (current: {existing.status})"
        )

    # Send the proposal
    message = send_data.message if send_data else None
    updated = await proposal_service.send_proposal(proposal_id, message)

    if not updated:
        raise HTTPException(status_code=500, detail="Failed to send proposal")

    # Schedule proposal follow-up
    if background_tasks:
        background_tasks.add_task(
            enhanced_followup.schedule_proposal_followup,
            company_id=existing.company_id,
            lead_id=existing.lead_id,
            proposal_id=proposal_id,
            proposal_titulo=existing.titulo,
            dias_restantes=existing.validade_dias
        )

    return {
        "status": "sent",
        "proposal": updated,
        "message": "Proposal sent successfully"
    }


@router.post("/{proposal_id}/view")
async def mark_proposal_viewed(
    proposal_id: int,
    viewer_info: Optional[dict] = None
):
    """
    Mark a proposal as viewed.

    Call this when the lead opens/views the proposal.
    """
    existing = await proposal_service.get_proposal(proposal_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if existing.status not in [ProposalStatus.SENT, "sent", ProposalStatus.VIEWED, "viewed"]:
        raise HTTPException(
            status_code=400,
            detail="Can only mark sent proposals as viewed"
        )

    updated = await proposal_service.mark_viewed(proposal_id, viewer_info)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to mark proposal as viewed")

    return {
        "status": "viewed",
        "proposal": updated
    }


@router.post("/{proposal_id}/accept")
async def accept_proposal(
    proposal_id: int,
    response: Optional[ProposalResponse] = None
):
    """
    Accept a proposal.

    Call this when the lead accepts the proposal.
    """
    existing = await proposal_service.get_proposal(proposal_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if existing.status in [ProposalStatus.ACCEPTED, "accepted", ProposalStatus.REJECTED, "rejected"]:
        raise HTTPException(
            status_code=400,
            detail=f"Proposal already {existing.status}"
        )

    acceptance_details = response.model_dump() if response else None
    updated = await proposal_service.accept_proposal(proposal_id, acceptance_details)

    if not updated:
        raise HTTPException(status_code=500, detail="Failed to accept proposal")

    # Cancel any pending follow-ups for this lead
    await enhanced_followup.cancel_for_lead(
        existing.lead_id,
        reason="Proposal accepted"
    )

    return {
        "status": "accepted",
        "proposal": updated,
        "message": "Congratulations! Proposal accepted."
    }


@router.post("/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: int,
    response: Optional[ProposalResponse] = None
):
    """
    Reject a proposal.

    Optionally include a reason and counter-offer.
    """
    existing = await proposal_service.get_proposal(proposal_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if existing.status in [ProposalStatus.ACCEPTED, "accepted", ProposalStatus.REJECTED, "rejected"]:
        raise HTTPException(
            status_code=400,
            detail=f"Proposal already {existing.status}"
        )

    reason = response.reason if response else None
    counter_offer = response.counter_offer if response else None

    updated = await proposal_service.reject_proposal(
        proposal_id,
        reason=reason,
        counter_offer=counter_offer
    )

    if not updated:
        raise HTTPException(status_code=500, detail="Failed to reject proposal")

    # Cancel follow-ups
    await enhanced_followup.cancel_for_lead(
        existing.lead_id,
        reason="Proposal rejected"
    )

    return {
        "status": "rejected",
        "proposal": updated
    }


@router.post("/{proposal_id}/negotiate")
async def start_negotiation(
    proposal_id: int,
    notes: Optional[str] = None
):
    """
    Mark proposal as in negotiation.

    Use this when the lead wants to discuss terms.
    """
    existing = await proposal_service.get_proposal(proposal_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Proposal not found")

    updated = await proposal_service.mark_negotiating(proposal_id, notes)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update proposal status")

    return {
        "status": "negotiating",
        "proposal": updated
    }


# ==================== Utility Endpoints ====================

@router.get("/lead/{lead_id}/active")
async def get_lead_active_proposal(lead_id: int):
    """Get the active proposal for a lead (if any)"""
    proposal = await proposal_service.get_lead_active_proposal(lead_id)
    if not proposal:
        return {"active_proposal": None}
    return {"active_proposal": proposal}


@router.get("/company/{company_id}/stats")
async def get_proposal_stats(company_id: int):
    """Get proposal statistics for a company"""
    stats = await proposal_service.get_proposal_stats(company_id)
    return stats


@router.post("/expire-check")
async def check_and_expire_proposals():
    """
    Check and expire proposals that are past their expiration date.

    This can be called periodically (e.g., via cron job) or manually.
    """
    count = await proposal_service.expire_due_proposals()
    return {
        "expired_count": count,
        "message": f"Expired {count} proposals"
    }
