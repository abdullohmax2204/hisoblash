"""Alembic environment configuration.

This file is used by Alembic to configure the migration environment.
It reads the database URL from the application config (not alembic.ini).
"""

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool, create_engine

# Load .env manually (don't depend on app.core.config for Alembic)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# Import Base directly to avoid triggering database engine creation
from app.database.models.base import Base

# Import all models so they register with Base.metadata
from app.database.models import user, account, category, transaction, debt, saving_goal  # noqa: F401

# Alembic Config object
config = context.config

# Setup logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
target_metadata = Base.metadata

# Get database URL from environment
_db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/finance.db")
# Convert async URL to sync for Alembic (which runs synchronously)
sync_url = _db_url.replace("+aiosqlite", "")

# Ensure directory for SQLite database file exists before connecting
if "sqlite" in sync_url:
    path_part = sync_url.split("sqlite:///")[-1].split("?")[0]
    if path_part and not path_part.startswith(":memory:"):
        Path(path_part).resolve().parent.mkdir(parents=True, exist_ok=True)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL script without connecting to the database.
    """
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Required for SQLite ALTER TABLE
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates a connection and runs migrations against the live database.
    """
    connectable = create_engine(sync_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for SQLite ALTER TABLE
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
