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

    # Web / Mini App settings
    webapp_url: str = ""
    web_port: int = 8080

    # Single-user Access & Emergency password settings
    emergency_password: str = "$12Abdurahmon1"
    auth_challenge_timeout_seconds: int = 120  # 2 minutes

    # Turso Cloud Sync settings
    turso_database_url: str = ""
    turso_auth_token: str = ""
    turso_sync_interval_seconds: int = 60

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def sqlite_db_path(self) -> Path:
        if "sqlite" in self.database_url:
            path_part = self.database_url.split("sqlite+aiosqlite:///")[-1].split("?")[0]
            if path_part and not path_part.startswith(":memory:"):
                return Path(path_part).resolve()
        return self.data_dir / "finance.db"

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
    webapp_url = os.getenv("WEBAPP_URL", "")
    if not webapp_url:
        render_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("APP_URL", "")
        if render_url:
            webapp_url = render_url if render_url.startswith("http") else f"https://{render_url}"
    web_port = int(os.getenv("PORT", os.getenv("WEB_PORT", "8080")))
    emergency_password = os.getenv("EMERGENCY_PASSWORD", "$12Abdurahmon1")
    auth_challenge_timeout_seconds = int(os.getenv("AUTH_CHALLENGE_TIMEOUT_SECONDS", "120"))
    turso_database_url = os.getenv("TURSO_DATABASE_URL", "")
    turso_auth_token = os.getenv("TURSO_AUTH_TOKEN", "")
    turso_sync_interval_seconds = int(os.getenv("TURSO_SYNC_INTERVAL_SECONDS", "60"))
    base_dir = Path(__file__).resolve().parent.parent.parent

    return Settings(
        bot_token=bot_token,
        admin_user_id=admin_user_id,
        database_url=database_url,
        environment=environment,
        log_level=log_level,
        base_dir=base_dir,
        webapp_url=webapp_url,
        web_port=web_port,
        emergency_password=emergency_password,
        auth_challenge_timeout_seconds=auth_challenge_timeout_seconds,
        turso_database_url=turso_database_url,
        turso_auth_token=turso_auth_token,
        turso_sync_interval_seconds=turso_sync_interval_seconds,
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
