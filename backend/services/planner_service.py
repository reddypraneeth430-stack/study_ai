"""
StudyMate AI - Planner Service (thin wrapper over GrokService)
Provides study-plan-specific business logic.
"""
from datetime import datetime, date


def days_until_exam(exam_date_str: str) -> int:
    """Calculate days remaining until the exam."""
    try:
        exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
        today = date.today()
        delta = (exam_date - today).days
        return max(0, delta)
    except ValueError:
        return 0


def validate_plan_inputs(
    subjects: list[str],
    topics: list[str],
    exam_date: str,
    available_hours: float,
) -> list[str]:
    """Validate study plan inputs. Returns list of error messages (empty = valid)."""
    errors = []

    if not subjects:
        errors.append("At least one subject is required.")
    if not topics:
        errors.append("At least one topic is required.")

    try:
        exam_dt = datetime.strptime(exam_date, "%Y-%m-%d").date()
        if exam_dt <= date.today():
            errors.append("Exam date must be in the future.")
    except ValueError:
        errors.append("Invalid exam date format. Use YYYY-MM-DD.")

    if available_hours <= 0:
        errors.append("Available hours must be greater than 0.")

    return errors
