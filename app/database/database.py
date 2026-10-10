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
    """Ensure data directory exists, create tables, and safely reconcile schema."""
    from app.core.config import settings
    from app.database.cloud_sync import turso_sync
    from app.database.models import Base

    settings.data_dir.mkdir(parents=True, exist_ok=True)

    # 1. If running with Turso cloud storage, restore state if Render wiped local disk
    if turso_sync.is_configured:
        try:
            await turso_sync.restore_from_cloud_if_needed()
        except Exception as e:
            logger.warning("Turso cloud restore skipped on startup: %s", e)

    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        if "sqlite" in settings.database_url:
            def _reconcile_sqlite_schema(sync_conn):
                # 1. Accounts table currency column
                acc_cols = [c[1] for c in sync_conn.exec_driver_sql("PRAGMA table_info(accounts)").fetchall()]
                if "currency" not in acc_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE accounts ADD COLUMN currency VARCHAR(10) DEFAULT 'UZS'")

                # 2. Transactions table currency, exchange_rate, source, idempotency_key columns
                tx_cols = [c[1] for c in sync_conn.exec_driver_sql("PRAGMA table_info(transactions)").fetchall()]
                if "currency" not in tx_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN currency VARCHAR(10) DEFAULT 'UZS'")
                if "exchange_rate" not in tx_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN exchange_rate NUMERIC(15, 6) DEFAULT 1.0")
                if "source" not in tx_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN source VARCHAR(50) DEFAULT 'bot'")
                if "idempotency_key" not in tx_cols:
                    sync_conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN idempotency_key VARCHAR(64)")
                    sync_conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS ix_transactions_idempotency_key ON transactions (idempotency_key)")

            await conn.run_sync(_reconcile_sqlite_schema)

    # 2. Start background replication loop if Turso is configured
    if turso_sync.is_configured:
        turso_sync.start_background_sync()

    logger.info("Database initialized and schema reconciled (url=%s)", settings.database_url)


async def close_db() -> None:
    """Dispose of the engine connection pool and gracefully shutdown cloud sync."""
    global _engine
    from app.database.cloud_sync import turso_sync

    if turso_sync.is_configured:
        try:
            await turso_sync.shutdown()
        except Exception as e:
            logger.warning("Error during Turso shutdown sync: %s", e)

    if _engine is not None:
        await _engine.dispose()
        logger.info("Database connection closed")
