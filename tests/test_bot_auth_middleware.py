"""End-to-end tests for AuthMiddleware Telegram bot event processing."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.types import Message, User as TgUser, Chat

from app.core.config import settings
from app.bot.middlewares.auth import AuthMiddleware
from app.services.access_service import is_telegram_authorized, has_active_challenge, clear_challenge


def create_mock_message(user_id: int, text: str, full_name: str = "Test User") -> Message:
    tg_user = TgUser(id=user_id, is_bot=False, first_name=full_name)
    chat = Chat(id=user_id, type="private")
    msg = MagicMock(spec=Message)
    msg.from_user = tg_user
    msg.chat = chat
    msg.text = text
    msg.answer = AsyncMock()
    msg.delete = AsyncMock()
    return msg


@pytest.mark.asyncio
async def test_auth_middleware_admin_allowed(session):
    """Admin user is passed directly to the next handler."""
    middleware = AuthMiddleware()
    msg = create_mock_message(settings.admin_user_id, "/start", "Admin")
    handler = AsyncMock(return_value="OK")
    data = {"session": session}

    result = await middleware(handler, msg, data)

    assert result == "OK"
    assert handler.called is True
    assert "user" in data
    assert data["user"].telegram_id == settings.admin_user_id


@pytest.mark.asyncio
async def test_auth_middleware_unauthorized_start_silent(session):
    """Unauthorized user sending /start gets silent challenge, handler not called."""
    stranger_id = 123999111
    clear_challenge(stranger_id)
    middleware = AuthMiddleware()
    msg = create_mock_message(stranger_id, "/start", "Stranger")
    handler = AsyncMock()
    data = {"session": session}

    result = await middleware(handler, msg, data)

    assert result is None
    assert handler.called is False
    assert msg.answer.called is False  # Complete radio silence!
    assert has_active_challenge(stranger_id) is True


@pytest.mark.asyncio
async def test_auth_middleware_unauthorized_wrong_password_cancels(session):
    """Unauthorized user entering wrong password gets challenge cancelled silently."""
    stranger_id = 123999222
    clear_challenge(stranger_id)
    middleware = AuthMiddleware()
    data = {"session": session}

    # 1. Start challenge
    msg_start = create_mock_message(stranger_id, "/start", "Stranger")
    await middleware(AsyncMock(), msg_start, data)
    assert has_active_challenge(stranger_id) is True

    # 2. Send wrong password
    msg_wrong = create_mock_message(stranger_id, "wrongpassword123", "Stranger")
    handler = AsyncMock()
    await middleware(handler, msg_wrong, data)

    assert handler.called is False
    assert msg_wrong.answer.called is False  # Silent
    assert has_active_challenge(stranger_id) is False  # Dropped


@pytest.mark.asyncio
async def test_auth_middleware_unauthorized_correct_password_success(session):
    """Unauthorized user entering correct password $12Abdurahmon1 gets authorized."""
    secondary_id = 123999333
    clear_challenge(secondary_id)
    middleware = AuthMiddleware()
    data = {"session": session}

    # 1. Start challenge
    msg_start = create_mock_message(secondary_id, "/start", "Secondary Account")
    await middleware(AsyncMock(), msg_start, data)
    assert has_active_challenge(secondary_id) is True

    # 2. Send correct emergency password
    msg_pass = create_mock_message(secondary_id, "$12Abdurahmon1", "Secondary Account")
    handler = AsyncMock()
    await middleware(handler, msg_pass, data)

    # Message with password was deleted for privacy
    assert msg_pass.delete.called is True

    # Bot sent confirmation
    assert msg_pass.answer.called is True
    first_answer = msg_pass.answer.call_args_list[0][0][0]
    assert "Доступ к финансовому кабинету успешно подтверждён" in first_answer

    # Now this secondary account is persistently authorized!
    assert await is_telegram_authorized(session, secondary_id) is True

    # 3. Subsequent message from this account now goes through directly to handlers!
    msg_next = create_mock_message(secondary_id, "Доход", "Secondary Account")
    next_handler = AsyncMock(return_value="NEXT_OK")
    res = await middleware(next_handler, msg_next, data)
    assert res == "NEXT_OK"
    assert next_handler.called is True
    assert data["user"].telegram_id == settings.admin_user_id
