"""
StudyMate AI - Ollama Local AI Service
All Ollama API communication is centralized here.
Configured via OLLAMA_BASE_URL and OLLAMA_MODEL from environment.
"""
import json
import logging
from typing import Any

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Base exception for Ollama service errors."""
    pass


class OllamaAPIError(OllamaError):
    """Raised when Ollama returns an error or fails to process request."""
    pass


class OllamaConnectionError(OllamaAPIError):
    """Raised when the Ollama server is unreachable."""
    pass


class OllamaModelNotFoundError(OllamaAPIError):
    """Raised when the specified model is not found in Ollama."""
    pass


class OllamaService:
    """Centralized wrapper for all Ollama local AI interactions."""

    def __init__(self):
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout_seconds

    async def check_health(self) -> dict[str, Any]:
        """
        Check whether Ollama is reachable and if the configured model is installed.

        Returns:
            dict with:
                - reachable: bool
                - model_available: bool
                - configured_model: str
                - available_models: list[str]
                - message: str
        """
        result = {
            "reachable": False,
            "model_available": False,
            "configured_model": self.model,
            "available_models": [],
            "message": "",
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    result["reachable"] = True
                    data = response.json()
                    models_raw = data.get("models", [])
                    available_names = [m.get("name", "") for m in models_raw]
                    result["available_models"] = available_names

                    # Normalize model names (e.g. "qwen2.5:7b" matches "qwen2.5:7b" or "qwen2.5:7b-latest")
                    target = self.model.lower()
                    target_base = target.split(":")[0]
                    matched = any(
                        target == name.lower()
                        or name.lower().startswith(f"{target}:")
                        or (":" not in target and name.lower().startswith(f"{target_base}:"))
                        for name in available_names
                    )
                    result["model_available"] = matched

                    if matched:
                        result["message"] = f"Ollama is healthy. Model '{self.model}' is ready."
                    else:
                        result["message"] = (
                            f"Ollama is running, but configured model '{self.model}' was not found. "
                            f"Run `ollama run {self.model}` or check available models: {available_names}"
                        )
                else:
                    result["message"] = f"Ollama returned HTTP status {response.status_code}."
        except httpx.ConnectError:
            result["message"] = (
                f"Cannot connect to Ollama at {self.base_url}. "
                "Ensure Ollama is running (`ollama serve`)."
            )
        except httpx.TimeoutException:
            result["message"] = f"Connection to Ollama at {self.base_url} timed out."
        except Exception as exc:
            logger.error("Error checking Ollama health: %s", exc)
            result["message"] = "Unable to determine Ollama status."

        return result

    async def _chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: str | None = None,
    ) -> str:
        """
        Sends a chat request to Ollama /api/chat.
        Returns the assistant's response text.
        Raises OllamaAPIError or specialized subclasses on failure.
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if response_format == "json":
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )

                if response.status_code == 404:
                    # Model not found error from Ollama
                    detail = response.text
                    logger.error("Ollama model not found: %s", detail)
                    raise OllamaModelNotFoundError(
                        f"Model '{self.model}' was not found in Ollama. "
                        f"Please run `ollama pull {self.model}` in your terminal."
                    )

                response.raise_for_status()
                data = response.json()
                message_content = data.get("message", {}).get("content", "")
                return message_content.strip()

        except httpx.ConnectError as exc:
            logger.error("Cannot connect to Ollama at %s: %s", self.base_url, exc)
            raise OllamaConnectionError(
                f"Ollama server is not reachable at {self.base_url}. "
                "Please make sure Ollama is running (`ollama serve`)."
            ) from exc

        except httpx.TimeoutException as exc:
            logger.error("Ollama request timed out after %ss: %s", self.timeout, exc)
            raise OllamaAPIError(
                f"Ollama took too long to respond ({self.timeout}s timeout). "
                "Try again with a shorter prompt or reduce document length."
            ) from exc

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            logger.error("Ollama HTTP status error %s: %s", status, exc.response.text)
            if status == 404:
                raise OllamaModelNotFoundError(
                    f"Model '{self.model}' not found in Ollama. Run `ollama pull {self.model}`."
                ) from exc
            raise OllamaAPIError(f"Ollama returned error (HTTP {status}).") from exc

        except (KeyError, json.JSONDecodeError) as exc:
            logger.error("Malformed Ollama response: %s", exc)
            raise OllamaAPIError("Received an invalid response format from Ollama.") from exc

        except OllamaAPIError:
            raise

        except Exception as exc:
            logger.error("Unexpected error communicating with Ollama: %s", exc, exc_info=True)
            raise OllamaAPIError("An unexpected error occurred while communicating with the local AI service.") from exc

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        Generate text for a generic prompt. Useful for manual tests and single-prompt generation.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return await self._chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # ------------------------------------------------------------------
    # Domain specific AI functions
    # ------------------------------------------------------------------

    async def generate_summary(
        self,
        document_text: str,
        summary_type: str = "quick",
    ) -> dict[str, Any]:
        """
        Generate a summary of the provided document text.

        Returns:
            dict with keys: quick_summary, detailed_summary, key_points
        """
        truncated = document_text[:12000]

        system_prompt = (
            "You are an expert academic assistant. "
            "Summarize the provided study material accurately and concisely. "
            "Only use information present in the material — do not add external information. "
            "Return your response as valid JSON."
        )

        user_prompt = f"""Analyze this study material and return a JSON object with:
- "quick_summary": A 2-3 sentence overview (plain text).
- "detailed_summary": A thorough paragraph-by-paragraph summary (plain text).
- "key_points": A JSON array of 5-10 important bullet points (each as a string).

Study Material:
\"\"\"
{truncated}
\"\"\"

Return ONLY valid JSON. No markdown backticks, no explanations outside JSON."""

        raw = await self._chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=2048,
            response_format="json",
        )

        try:
            cleaned = raw.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
            return {
                "quick_summary": data.get("quick_summary", ""),
                "detailed_summary": data.get("detailed_summary", ""),
                "key_points": data.get("key_points", []),
            }
        except json.JSONDecodeError:
            logger.warning("Ollama returned non-JSON for summary; fallback wrapping.")
            return {
                "quick_summary": raw[:500],
                "detailed_summary": raw,
                "key_points": [],
            }

    async def answer_question(
        self,
        document_text: str,
        question: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        """
        Answer a question based strictly on the document content.
        """
        truncated = document_text[:10000]
        history = conversation_history or []

        system_prompt = (
            "You are a knowledgeable academic tutor. "
            "Answer questions using ONLY the provided study material. "
            "If the answer is not in the material, clearly say so. "
            "Be clear, accurate, and educational."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Study Material Context:\n\"\"\"\n{truncated}\n\"\"\"",
            },
        ]

        # Add recent conversation history (last 3 turns)
        for msg in history[-6:]:
            messages.append(msg)

        messages.append({"role": "user", "content": question})

        return await self._chat_completion(messages=messages, temperature=0.5)

    async def generate_quiz(
        self,
        document_text: str,
        num_questions: int = 10,
        difficulty: str = "medium",
    ) -> list[dict[str, Any]]:
        """
        Generate multiple-choice quiz questions from document content.
        """
        truncated = document_text[:10000]

        system_prompt = (
            "You are an expert quiz creator for academic materials. "
            "Create clear, unambiguous multiple-choice questions. "
            "Return ONLY a JSON array."
        )

        user_prompt = f"""Create exactly {num_questions} multiple-choice questions at {difficulty} difficulty
based on the following study material. Return a JSON array where each object has:
- "question": the question text
- "option_a": first option
- "option_b": second option
- "option_c": third option
- "option_d": fourth option
- "correct_answer": one of "A", "B", "C", or "D"
- "explanation": why the correct answer is right

Study Material:
\"\"\"
{truncated}
\"\"\"

Return ONLY the JSON array. No markdown, no extra text."""

        raw = await self._chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=4096,
            response_format="json",
        )

        try:
            cleaned = raw.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            questions = json.loads(cleaned)
            # Handle case where Ollama wraps in {"questions": [...]}
            if isinstance(questions, dict):
                for key in ("questions", "quiz", "data"):
                    if key in questions and isinstance(questions[key], list):
                        questions = questions[key]
                        break

            if isinstance(questions, list):
                return questions
            raise ValueError("Expected a JSON array of questions")
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Failed to parse quiz JSON from Ollama: %s (Raw: %s)", exc, raw[:200])
            raise OllamaAPIError("AI returned an invalid quiz format. Please try again.") from exc

    async def generate_exam_questions(
        self,
        document_text: str,
        mark_types: list[str] | None = None,
    ) -> dict[str, list[dict[str, str]]]:
        """
        Generate structured exam questions (2, 5, 10 mark types).
        """
        if mark_types is None:
            mark_types = ["2", "5", "10"]

        truncated = document_text[:10000]

        system_prompt = (
            "You are an experienced exam paper setter. "
            "Generate clear, well-structured exam questions. "
            "Return ONLY valid JSON."
        )

        user_prompt = f"""Generate exam questions for the following study material.
Return a JSON object with keys {mark_types}. Each key maps to an array of objects:
- "question": the exam question
- "sample_answer": a model answer appropriate for that mark type
  (2-mark: 2-3 sentences; 5-mark: a paragraph; 10-mark: detailed explanation)

Generate at least 3 questions per mark type.

Study Material:
\"\"\"
{truncated}
\"\"\"

Return ONLY valid JSON. No markdown, no extra text."""

        raw = await self._chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=4096,
            response_format="json",
        )

        try:
            cleaned = raw.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            result = json.loads(cleaned)
            if isinstance(result, dict):
                return result
            raise ValueError("Expected a JSON object with mark types as keys")
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Failed to parse exam questions JSON: %s (Raw: %s)", exc, raw[:200])
            raise OllamaAPIError("AI returned an invalid exam question format. Please try again.") from exc

    async def generate_study_plan(
        self,
        subjects: list[str],
        topics: list[str],
        exam_date: str,
        available_hours_per_day: float,
        preferred_session_duration: int,
    ) -> dict[str, Any]:
        """
        Generate a personalized study plan.
        """
        system_prompt = (
            "You are a professional academic coach. "
            "Create detailed, realistic, and personalized study plans. "
            "Return ONLY valid JSON."
        )

        user_prompt = f"""Create a personalized study plan with these details:
- Subjects: {', '.join(subjects)}
- Topics to cover: {', '.join(topics)}
- Exam date: {exam_date}
- Available study hours per day: {available_hours_per_day}
- Preferred session duration: {preferred_session_duration} minutes

Return a JSON object with:
- "overview": a brief summary of the plan
- "daily_schedule": an array of objects with:
  - "day": day number (1, 2, ...)
  - "date_label": relative label like "Day 1", "Day 2"
  - "sessions": array of {{"subject": ..., "topic": ..., "duration_minutes": ..., "activity": ...}}
  - "total_hours": total hours for that day
- "study_tips": array of 3-5 actionable study tips
- "milestones": array of key checkpoints

Return ONLY valid JSON. No markdown, no extra text."""

        raw = await self._chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=4096,
            response_format="json",
        )

        try:
            cleaned = raw.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse study plan JSON: %s (Raw: %s)", exc, raw[:200])
            raise OllamaAPIError("AI returned an invalid study plan format.") from exc


# Singleton service instance
ollama_service = OllamaService()
