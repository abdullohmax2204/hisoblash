"""Authorization middleware — enforces single-user security and 2-minute emergency password challenges."""

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from app.core.config import settings
from app.services.access_service import (
    start_challenge,
    has_active_challenge,
    clear_challenge,
    is_telegram_authorized,
    authorize_secondary_account,
    get_master_user,
)
from app.bot.keyboards.inline import main_menu_keyboard
from app.bot.handlers.start import get_main_menu_text

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Enforces single master account security.

    - Admin user (ADMIN_USER_ID) has immediate full access.
    - Authorized secondary Telegram accounts have full access to the master profile.
    - Unknown users sending /start trigger a silent 2-minute challenge expecting the emergency password.
    - If password matches within 2 minutes, access is granted.
    - Otherwise, complete radio silence is maintained.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session = data.get("session")
        if not session:
            # Fallback if session middleware is not yet executed
            return await handler(event, data)

        from_user = None
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            from_user = event.from_user

        if not from_user:
            return None

        telegram_id = from_user.id

        # 1. Check if user is already authorized
        if await is_telegram_authorized(session, telegram_id):
            # Inject single master user
            master_user = await get_master_user(session)
            data["user"] = master_user
            return await handler(event, data)

        # 2. User is NOT authorized — handle challenge logic for Messages
        if isinstance(event, Message):
            text = (event.text or "").strip()

            # Case A: User sent /start -> silently start 2-minute challenge window
            if text == "/start" or text.startswith("/start "):
                start_challenge(telegram_id)
                logger.info("Unauthorized user %d triggered /start -> silent challenge started", telegram_id)
                # Keep radio silence as requested
                return None

            # Case B: User has an active challenge window
            if has_active_challenge(telegram_id):
                # Verify emergency password
                if text == settings.emergency_password:
                    logger.info("Emergency password matched for secondary user %d (%s)", telegram_id, from_user.full_name)
                    await authorize_secondary_account(
                        session=session,
                        telegram_id=telegram_id,
                        name=from_user.full_name or str(telegram_id),
                    )

                    # Delete the password message for privacy if possible
                    try:
                        await event.delete()
                    except Exception:
                        pass

                    # Fetch master user and send welcome dashboard
                    master_user = await get_master_user(session)
                    dashboard_text = await get_main_menu_text(master_user.id, session)

                    welcome_msg = (
                        "🔐 <b>Доступ к финансовому кабинету успешно подтверждён!</b>\n"
                        "Устройство привязано к вашему основному профилю.\n\n"
                        + dashboard_text
                    )
                    await event.answer(welcome_msg, reply_markup=main_menu_keyboard())
                    return None
                else:
                    # Wrong password sent -> cancel challenge and remain silent
                    clear_challenge(telegram_id)
                    logger.warning("Failed emergency password attempt from %d -> challenge cancelled", telegram_id)
                    return None

            # Case C: No active challenge -> complete radio silence
            logger.info("Ignored message from unauthorized user %d: %s", telegram_id, text[:20])
            return None

        # 3. For unauthorized CallbackQuery -> do not answer or execute
        if isinstance(event, CallbackQuery):
            logger.info("Ignored callback query from unauthorized user %d", telegram_id)
            return None

        return None
