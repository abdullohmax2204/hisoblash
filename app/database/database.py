"""Database engine, session management, and initialization."""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)

# Engine and session factory — created lazily on first use
_engine = None
_async_session_factory = None


def _get_engine():
    """Get or create the async engine (lazy initialization)."""
    global _engine
    if _engine is None:
        from pathlib import Path
        from app.core.config import settings

        if "sqlite" in settings.database_url:
            path_part = settings.database_url.split("sqlite+aiosqlite:///")[-1].split("?")[0]
            if path_part and not path_part.startswith(":memory:"):
                Path(path_part).resolve().parent.mkdir(parents=True, exist_ok=True)

        _engine = create_async_engine(
            settings.database_url,
            echo=False,
        )
    return _engine


def _get_session_factory():
    """Get or create the session factory (lazy initialization)."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


def async_session_factory():
    """Public accessor for the session factory."""
    return _get_session_factory()()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with _get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Ensure the data directory exists. Alembic handles schema creation."""
    from app.core.config import settings
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Database initialized (url=%s)", settings.database_url)


async def close_db() -> None:
    """Dispose of the engine connection pool."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        logger.info("Database connection closed")
