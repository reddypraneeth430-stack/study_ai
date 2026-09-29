"""
StudyMate AI - Quiz Service (business logic for quizzes)
Provides quiz-specific business logic beyond raw AI calls.
"""
from backend.services.ollama_service import ollama_service, OllamaAPIError


async def validate_quiz_answers(
    questions: list[dict],
    answers: dict[str, str],
) -> dict:
    """
    Validate submitted quiz answers against correct answers.
    Returns scoring details.
    """
    score = 0
    results = []
    for q in questions:
        qid = q["id"]
        selected = answers.get(qid, "").upper()
        correct = q["correct_answer"].upper()
        is_correct = selected == correct
        if is_correct:
            score += 1
        results.append({
            "question_id": qid,
            "selected": selected,
            "correct": correct,
            "is_correct": is_correct,
        })

    total = len(questions)
    percentage = round((score / total * 100) if total else 0, 1)
    return {"score": score, "total": total, "percentage": percentage, "results": results}
