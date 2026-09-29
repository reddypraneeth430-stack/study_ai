"""
StudyMate AI - FastAPI Application Entry Point
Run with: uvicorn backend.main:app --reload
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import init_db
from backend.services.ollama_service import ollama_service
from backend.routes import documents, chat, quiz, exam, planner, dashboard

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Startup / Shutdown lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("StudyMate AI starting up...")

    # Ensure directories exist
    settings.upload_path   # triggers mkdir
    settings.data_path     # triggers mkdir

    # Initialize the database (creates tables if they don't exist)
    await init_db()
    logger.info("Database initialized.")

    # Check Ollama AI connectivity
    ollama_health = await ollama_service.check_health()
    if ollama_health["reachable"]:
        if ollama_health["model_available"]:
            logger.info("Ollama AI is ready with model '%s'.", settings.ollama_model)
        else:
            logger.warning(
                "Ollama is reachable, but model '%s' was not found. "
                "Available models: %s",
                settings.ollama_model,
                ollama_health["available_models"],
            )
    else:
        logger.warning(
            "Ollama is NOT reachable at %s. "
            "Please ensure Ollama is running (`ollama serve`).",
            settings.ollama_base_url,
        )

    yield

    logger.info("StudyMate AI shutting down.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered learning assistant for students.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS (allows frontend served from any origin in development)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global exception handlers (never expose raw stack traces)
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception at %s: %s", request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again."},
    )


# ---------------------------------------------------------------------------
# API Routers
# ---------------------------------------------------------------------------
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(quiz.router)
app.include_router(exam.router)
app.include_router(planner.router)
app.include_router(dashboard.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["health"])
async def health_check():
    """Health check endpoint providing application and Ollama status."""
    ollama_status = await ollama_service.check_health()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "ai_provider": "ollama",
        "ollama_configured": settings.is_ollama_configured(),
        "ollama_reachable": ollama_status["reachable"],
        "ollama_model_available": ollama_status["model_available"],
        "ollama_model": settings.ollama_model,
        "ollama_message": ollama_status["message"],
    }


# ---------------------------------------------------------------------------
# Serve frontend static files
# ---------------------------------------------------------------------------
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
