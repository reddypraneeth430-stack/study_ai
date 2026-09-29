"""
StudyMate AI - Chat / Q&A Routes
POST /api/documents/{id}/chat
GET  /api/documents/{id}/conversations
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models.models import Conversation, Message
from backend.services.document_service import get_document_by_id, get_document_text
from backend.services.ollama_service import (
    ollama_service,
    OllamaAPIError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["chat"])


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    question: str
    answer: str


@router.post("/{document_id}/chat")
async def chat_with_document(
    document_id: str,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Ask a question about a specific document."""
    # Validate document exists
    doc = await get_document_by_id(document_id, db)
    text = await get_document_text(document_id, db)

    # Get or create conversation
    conversation: Conversation | None = None
    if body.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == body.conversation_id,
                Conversation.document_id == document_id,
            )
        )
        conversation = result.scalar_one_or_none()

    if not conversation:
        conversation = Conversation(
            document_id=document_id,
            title=f"Chat about {doc.original_filename[:40]}",
        )
        db.add(conversation)
        await db.flush()

    # Build conversation history for context
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    history_msgs = list(reversed(result.scalars().all()))
    history = [{"role": m.role, "content": m.content} for m in history_msgs]

    # Call Ollama
    try:
        answer = await ollama_service.answer_question(
            document_text=text,
            question=body.question,
            conversation_history=history,
        )
    except OllamaConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except OllamaModelNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except OllamaAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Save messages
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=body.question,
    )
    ai_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
    )
    db.add(user_msg)
    db.add(ai_msg)
    await db.commit()

    return ChatResponse(
        conversation_id=conversation.id,
        question=body.question,
        answer=answer,
    )


@router.get("/{document_id}/conversations")
async def list_conversations(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all conversations for a document."""
    await get_document_by_id(document_id, db)
    result = await db.execute(
        select(Conversation)
        .where(Conversation.document_id == document_id)
        .order_by(Conversation.updated_at.desc())
    )
    convs = result.scalars().all()
    return {
        "conversations": [
            {
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in convs
        ]
    }
