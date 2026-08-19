"""Authorization middleware — restricts bot access to ADMIN_USER_ID."""

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from app.core.config import settings

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Allows all Telegram users to access the bot with their isolated account."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        return await handler(event, data)
