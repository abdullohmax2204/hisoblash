"""Database middleware — injects async session into handler data."""

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.database.database import async_session_factory

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """Provides an async database session to every handler.

    The session is available in handler data as `data["session"]`.
    It auto-commits on success and rolls back on exception.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with async_session_factory() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
