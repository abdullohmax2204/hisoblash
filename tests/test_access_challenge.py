"""Tests for single-user security and 2-minute emergency password authorization challenge."""

import asyncio
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.database.models.authorized_user import AuthorizedTelegramUser
from app.services.access_service import (
    start_challenge,
    has_active_challenge,
    clear_challenge,
    is_telegram_authorized,
    authorize_secondary_account,
    get_master_user,
    _active_challenges,
)


@pytest.mark.asyncio
async def test_admin_is_always_authorized(session):
    """Primary admin user is always authorized immediately."""
    assert await is_telegram_authorized(session, settings.admin_user_id) is True


@pytest.mark.asyncio
async def test_unknown_user_starts_challenge():
    """Unknown user entering /start gets an active 2-minute challenge."""
    unknown_id = 999888777
    assert has_active_challenge(unknown_id) is False

    start_challenge(unknown_id)
    assert has_active_challenge(unknown_id) is True

    # Challenge expiration is set to ~120 seconds in future
    exp = _active_challenges[unknown_id]
    now = datetime.now(timezone.utc)
    assert 110 < (exp - now).total_seconds() <= 120


@pytest.mark.asyncio
async def test_challenge_expired_drops_silently():
    """Expired challenge returns False and drops from active challenges."""
    user_id = 111222333
    # Manually set expired challenge
    _active_challenges[user_id] = datetime.now(timezone.utc) - timedelta(seconds=1)

    assert has_active_challenge(user_id) is False
    assert user_id not in _active_challenges


@pytest.mark.asyncio
async def test_successful_emergency_password_authorization(session):
    """Sending correct password authorizes secondary account to master profile."""
    secondary_tg_id = 777666555
    start_challenge(secondary_tg_id)
    assert has_active_challenge(secondary_tg_id) is True

    # Check initially not authorized
    assert await is_telegram_authorized(session, secondary_tg_id) is False

    # Simulate authorization
    await authorize_secondary_account(session, secondary_tg_id, "Secondary Device")
    await session.commit()

    # Now authorized
    assert await is_telegram_authorized(session, secondary_tg_id) is True
    assert has_active_challenge(secondary_tg_id) is False

    # Check saved in database
    result = await session.execute(
        select(AuthorizedTelegramUser).where(AuthorizedTelegramUser.telegram_id == secondary_tg_id)
    )
    db_rec = result.scalar_one_or_none()
    assert db_rec is not None
    assert db_rec.telegram_id == secondary_tg_id

    # Master user is the single personal finance user
    master = await get_master_user(session)
    assert master.telegram_id == settings.admin_user_id
