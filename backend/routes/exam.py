"""
StudyMate AI - Exam Preparation Routes
POST /api/exam/generate
GET  /api/exam/{id}
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.models import ExamSet, ExamQuestion
from backend.services.document_service import get_document_by_id, get_document_text
from backend.services.ollama_service import (
    ollama_service,
    OllamaAPIError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/exam", tags=["exam"])


class GenerateExamRequest(BaseModel):
    document_id: str
    mark_types: list[str] = Field(default=["2", "5", "10"])


@router.post("/generate", status_code=201)
async def generate_exam(
    body: GenerateExamRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate 2-mark, 5-mark, and 10-mark exam questions from a document."""
    doc = await get_document_by_id(body.document_id, db)
    text = await get_document_text(body.document_id, db)

    valid_marks = {"2", "5", "10"}
    mark_types = [m for m in body.mark_types if m in valid_marks]
    if not mark_types:
        raise HTTPException(status_code=400, detail="Provide valid mark_types: '2', '5', or '10'.")

    try:
        exam_data = await ollama_service.generate_exam_questions(
            document_text=text,
            mark_types=mark_types,
        )
    except OllamaConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except OllamaModelNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except OllamaAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Persist exam set
    exam_set = ExamSet(
        document_id=body.document_id,
        title=f"Exam Prep — {doc.original_filename[:40]}",
    )
    db.add(exam_set)
    await db.flush()

    questions_out: dict[str, list] = {}
    order = 0
    for mark_type, questions in exam_data.items():
        if not isinstance(questions, list):
            continue
        questions_out[mark_type] = []
        for q in questions:
            eq = ExamQuestion(
                exam_set_id=exam_set.id,
                question_text=q.get("question", ""),
                mark_type=mark_type,
                sample_answer=q.get("sample_answer", ""),
                order_index=order,
            )
            db.add(eq)
            await db.flush()
            questions_out[mark_type].append({
                "id": eq.id,
                "question": eq.question_text,
                "mark_type": mark_type,
                "sample_answer": eq.sample_answer,
            })
            order += 1

    await db.commit()

    return {
        "exam_set_id": exam_set.id,
        "title": exam_set.title,
        "document_id": body.document_id,
        "questions": questions_out,
    }


@router.get("/{exam_set_id}")
async def get_exam(
    exam_set_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve an exam set by ID."""
    result = await db.execute(select(ExamSet).where(ExamSet.id == exam_set_id))
    exam_set = result.scalar_one_or_none()
    if not exam_set:
        raise HTTPException(status_code=404, detail="Exam set not found.")

    q_result = await db.execute(
        select(ExamQuestion)
        .where(ExamQuestion.exam_set_id == exam_set_id)
        .order_by(ExamQuestion.order_index)
    )
    questions = q_result.scalars().all()

    grouped: dict[str, list] = {}
    for q in questions:
        grouped.setdefault(q.mark_type, []).append({
            "id": q.id,
            "question": q.question_text,
            "mark_type": q.mark_type,
            "sample_answer": q.sample_answer,
        })

    return {
        "exam_set_id": exam_set.id,
        "title": exam_set.title,
        "created_at": exam_set.created_at.isoformat(),
        "questions": grouped,
    }
