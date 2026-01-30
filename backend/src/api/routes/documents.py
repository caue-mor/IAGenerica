"""
Documents API Routes
Document extraction and processing endpoints.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, HttpUrl
import base64

from ...services.document_extractor import (
    document_extractor,
    DocumentType,
    ExtractionResult
)
from ...services.database import db
from ...services.notification import notification_service, NotificationType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# ==================== Request/Response Models ====================

class ExtractFromURLRequest(BaseModel):
    """Request model for extracting from URL"""
    document_url: str
    document_type: Optional[str] = None
    custom_fields: Optional[List[str]] = None
    lead_id: Optional[int] = None
    company_id: Optional[int] = None


class ExtractFromBase64Request(BaseModel):
    """Request model for extracting from base64"""
    document_base64: str
    document_type: Optional[str] = None
    custom_fields: Optional[List[str]] = None
    lead_id: Optional[int] = None
    company_id: Optional[int] = None


class ExtractionResponse(BaseModel):
    """Response model for extraction"""
    success: bool
    document_type: str
    document_type_confidence: float
    fields: dict
    summary: Optional[str]
    errors: List[str]
    lead_updated: bool = False


# ==================== Extraction Endpoints ====================

@router.post("/extract")
async def extract_document(request: ExtractFromURLRequest) -> ExtractionResponse:
    """
    Extract data from a document via URL.

    Supports:
    - Images (JPEG, PNG, WebP)
    - PDFs (first page is analyzed)

    Document types:
    - conta_luz, conta_agua, fatura, nota_fiscal
    - orcamento, proposta, contrato
    - rg, cnh, cpf, comprovante_residencia
    - formulario, documento (generic)

    If document_type is not provided, it will be auto-detected.
    """
    # Validate document type if provided
    doc_type = None
    if request.document_type:
        try:
            doc_type = DocumentType(request.document_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid document_type. Valid types: {[t.value for t in DocumentType]}"
            )

    # Extract data
    result = await document_extractor.extract(
        document_url=request.document_url,
        document_type=doc_type,
        custom_fields=request.custom_fields
    )

    lead_updated = False

    # If lead_id provided, update lead data
    if request.lead_id and result.success:
        try:
            lead = await db.get_lead(request.lead_id)
            if lead:
                # Merge extracted data with existing
                validated_data = result.get_validated_data()
                if validated_data:
                    existing_data = lead.dados_coletados or {}
                    merged_data = {**existing_data, **validated_data}

                    from ...models import LeadUpdate
                    await db.update_lead(request.lead_id, LeadUpdate(dados_coletados=merged_data))
                    lead_updated = True

                    logger.info(f"Updated lead {request.lead_id} with extracted data: {list(validated_data.keys())}")

                    # Send notification
                    if request.company_id:
                        await notification_service.notify_document_received(
                            company_id=request.company_id,
                            lead_id=request.lead_id,
                            document_type=result.document_type.value,
                            lead_name=lead.nome
                        )
        except Exception as e:
            logger.error(f"Failed to update lead with extracted data: {e}")

    return ExtractionResponse(
        success=result.success,
        document_type=result.document_type.value,
        document_type_confidence=result.document_type_confidence,
        fields={
            name: {
                "value": f.value,
                "confidence": f.confidence,
                "validated": f.validated,
                "validation_error": f.validation_error
            }
            for name, f in result.fields.items()
        },
        summary=result.summary,
        errors=result.errors,
        lead_updated=lead_updated
    )


@router.post("/extract-base64")
async def extract_document_base64(request: ExtractFromBase64Request) -> ExtractionResponse:
    """
    Extract data from a document provided as base64.

    Same functionality as /extract but accepts base64 encoded image.
    """
    # Validate document type if provided
    doc_type = None
    if request.document_type:
        try:
            doc_type = DocumentType(request.document_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid document_type. Valid types: {[t.value for t in DocumentType]}"
            )

    # Extract data
    result = await document_extractor.extract(
        document_base64=request.document_base64,
        document_type=doc_type,
        custom_fields=request.custom_fields
    )

    lead_updated = False

    # If lead_id provided, update lead data
    if request.lead_id and result.success:
        try:
            lead = await db.get_lead(request.lead_id)
            if lead:
                validated_data = result.get_validated_data()
                if validated_data:
                    existing_data = lead.dados_coletados or {}
                    merged_data = {**existing_data, **validated_data}

                    from ...models import LeadUpdate
                    await db.update_lead(request.lead_id, LeadUpdate(dados_coletados=merged_data))
                    lead_updated = True

                    if request.company_id:
                        await notification_service.notify_document_received(
                            company_id=request.company_id,
                            lead_id=request.lead_id,
                            document_type=result.document_type.value,
                            lead_name=lead.nome
                        )
        except Exception as e:
            logger.error(f"Failed to update lead with extracted data: {e}")

    return ExtractionResponse(
        success=result.success,
        document_type=result.document_type.value,
        document_type_confidence=result.document_type_confidence,
        fields={
            name: {
                "value": f.value,
                "confidence": f.confidence,
                "validated": f.validated,
                "validation_error": f.validation_error
            }
            for name, f in result.fields.items()
        },
        summary=result.summary,
        errors=result.errors,
        lead_updated=lead_updated
    )


@router.post("/extract-upload")
async def extract_document_upload(
    file: UploadFile = File(...),
    document_type: Optional[str] = Query(None),
    lead_id: Optional[int] = Query(None),
    company_id: Optional[int] = Query(None)
) -> ExtractionResponse:
    """
    Extract data from an uploaded document file.

    Accepts image files (JPEG, PNG, WebP) up to 10MB.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {allowed_types}"
        )

    # Read and encode file
    contents = await file.read()

    # Check file size (10MB max)
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB."
        )

    document_base64 = base64.b64encode(contents).decode()

    # Validate document type if provided
    doc_type = None
    if document_type:
        try:
            doc_type = DocumentType(document_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid document_type. Valid types: {[t.value for t in DocumentType]}"
            )

    # Extract data
    result = await document_extractor.extract(
        document_base64=document_base64,
        document_type=doc_type
    )

    lead_updated = False

    # If lead_id provided, update lead data
    if lead_id and result.success:
        try:
            lead = await db.get_lead(lead_id)
            if lead:
                validated_data = result.get_validated_data()
                if validated_data:
                    existing_data = lead.dados_coletados or {}
                    merged_data = {**existing_data, **validated_data}

                    from ...models import LeadUpdate
                    await db.update_lead(lead_id, LeadUpdate(dados_coletados=merged_data))
                    lead_updated = True

                    if company_id:
                        await notification_service.notify_document_received(
                            company_id=company_id,
                            lead_id=lead_id,
                            document_type=result.document_type.value,
                            lead_name=lead.nome
                        )
        except Exception as e:
            logger.error(f"Failed to update lead with extracted data: {e}")

    return ExtractionResponse(
        success=result.success,
        document_type=result.document_type.value,
        document_type_confidence=result.document_type_confidence,
        fields={
            name: {
                "value": f.value,
                "confidence": f.confidence,
                "validated": f.validated,
                "validation_error": f.validation_error
            }
            for name, f in result.fields.items()
        },
        summary=result.summary,
        errors=result.errors,
        lead_updated=lead_updated
    )


# ==================== Utility Endpoints ====================

@router.get("/types")
async def list_document_types():
    """List all supported document types"""
    return {
        "document_types": [
            {"value": t.value, "name": t.name}
            for t in DocumentType
        ]
    }


@router.post("/classify")
async def classify_document(request: ExtractFromURLRequest):
    """
    Classify a document without extracting data.

    Returns only the document type and confidence score.
    """
    # Use extract but we only care about classification
    result = await document_extractor.extract(
        document_url=request.document_url,
        document_type=None,  # Force classification
        custom_fields=[]  # No extraction needed
    )

    return {
        "document_type": result.document_type.value,
        "confidence": result.document_type_confidence,
        "success": result.success
    }
