"""Application entry point: python -m app"""

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from aiohttp import web

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database import init_db, close_db
from app.bot.middlewares.auth import AuthMiddleware
from app.bot.middlewares.db import DatabaseMiddleware

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


async def start_healthcheck_server(port: int) -> web.AppRunner:
    """Start lightweight HTTP server for cloud platform (Render/Koyeb) health checks."""
    app = web.Application()

    async def handle_health(request: web.Request) -> web.Response:
        return web.Response(text="Hisoblash Bot is Running OK!", status=200)

    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Healthcheck web server started on 0.0.0.0:%d", port)
    return runner


async def main() -> None:
    """Initialize and start the bot."""
    # Setup logging
    setup_logging(settings.log_level, settings.logs_dir)
    logger.info("Starting Hisoblash Bot (env=%s)", settings.environment)

    # Initialize database
    await init_db()

    # Create bot and dispatcher
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register middlewares (order matters: auth first, then db)
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())

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

    web_runner = None
    port_env = os.getenv("PORT")
    if port_env:
        try:
            port = int(port_env)
            web_runner = await start_healthcheck_server(port)
        except Exception as e:
            logger.warning("Failed to start healthcheck server on port %s: %s", port_env, e)

    try:
        logger.info("Bot is running. Press Ctrl+C to stop.")
        # Delete webhook + start polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
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
