"""
StudyMate AI - Quiz Routes
POST /api/documents/{id}/quiz  — generate quiz
POST /api/quiz/{id}/submit     — submit answers & get results
GET  /api/quiz/{id}            — get quiz details
GET  /api/quiz/results         — get all results
"""
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.models import Quiz, QuizQuestion, QuizResult
from backend.services.ollama_service import (
    ollama_service,
    OllamaAPIError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["quiz"])


class GenerateQuizRequest(BaseModel):
    num_questions: int = Field(default=10, ge=5, le=20)
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")


class SubmitQuizRequest(BaseModel):
    answers: dict[str, str]  # {question_id: selected_option ("A"|"B"|"C"|"D")}


@router.post("/api/documents/{document_id}/quiz", status_code=201)
async def generate_quiz(
    document_id: str,
    body: GenerateQuizRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate an MCQ quiz for the specified document."""
    doc = await get_document_by_id(document_id, db)
    text = await get_document_text(document_id, db)

    try:
        questions_data = await ollama_service.generate_quiz(
            document_text=text,
            num_questions=body.num_questions,
            difficulty=body.difficulty,
        )
    except OllamaConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except OllamaModelNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except OllamaAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Persist quiz
    quiz = Quiz(
        document_id=document_id,
        title=f"{body.difficulty.capitalize()} Quiz — {doc.original_filename[:40]}",
        difficulty=body.difficulty,
        num_questions=len(questions_data),
    )
    db.add(quiz)
    await db.flush()

    questions_out = []
    for idx, q in enumerate(questions_data):
        qq = QuizQuestion(
            quiz_id=quiz.id,
            order_index=idx,
            question_text=q.get("question", ""),
            option_a=q.get("option_a", ""),
            option_b=q.get("option_b", ""),
            option_c=q.get("option_c", ""),
            option_d=q.get("option_d", ""),
            correct_answer=q.get("correct_answer", "A").upper(),
            explanation=q.get("explanation", ""),
        )
        db.add(qq)
        await db.flush()
        questions_out.append({
            "id": qq.id,
            "order_index": idx,
            "question": qq.question_text,
            "option_a": qq.option_a,
            "option_b": qq.option_b,
            "option_c": qq.option_c,
            "option_d": qq.option_d,
            # NOTE: correct_answer NOT included in response (revealed after submission)
        })

    await db.commit()

    return {
        "quiz_id": quiz.id,
        "title": quiz.title,
        "difficulty": quiz.difficulty,
        "num_questions": quiz.num_questions,
        "questions": questions_out,
    }


@router.get("/api/quiz/{quiz_id}")
async def get_quiz(quiz_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Get quiz details (without answers)."""
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    q_result = await db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == quiz_id)
        .order_by(QuizQuestion.order_index)
    )
    questions = q_result.scalars().all()

    return {
        "quiz_id": quiz.id,
        "title": quiz.title,
        "difficulty": quiz.difficulty,
        "questions": [
            {
                "id": q.id,
                "order_index": q.order_index,
                "question": q.question_text,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
            }
            for q in questions
        ],
    }


@router.post("/api/quiz/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: str,
    body: SubmitQuizRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Submit quiz answers and get scored results with explanations."""
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    q_result = await db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == quiz_id)
        .order_by(QuizQuestion.order_index)
    )
    questions = list(q_result.scalars().all())

    score = 0
    detailed_results = []
    for q in questions:
        selected = body.answers.get(q.id, "").upper()
        is_correct = selected == q.correct_answer
        if is_correct:
            score += 1
        detailed_results.append({
            "question_id": q.id,
            "question": q.question_text,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d,
            "selected": selected,
            "correct_answer": q.correct_answer,
            "is_correct": is_correct,
            "explanation": q.explanation,
        })

    total = len(questions)
    percentage = round((score / total * 100) if total > 0 else 0, 1)

    # Persist result
    quiz_result = QuizResult(
        quiz_id=quiz_id,
        score=score,
        total=total,
        percentage=percentage,
        answers=json.dumps(body.answers),
    )
    db.add(quiz_result)
    await db.commit()

    return {
        "quiz_id": quiz_id,
        "result_id": quiz_result.id,
        "score": score,
        "total": total,
        "percentage": percentage,
        "results": detailed_results,
    }
