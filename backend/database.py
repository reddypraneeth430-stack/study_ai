"""
StudyMate AI - Database Setup and Session Management
SQLite with SQLAlchemy async support
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event

from backend.config import settings


# Convert sqlite:// to sqlite+aiosqlite:// for async support
def _build_async_url(url: str) -> str:
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


ASYNC_DATABASE_URL = _build_async_url(settings.database_url)

engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.debug,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency: yields a database session and closes it after use."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all database tables on startup."""
    # Ensure data directory exists
    settings.data_path  # triggers mkdir

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
