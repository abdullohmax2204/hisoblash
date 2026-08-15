"""Application configuration loaded from environment variables."""

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os


# Load .env file from project root
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)


@dataclass(frozen=True)
class Settings:
    """Application settings. All values come from environment variables."""

    bot_token: str
    admin_user_id: int
    database_url: str
    environment: str  # "development" or "production"
    log_level: str
    base_dir: Path  # Project root directory

    # Currency settings (single currency in MVP)
    currency_code: str = "UZS"
    currency_symbol: str = "сум"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def logs_dir(self) -> Path:
        return self.base_dir / "logs"

    @property
    def backups_dir(self) -> Path:
        return self.base_dir / "backups"


def load_settings() -> Settings:
    """Load settings from environment variables.

    Raises ValueError if required variables are missing.
    """
    bot_token = os.getenv("BOT_TOKEN", "")
    if not bot_token:
        raise ValueError("BOT_TOKEN is not set in .env")

    admin_user_id_str = os.getenv("ADMIN_USER_ID", "")
    if not admin_user_id_str:
        raise ValueError("ADMIN_USER_ID is not set in .env")

    try:
        admin_user_id = int(admin_user_id_str)
    except ValueError:
        raise ValueError("ADMIN_USER_ID must be a valid integer")

    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/finance.db")
    environment = os.getenv("ENVIRONMENT", "development")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    base_dir = Path(__file__).resolve().parent.parent.parent

    return Settings(
        bot_token=bot_token,
        admin_user_id=admin_user_id,
        database_url=database_url,
        environment=environment,
        log_level=log_level,
        base_dir=base_dir,
    )


class _SettingsProxy:
    """Lazy proxy that creates Settings on first attribute access.

    This allows modules to import `settings` without crashing
    when .env is incomplete (e.g., during Alembic migrations or tests).
    """

    _instance: Settings | None = None

    def _get(self) -> Settings:
        if self._instance is None:
            self._instance = load_settings()
        return self._instance

    def __getattr__(self, name: str):
        return getattr(self._get(), name)


# Lazy singleton — created on first attribute access
settings = _SettingsProxy()
