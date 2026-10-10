"""Application entry point: python -m app"""

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage

import aiohttp
from aiohttp import web

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database import init_db, close_db
from app.bot.middlewares.auth import AuthMiddleware
from app.bot.middlewares.db import DatabaseMiddleware
from app.web.server import start_web_server
from aiogram.types import MenuButtonWebApp, WebAppInfo

# Import all routers
from app.bot.handlers import (
    start as start_handler,
    bank as bank_handler,
    income as income_handler,
    expense as expense_handler,
    savings as savings_handler,
    debts as debts_handler,
    statistics as statistics_handler,
    history as history_handler,
    settings as settings_handler,
)

logger = logging.getLogger(__name__)


async def keep_alive_task(url: str, interval_seconds: int = 480) -> None:
    """Periodically ping public URL to prevent free cloud instances from sleeping."""
    logger.info("Keep-alive task started for URL: %s (interval: %ds)", url, interval_seconds)
    await asyncio.sleep(60)  # Wait 1 minute after start before first ping
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    logger.info("Keep-alive ping sent to %s -> HTTP %d", url, resp.status)
            except Exception as e:
                logger.warning("Keep-alive ping error: %s", e)
            await asyncio.sleep(interval_seconds)


async def main() -> None:
    """Initialize and start the bot and Mini App web server."""
    # Setup logging
    setup_logging(settings.log_level, settings.logs_dir)
    logger.info("Starting Hisoblash Bot & Mini App (env=%s, port=%d)", settings.environment, settings.web_port)

    # Initialize database
    await init_db()

    # Create bot and dispatcher
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register middlewares (database session first, then auth check)
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # Register all routers
    dp.include_router(start_handler.router)
    dp.include_router(bank_handler.router)
    dp.include_router(income_handler.router)
    dp.include_router(expense_handler.router)
    dp.include_router(savings_handler.router)
    dp.include_router(debts_handler.router)
    dp.include_router(statistics_handler.router)
    dp.include_router(history_handler.router)
    dp.include_router(settings_handler.router)

    # Global error handler
    @dp.errors()
    async def error_handler(event, exception):
        logger.error("Unhandled error: %s", exception, exc_info=True)
        try:
            update = event.update
            if update.message:
                await update.message.answer(
                    "⚠️ Произошла ошибка.\n\nПопробуйте еще раз."
                )
            elif update.callback_query:
                await update.callback_query.answer(
                    "⚠️ Произошла ошибка. Попробуйте еще раз.",
                    show_alert=True,
                )
        except Exception:
            pass
        return True

    # Start Mini App Web Server (Serves SPA frontend + REST API + Healthcheck)
    web_runner = None
    try:
        web_runner = await start_web_server(port=settings.web_port)
    except Exception as e:
        logger.warning("Failed to start WebApp server on port %d: %s", settings.web_port, e)

    # Configure Telegram Menu Button for WebApp if URL is provided
    if settings.webapp_url:
        try:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="📱 Приложение",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            )
            logger.info("Chat menu button set to WebApp: %s", settings.webapp_url)
        except Exception as e:
            logger.warning("Failed to set chat menu button: %s", e)

    # Automatic self-ping to prevent free instances from sleeping
    keep_alive_handle = None
    app_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("APP_URL") or (settings.webapp_url if settings.webapp_url.startswith("http") else None)
    if app_url:
        if not app_url.startswith("http"):
            app_url = f"https://{app_url}"
        if not app_url.endswith("/health"):
            app_url = f"{app_url.rstrip('/')}/health"
        keep_alive_handle = asyncio.create_task(keep_alive_task(app_url))

    try:
        logger.info("Bot is running. Press Ctrl+C to stop.")
        # Delete webhook + start polling
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
        except TelegramUnauthorizedError as e:
            logger.error("CRITICAL: Telegram Bot Token is unauthorized or revoked (%s)! Please update BOT_TOKEN in your Render Environment settings.", e)
            # Keep web runner running so WebApp stays online and healthchecks pass
            while True:
                await asyncio.sleep(3600)
    finally:
        if keep_alive_handle is not None:
            keep_alive_handle.cancel()
        if web_runner is not None:
            await web_runner.cleanup()
        await close_db()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
