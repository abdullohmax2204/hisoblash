"""Access and security service for single-user authentication and emergency multi-account access."""

from datetime import datetime, timezone, timedelta
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.models.authorized_user import AuthorizedTelegramUser
from app.database.models.user import User
from app.services.user_service import ensure_user_exists

logger = logging.getLogger(__name__)

# In-memory auth challenges: telegram_id -> expiration datetime (UTC)
_active_challenges: dict[int, datetime] = {}

# In-memory cache of authorized secondary IDs to avoid DB query on every message
_authorized_ids_cache: set[int] = set()


def start_challenge(telegram_id: int) -> None:
    """Register an authentication challenge window (2 minutes) for an unknown telegram_id."""
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.auth_challenge_timeout_seconds)
    _active_challenges[telegram_id] = expires_at
    logger.info("Started auth challenge for telegram_id=%d (expires in %ds)", telegram_id, settings.auth_challenge_timeout_seconds)


def has_active_challenge(telegram_id: int) -> bool:
    """Check if the telegram user has a non-expired challenge waiting for password."""
    expires_at = _active_challenges.get(telegram_id)
    if not expires_at:
        return False

    now = datetime.now(timezone.utc)
    if now > expires_at:
        # Challenge expired
        _active_challenges.pop(telegram_id, None)
        logger.info("Auth challenge expired for telegram_id=%d", telegram_id)
        return False

    return True


def clear_challenge(telegram_id: int) -> None:
    """Drop active challenge for a telegram user."""
    _active_challenges.pop(telegram_id, None)


async def is_telegram_authorized(session: AsyncSession, telegram_id: int) -> bool:
    """Check if telegram_id is the primary admin or an authorized secondary account."""
    if telegram_id == settings.admin_user_id:
        return True

    if telegram_id in _authorized_ids_cache:
        return True

    # Check database
    query = select(AuthorizedTelegramUser).where(AuthorizedTelegramUser.telegram_id == telegram_id)
    result = await session.execute(query)
    record = result.scalar_one_or_none()
    if record is not None:
        _authorized_ids_cache.add(telegram_id)
        return True

    return False


async def authorize_secondary_account(
    session: AsyncSession,
    telegram_id: int,
    name: str = "",
) -> None:
    """Persist an authorized secondary Telegram ID to access the master profile."""
    query = select(AuthorizedTelegramUser).where(AuthorizedTelegramUser.telegram_id == telegram_id)
    result = await session.execute(query)
    record = result.scalar_one_or_none()

    if record is None:
        new_auth = AuthorizedTelegramUser(telegram_id=telegram_id, name=name or f"Authorized {telegram_id}")
        session.add(new_auth)
        await session.flush()

    _authorized_ids_cache.add(telegram_id)
    clear_challenge(telegram_id)
    logger.info("Successfully authorized secondary telegram_id=%d (%s) for master access", telegram_id, name)


async def get_master_user(session: AsyncSession) -> User:
    """Get the single master personal finance user."""
    return await ensure_user_exists(
        session=session,
        telegram_id=settings.admin_user_id,
        name="Admin User",
    )
