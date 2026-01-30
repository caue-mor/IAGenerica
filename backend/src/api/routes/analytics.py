"""
Analytics API Routes
Provides endpoints for dashboard metrics and analytics data.
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional

from ...services.analytics import analytics_service, EventType

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard/{company_id}")
async def get_dashboard(company_id: int):
    """
    Get dashboard summary for a company.

    Returns metrics for today, this week, and this month.
    """
    try:
        summary = await analytics_service.get_dashboard_summary(company_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/funnel/{company_id}")
async def get_funnel_metrics(
    company_id: int,
    days: int = Query(30, ge=1, le=365)
):
    """
    Get funnel metrics for a company.

    Args:
        company_id: Company ID
        days: Number of days to look back (default: 30)
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        metrics = await analytics_service.get_funnel_metrics(
            company_id, start_date
        )
        return metrics.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/field-performance/{company_id}")
async def get_field_performance(
    company_id: int,
    days: int = Query(30, ge=1, le=365)
):
    """
    Get field collection performance (where leads drop off).

    Args:
        company_id: Company ID
        days: Number of days to look back (default: 30)
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        performance = await analytics_service.get_field_performance(
            company_id, start_date
        )
        return [p.to_dict() for p in performance]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline/{company_id}")
async def get_conversion_timeline(
    company_id: int,
    days: int = Query(30, ge=1, le=365),
    granularity: str = Query("day", regex="^(hour|day|week)$")
):
    """
    Get conversion timeline data.

    Args:
        company_id: Company ID
        days: Number of days to look back
        granularity: Time granularity (hour, day, week)
    """
    try:
        timeline = await analytics_service.get_conversion_timeline(
            company_id, days, granularity
        )
        return [
            {
                "timestamp": p.timestamp.isoformat(),
                "value": p.value,
                "label": p.label
            }
            for p in timeline
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/{company_id}")
async def get_recent_events(
    company_id: int,
    limit: int = Query(50, ge=1, le=500),
    event_type: Optional[str] = None
):
    """
    Get recent analytics events.

    Args:
        company_id: Company ID
        limit: Maximum number of events
        event_type: Filter by event type (optional)
    """
    try:
        event_types = None
        if event_type:
            try:
                event_types = [EventType(event_type)]
            except ValueError:
                raise HTTPException(400, f"Invalid event type: {event_type}")

        events = await analytics_service.get_recent_events(
            company_id, limit, event_types
        )
        return events
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lead-journey/{lead_id}")
async def get_lead_journey(lead_id: int):
    """
    Get complete journey for a specific lead.

    Args:
        lead_id: Lead ID
    """
    try:
        journey = await analytics_service.get_lead_journey(lead_id)
        return journey
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/event-types")
async def get_event_types():
    """Get list of available event types."""
    return [e.value for e in EventType]
