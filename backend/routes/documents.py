"""
StudyMate AI - Document Routes
POST /api/documents/upload
GET  /api/documents
GET  /api/documents/{id}
POST /api/documents/{id}/summary
"""
import logging
from typing import Any

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.models import Document, ExtractedContent
from backend.services.document_service import (
    save_document,
    get_all_documents,
    get_document_by_id,
    get_document_text,
)
from backend.services.ollama_service import (
    ollama_service,
    OllamaAPIError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    created_at: str
    word_count: int | None = None
    page_count: int | None = None

    @classmethod
    def from_orm(cls, doc: Document, extracted: ExtractedContent | None = None) -> "DocumentResponse":
        return cls(
            id=doc.id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            created_at=doc.created_at.isoformat(),
            word_count=extracted.word_count if extracted else None,
            page_count=extracted.page_count if extracted else None,
        )


class SummaryResponse(BaseModel):
    document_id: str
    quick_summary: str
    detailed_summary: str
    key_points: list[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload a PDF, DOCX, or TXT study material."""
    logger.info("Upload request received: filename='%s'", file.filename)
    content = await file.read()
    doc = await save_document(file, content, db)

    # Get extracted content for word/page count
    result = await db.execute(
        select(ExtractedContent).where(ExtractedContent.document_id == doc.id)
    )
    extracted = result.scalar_one_or_none()
    word_count = extracted.word_count if extracted else None
    logger.info("Document saved successfully: doc_id=%s, word_count=%s", doc.id, word_count)

    return {
        "message": "Document uploaded and processed successfully.",
        "document": DocumentResponse.from_orm(doc, extracted).model_dump(),
    }


@router.get("")
async def list_documents(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """List all uploaded documents."""
    docs = await get_all_documents(db)

    result_list = []
    for doc in docs:
        res = await db.execute(
            select(ExtractedContent).where(ExtractedContent.document_id == doc.id)
        )
        extracted = res.scalar_one_or_none()
        result_list.append(DocumentResponse.from_orm(doc, extracted).model_dump())

    return {"documents": result_list, "total": len(result_list)}


@router.get("/{document_id}")
async def get_document(
    document_id: str, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Get a single document by ID."""
    doc = await get_document_by_id(document_id, db)
    result = await db.execute(
        select(ExtractedContent).where(ExtractedContent.document_id == doc.id)
    )
    extracted = result.scalar_one_or_none()
    return {"document": DocumentResponse.from_orm(doc, extracted).model_dump()}


@router.post("/{document_id}/summary")
async def generate_summary(
    document_id: str, db: AsyncSession = Depends(get_db)
) -> SummaryResponse:
    """Generate an AI summary for the specified document."""
    # Get the document text
    text = await get_document_text(document_id, db)
    logger.info("Summary requested for document_id=%s (text_length=%d chars)", document_id, len(text))

    # Call Ollama
    try:
        summary_data = await ollama_service.generate_summary(text)
    except OllamaConnectionError as exc:
        logger.error("Ollama connection error for document_id=%s: %s", document_id, exc)
        raise HTTPException(status_code=503, detail=str(exc))
    except OllamaModelNotFoundError as exc:
        logger.error("Ollama model not found for document_id=%s: %s", document_id, exc)
        raise HTTPException(status_code=503, detail=str(exc))
    except OllamaAPIError as exc:
        logger.error("Ollama API error for document_id=%s: %s", document_id, exc)
        raise HTTPException(status_code=502, detail=str(exc))

    # Persist summaries back to ExtractedContent
    result = await db.execute(
        select(ExtractedContent).where(ExtractedContent.document_id == document_id)
    )
    extracted = result.scalar_one_or_none()
    if extracted:
        import json
        extracted.quick_summary = summary_data.get("quick_summary", "")
        extracted.detailed_summary = summary_data.get("detailed_summary", "")
        key_points = summary_data.get("key_points", [])
        extracted.key_points = json.dumps(key_points)
        await db.commit()

    logger.info("Summary generated successfully for document_id=%s", document_id)

    return SummaryResponse(
        document_id=document_id,
        quick_summary=summary_data.get("quick_summary", ""),
        detailed_summary=summary_data.get("detailed_summary", ""),
        key_points=summary_data.get("key_points", []),
    )
