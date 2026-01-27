"""
Companies API routes
"""
from fastapi import APIRouter, HTTPException
from typing import Any

from ...models import Company, CompanyCreate, CompanyUpdate, FlowConfig
from ...services.database import db
from ...services.whatsapp import create_whatsapp_service

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("")
async def list_companies():
    """List all companies"""
    companies = await db.list_companies()
    return {"companies": companies, "total": len(companies)}


@router.get("/{company_id}")
async def get_company(company_id: int):
    """Get a specific company"""
    company = await db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.post("")
async def create_company(company: CompanyCreate):
    """Create a new company"""
    new_company = await db.create_company(company)
    return new_company


@router.patch("/{company_id}")
async def update_company(company_id: int, company: CompanyUpdate):
    """Update a company"""
    existing = await db.get_company(company_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Company not found")

    updated = await db.update_company(company_id, company)
    return updated


@router.delete("/{company_id}")
async def delete_company(company_id: int):
    """Delete a company"""
    existing = await db.get_company(company_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Company not found")

    await db.delete_company(company_id)
    return {"status": "deleted"}


# ==================== FLOW CONFIG ====================

@router.get("/{company_id}/flow")
async def get_company_flow(company_id: int):
    """Get company flow configuration"""
    company = await db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return {"flow_config": company.flow_config}


@router.put("/{company_id}/flow")
async def update_company_flow(company_id: int, flow_config: dict[str, Any]):
    """Update company flow configuration"""
    import logging
    logger = logging.getLogger(__name__)

    company = await db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Log received payload for debugging
    logger.info(f"Received flow_config: {flow_config}")

    # Validate flow config
    try:
        # Ensure nodes have config if missing
        if "nodes" in flow_config:
            for node in flow_config["nodes"]:
                if "config" not in node or node["config"] is None:
                    node["config"] = {}

        config = FlowConfig(**flow_config)
        logger.info(f"Validated flow config: {config.start_node_id}, {len(config.nodes)} nodes")
    except Exception as e:
        logger.exception(f"Flow config validation error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid flow config: {str(e)}")

    updated = await db.update_company_flow(company_id, config)
    return {"flow_config": updated.flow_config}


# ==================== WHATSAPP ====================

@router.get("/{company_id}/whatsapp/status")
async def check_whatsapp_status(company_id: int):
    """Check WhatsApp connection status"""
    company = await db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not company.uazapi_instancia or not company.uazapi_token:
        return {
            "configured": False,
            "connected": False,
            "message": "UAZAPI not configured"
        }

    wa_service = create_whatsapp_service(
        instance=company.uazapi_instancia,
        token=company.uazapi_token
    )

    status = await wa_service.check_connection()

    return {
        "configured": True,
        "connected": status.get("connected", False),
        "state": status.get("state"),
        "error": status.get("error")
    }


@router.post("/{company_id}/whatsapp/test")
async def test_whatsapp_message(
    company_id: int,
    to: str,
    message: str
):
    """Send a test WhatsApp message"""
    company = await db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not company.uazapi_instancia or not company.uazapi_token:
        raise HTTPException(status_code=400, detail="UAZAPI not configured")

    wa_service = create_whatsapp_service(
        instance=company.uazapi_instancia,
        token=company.uazapi_token
    )

    result = await wa_service.send_text(to=to, message=message)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to send message"))

    return result


# ==================== LEAD STATUSES ====================

@router.get("/{company_id}/statuses")
async def get_company_statuses(company_id: int):
    """Get all lead statuses for a company"""
    company = await db.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    statuses = await db.get_lead_statuses(company_id)
    return {"statuses": statuses}
