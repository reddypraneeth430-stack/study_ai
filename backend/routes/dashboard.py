"""
StudyMate AI - Dashboard Routes
GET /api/dashboard/stats
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.database import get_db
from backend.models.models import Document, Quiz, QuizResult, StudyPlan, Conversation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Return aggregated statistics for the dashboard."""

    # Document count
    doc_count_result = await db.execute(select(func.count()).select_from(Document))
    doc_count = doc_count_result.scalar() or 0

    # Quiz count
    quiz_count_result = await db.execute(select(func.count()).select_from(Quiz))
    quiz_count = quiz_count_result.scalar() or 0

    # Quiz results count and average score
    results_count_result = await db.execute(select(func.count()).select_from(QuizResult))
    results_count = results_count_result.scalar() or 0

    avg_score_result = await db.execute(select(func.avg(QuizResult.percentage)).select_from(QuizResult))
    avg_score = avg_score_result.scalar()
    avg_score = round(avg_score, 1) if avg_score else 0.0

    # Study plans count
    plans_count_result = await db.execute(select(func.count()).select_from(StudyPlan))
    plans_count = plans_count_result.scalar() or 0

    # Recent documents (last 5)
    recent_docs_result = await db.execute(
        select(Document).order_by(Document.created_at.desc()).limit(5)
    )
    recent_docs = recent_docs_result.scalars().all()

    # Recent quiz results (last 5)
    recent_results_result = await db.execute(
        select(QuizResult).order_by(QuizResult.completed_at.desc()).limit(5)
    )
    recent_results = recent_results_result.scalars().all()

    # Score distribution for chart (group by percentage ranges)
    all_results_result = await db.execute(
        select(QuizResult.percentage).order_by(QuizResult.completed_at.desc()).limit(50)
    )
    all_scores = [r for r in all_results_result.scalars().all()]

    return {
        "stats": {
            "documents_uploaded": doc_count,
            "quizzes_completed": results_count,
            "average_quiz_score": avg_score,
            "study_plans_created": plans_count,
            "total_quizzes_generated": quiz_count,
        },
        "recent_documents": [
            {
                "id": d.id,
                "original_filename": d.original_filename,
                "file_type": d.file_type,
                "created_at": d.created_at.isoformat(),
            }
            for d in recent_docs
        ],
        "recent_quiz_results": [
            {
                "id": r.id,
                "quiz_id": r.quiz_id,
                "score": r.score,
                "total": r.total,
                "percentage": r.percentage,
                "completed_at": r.completed_at.isoformat(),
            }
            for r in recent_results
        ],
        "score_history": all_scores,
    }
