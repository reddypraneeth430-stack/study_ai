"""
StudyMate AI - Document Service
Handles file validation, saving, and database operations for documents.
"""
import logging
import re
import uuid
from pathlib import Path

from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.config import settings
from backend.models.models import Document, ExtractedContent
from backend.utils.document_parser import extract_text, count_words, DocumentParseError

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


def sanitize_filename(filename: str) -> str:
    """Remove unsafe characters from filenames."""
    # Strip directory traversal sequences
    name = re.sub(r"\.{2,}", "", filename)
    # Replace spaces with underscores, remove everything except alphanumeric, dots, underscores, hyphens
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^\w\-.]", "", name)
    # Truncate to 200 chars to avoid filesystem limits
    return name[:200] if name else "upload"


def validate_upload(file: UploadFile, content: bytes) -> str:
    """
    Validate uploaded file. Returns the file extension.
    Raises HTTPException on failure.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="File has no name.")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    file_size = len(content)
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    max_bytes = settings.max_file_size_bytes
    if file_size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({file_size // (1024*1024)} MB). Maximum: {settings.max_file_size_mb} MB.",
        )

    return ext


async def save_document(
    file: UploadFile,
    content: bytes,
    db: AsyncSession,
) -> Document:
    """
    Validate, save, extract text, and persist document to database.
    Returns the created Document ORM object.
    """
    ext = validate_upload(file, content)

    # Build a safe unique filename
    unique_id = uuid.uuid4().hex[:8]
    safe_name = sanitize_filename(Path(file.filename).stem)
    stored_filename = f"{safe_name}_{unique_id}{ext}"

    # Ensure upload directory exists
    upload_path = settings.upload_path
    file_path = upload_path / stored_filename

    # Write file to disk
    try:
        file_path.write_bytes(content)
    except OSError as exc:
        logger.error("Failed to write uploaded file: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    # Extract text
    try:
        raw_text, page_count = extract_text(file_path)
    except DocumentParseError as exc:
        # Clean up saved file on extraction failure
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc))

    if not raw_text or not raw_text.strip():
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422,
            detail="The uploaded document contains no readable text.",
        )

    word_count = count_words(raw_text)

    # Persist Document record
    doc = Document(
        filename=stored_filename,
        original_filename=file.filename,
        file_type=ext.lstrip("."),
        file_size=len(content),
        file_path=str(file_path),
    )
    db.add(doc)
    await db.flush()  # get doc.id before creating child

    # Persist ExtractedContent record
    extracted = ExtractedContent(
        document_id=doc.id,
        raw_text=raw_text,
        page_count=page_count,
        word_count=word_count,
    )
    db.add(extracted)
    await db.commit()
    await db.refresh(doc)

    logger.info("Saved document '%s' (%s) with %d words.", stored_filename, ext, word_count)
    return doc


async def get_all_documents(db: AsyncSession) -> list[Document]:
    """Return all documents ordered by newest first."""
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def get_document_by_id(document_id: str, db: AsyncSession) -> Document:
    """Return a document by ID or raise 404."""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )
    return doc


async def get_document_text(document_id: str, db: AsyncSession) -> str:
    """Return the extracted text for a document, or raise 404."""
    result = await db.execute(
        select(ExtractedContent).where(ExtractedContent.document_id == document_id)
    )
    extracted = result.scalar_one_or_none()
    if not extracted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extracted content not found for this document.",
        )
    return extracted.raw_text
