"""Authorization middleware — restricts bot access to ADMIN_USER_ID."""

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from app.core.config import settings

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Blocks all updates from unauthorized users.

    Only ADMIN_USER_ID from .env is allowed to interact with the bot.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Extract user from the event
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user is None:
            return  # Skip events without user (e.g., channel posts)

        if user.id != settings.admin_user_id:
            logger.warning(
                "Unauthorized access attempt: user_id=%d username=%s",
                user.id,
                user.username or "N/A",
            )
            if isinstance(event, Message):
                await event.answer("⛔ Доступ запрещен.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Доступ запрещен.", show_alert=True)
            return  # Do not call the handler

        return await handler(event, data)
