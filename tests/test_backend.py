"""
StudyMate AI — Backend Tests
Phase 1: Foundation tests for health, upload validation, DB, and document parser.
"""
import io
import os
import sys
import pytest
import pytest_asyncio
from pathlib import Path

# Ensure we run from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Use an in-memory SQLite for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

# Patch settings BEFORE importing app
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/studymate.db")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OLLAMA_MODEL", "qwen2.5:7b")

from backend.database import Base, get_db
from backend.main import app


# ---------------------------------------------------------------------------
# Test DB fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    AsyncTestSession = async_sessionmaker(test_engine, expire_on_commit=False)
    async with AsyncTestSession() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """Test HTTP client with overridden DB dependency."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data
    assert "version" in data
    assert data.get("ai_provider") == "ollama"
    assert "ollama_configured" in data
    assert "ollama_reachable" in data
    assert "ollama_model_available" in data
    assert data.get("ollama_model") == "qwen2.5:7b"


# ---------------------------------------------------------------------------
# Document upload validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_txt_document(client):
    """Upload a valid TXT document and verify it is stored."""
    content = b"This is a test study material.\nIt contains important information about Python and AI."
    response = await client.post(
        "/api/documents/upload",
        files={"file": ("test_notes.txt", io.BytesIO(content), "text/plain")},
    )
    assert response.status_code == 201
    data = response.json()
    assert "document" in data
    assert data["document"]["original_filename"] == "test_notes.txt"
    assert data["document"]["file_type"] == "txt"
    assert data["document"]["word_count"] > 0


@pytest.mark.asyncio
async def test_upload_unsupported_file_type(client):
    """Upload an unsupported file type should return 400."""
    content = b"data"
    response = await client.post(
        "/api/documents/upload",
        files={"file": ("test.xlsx", io.BytesIO(content), "application/vnd.ms-excel")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_empty_file(client):
    """Upload an empty file should return 400."""
    response = await client.post(
        "/api/documents/upload",
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Document list and get
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_documents_empty(client):
    """List documents on a fresh DB should return empty list."""
    response = await client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert isinstance(data["documents"], list)


@pytest.mark.asyncio
async def test_get_nonexistent_document(client):
    """Getting a document that doesn't exist should return 404."""
    response = await client.get("/api/documents/nonexistent-id-12345")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_stats(client):
    """Dashboard stats endpoint should return valid structure."""
    response = await client.get("/api/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert "stats" in data
    assert "documents_uploaded" in data["stats"]
    assert "quizzes_completed" in data["stats"]
    assert "average_quiz_score" in data["stats"]


# ---------------------------------------------------------------------------
# Text extraction (unit tests — no HTTP)
# ---------------------------------------------------------------------------

def test_extract_txt_text():
    """Test TXT text extraction directly."""
    from backend.utils.document_parser import extract_text_from_txt
    import tempfile

    content = "Hello World! This is a test document.\nSecond line of content."
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        tmp_path = Path(f.name)

    try:
        text, pages = extract_text_from_txt(tmp_path)
        assert "Hello World" in text
        assert pages >= 1
    finally:
        tmp_path.unlink(missing_ok=True)


def test_extract_unsupported_raises():
    """Unsupported file extension should raise DocumentParseError."""
    from backend.utils.document_parser import extract_text, DocumentParseError
    dummy = Path("dummy.xyz")
    with pytest.raises(DocumentParseError):
        extract_text(dummy)


def test_count_words():
    """Word counter should work correctly."""
    from backend.utils.document_parser import count_words
    assert count_words("Hello world this is a test") == 6
    assert count_words("") == 0
    assert count_words("  single  ") == 1


# ---------------------------------------------------------------------------
# Filename sanitization
# ---------------------------------------------------------------------------

def test_sanitize_filename():
    from backend.services.document_service import sanitize_filename
    assert sanitize_filename("my file (1).pdf") == "my_file_1.pdf"
    assert sanitize_filename("../../../etc/passwd") == "etcpasswd"
    assert len(sanitize_filename("a" * 300)) <= 200


# ---------------------------------------------------------------------------
# Config — Ollama detection
# ---------------------------------------------------------------------------

def test_ollama_configured_detection():
    from backend.config import Settings
    s = Settings(ollama_base_url="http://localhost:11434", ollama_model="qwen2.5:7b")
    assert s.is_ollama_configured() is True

    s2 = Settings(ollama_base_url="", ollama_model="qwen2.5:7b")
    assert s2.is_ollama_configured() is False

    s3 = Settings(ollama_base_url="http://localhost:11434", ollama_model="")
    assert s3.is_ollama_configured() is False


@pytest.mark.asyncio
async def test_ollama_service_health():
    from backend.services.ollama_service import ollama_service
    health = await ollama_service.check_health()
    assert "reachable" in health
    assert "model_available" in health
    assert health["configured_model"] == "qwen2.5:7b"
