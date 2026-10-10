"""Aiohttp Web Application server for Telegram Mini App and REST API."""

import logging
from pathlib import Path
from aiohttp import web

from app.web import api

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@web.middleware
async def cors_middleware(request: web.Request, handler):
    """Handle CORS preflight and headers for WebApp."""
    if request.method == "OPTIONS":
        response = web.Response(status=204)
    else:
        try:
            response = await handler(request)
        except web.HTTPException as ex:
            response = ex

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Telegram-Init-Data, X-Profile-Id"
    return response


async def handle_index(request: web.Request) -> web.FileResponse:
    """Serve Mini App main entry HTML file."""
    index_path = STATIC_DIR / "index.html"
    return web.FileResponse(index_path)


async def handle_health(request: web.Request) -> web.Response:
    """Healthcheck endpoint for monitoring / cloud platforms."""
    return web.Response(text="Hisoblash Bot & Mini App is Running OK!", status=200)


def create_web_app() -> web.Application:
    """Create and configure aiohttp web application."""
    app = web.Application(middlewares=[cors_middleware])

    # Healthcheck
    app.router.add_get("/health", handle_health)

    # API Routes
    app.router.add_get("/api/users", api.handle_get_users)
    app.router.add_post("/api/users/create", api.handle_create_user_profile)
    app.router.add_post("/api/users/rename", api.handle_update_user_name)
    app.router.add_post("/api/users/delete", api.handle_delete_user_profile)
    app.router.add_get("/api/summary", api.handle_summary)
    app.router.add_get("/api/accounts", api.handle_get_accounts)
    app.router.add_post("/api/accounts", api.handle_create_account)
    app.router.add_get("/api/categories", api.handle_get_categories)
    app.router.add_post("/api/categories", api.handle_create_category)
    app.router.add_post("/api/transactions/income", api.handle_add_income)
    app.router.add_post("/api/transactions/expense", api.handle_add_expense)
    app.router.add_post("/api/transactions/transfer", api.handle_transfer)
    app.router.add_delete("/api/transactions/{id}", api.handle_delete_transaction)
    app.router.add_get("/api/savings", api.handle_get_savings)
    app.router.add_get("/api/savings/load-analysis", api.handle_get_load_analysis)
    app.router.add_post("/api/savings/deposit", api.handle_savings_deposit)
    app.router.add_post("/api/savings/withdraw", api.handle_savings_withdraw)
    app.router.add_post("/api/savings/goals", api.handle_create_goal)
    app.router.add_delete("/api/savings/goals/{id}", api.handle_delete_goal)
    app.router.add_post("/api/user/salary", api.handle_update_salary)
    app.router.add_get("/api/debts", api.handle_get_debts)
    app.router.add_post("/api/debts/give", api.handle_give_debt)
    app.router.add_post("/api/debts/take", api.handle_take_debt)
    app.router.add_post("/api/debts/return", api.handle_return_debt)
    app.router.add_get("/api/stats", api.handle_get_stats)
    app.router.add_get("/api/history", api.handle_get_history)
    app.router.add_get("/api/rates", api.handle_get_rates)
    app.router.add_post("/api/rates/sync", api.handle_sync_rates)

    # Frontend SPA entry point
    app.router.add_get("/", handle_index)
    app.router.add_static("/static", path=str(STATIC_DIR), name="static")

    return app


async def start_web_server(port: int, host: str = "0.0.0.0") -> web.AppRunner:
    """Start the aiohttp web server runner."""
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    app = create_web_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("Mini App Web Server started on http://%s:%d", host, port)
    return runner
