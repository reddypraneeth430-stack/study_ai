"""
StudyMate AI - Study Planner Routes
POST /api/planner/generate
GET  /api/planner/{id}
PUT  /api/planner/{id}
GET  /api/planner
"""
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.models import StudyPlan
from backend.services.ollama_service import (
    ollama_service,
    OllamaAPIError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/planner", tags=["planner"])


class GeneratePlanRequest(BaseModel):
    subjects: list[str] = Field(..., min_length=1)
    topics: list[str] = Field(..., min_length=1)
    exam_date: str = Field(..., description="ISO date, e.g. 2024-12-15")
    available_hours_per_day: float = Field(default=4.0, ge=0.5, le=16.0)
    preferred_session_duration: int = Field(default=45, ge=15, le=120)


class UpdatePlanRequest(BaseModel):
    plan_content: str  # Updated plan JSON as string


@router.post("/generate", status_code=201)
async def generate_plan(
    body: GeneratePlanRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate a personalized AI study plan."""
    try:
        plan_data = await ollama_service.generate_study_plan(
            subjects=body.subjects,
            topics=body.topics,
            exam_date=body.exam_date,
            available_hours_per_day=body.available_hours_per_day,
            preferred_session_duration=body.preferred_session_duration,
        )
    except OllamaConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except OllamaModelNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except OllamaAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    title = f"Study Plan — {', '.join(body.subjects[:2])}"
    plan = StudyPlan(
        title=title,
        subjects=json.dumps(body.subjects),
        topics=json.dumps(body.topics),
        exam_date=body.exam_date,
        available_hours_per_day=body.available_hours_per_day,
        preferred_session_duration=body.preferred_session_duration,
        plan_content=json.dumps(plan_data),
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return {
        "plan_id": plan.id,
        "title": plan.title,
        "exam_date": plan.exam_date,
        "plan": plan_data,
        "created_at": plan.created_at.isoformat(),
    }


@router.get("")
async def list_plans(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """List all study plans."""
    result = await db.execute(
        select(StudyPlan).order_by(StudyPlan.created_at.desc())
    )
    plans = result.scalars().all()
    return {
        "plans": [
            {
                "plan_id": p.id,
                "title": p.title,
                "exam_date": p.exam_date,
                "subjects": json.loads(p.subjects),
                "is_edited": p.is_edited,
                "created_at": p.created_at.isoformat(),
            }
            for p in plans
        ]
    }


@router.get("/{plan_id}")
async def get_plan(plan_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Get a specific study plan."""
    result = await db.execute(select(StudyPlan).where(StudyPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found.")

    return {
        "plan_id": plan.id,
        "title": plan.title,
        "exam_date": plan.exam_date,
        "subjects": json.loads(plan.subjects),
        "topics": json.loads(plan.topics),
        "available_hours_per_day": plan.available_hours_per_day,
        "preferred_session_duration": plan.preferred_session_duration,
        "plan": json.loads(plan.plan_content),
        "is_edited": plan.is_edited,
        "created_at": plan.created_at.isoformat(),
        "updated_at": plan.updated_at.isoformat(),
    }


@router.put("/{plan_id}")
async def update_plan(
    plan_id: str,
    body: UpdatePlanRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update (edit) a study plan's content."""
    result = await db.execute(select(StudyPlan).where(StudyPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found.")

    # Validate it's valid JSON
    try:
        json.loads(body.plan_content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="plan_content must be valid JSON.")

    plan.plan_content = body.plan_content
    plan.is_edited = True
    await db.commit()

    return {"message": "Plan updated successfully.", "plan_id": plan_id}
