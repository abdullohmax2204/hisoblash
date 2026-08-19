"""REST API handlers for Telegram Mini App."""

from datetime import date
from decimal import Decimal
import json
import logging
from aiohttp import web

from app.database.database import async_session_factory
from app.database.models.debt import DebtType
from app.database.models.transaction import TransactionType
from app.services.account_service import AccountService
from app.services.category_service import CategoryService
from app.services.debt_service import DebtService
from app.services.finance_service import FinanceService
from app.services.history_service import HistoryService
from app.services.savings_service import SavingsService
from app.services.statistics_service import StatisticsService
from app.services.user_service import ensure_user_exists, update_user_salary, get_all_users, create_extra_profile
from app.web.auth import get_authenticated_user_id

logger = logging.getLogger(__name__)


def json_response(data: dict | list, status: int = 200) -> web.Response:
    """Helper to return JSON response with Decimal and Datetime support."""
    def default_serializer(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        return str(obj)

    text = json.dumps(data, default=default_serializer, ensure_ascii=False)
    return web.Response(text=text, status=status, content_type="application/json")


async def get_current_user(request: web.Request, session) -> int:
    """Extract and ensure user from request headers or query params."""
    init_data = request.headers.get("X-Telegram-Init-Data") or request.query.get("init_data")
    profile_id = request.headers.get("X-Profile-Id") or request.query.get("profile_id")
    telegram_id, full_name, explicit_user_id = get_authenticated_user_id(init_data, profile_id)

    if explicit_user_id:
        from app.database.models.user import User
        user = await session.get(User, explicit_user_id)
        if user:
            return user.id

    if telegram_id:
        user = await ensure_user_exists(
            session=session,
            telegram_id=telegram_id,
            name=full_name or f"User {telegram_id}",
        )
        return user.id

    raise web.HTTPUnauthorized(
        text=json.dumps({"error": "Unauthorized"}),
        content_type="application/json",
    )


async def handle_get_users(request: web.Request) -> web.Response:
    """GET /api/users - List all available user profiles."""
    async with async_session_factory() as session:
        current_user_id = await get_current_user(request, session)
        users = await get_all_users(session)
        return json_response({
            "current_user_id": current_user_id,
            "users": [
                {
                    "id": u.id,
                    "name": u.name,
                    "telegram_id": u.telegram_id,
                }
                for u in users
            ],
        })


async def handle_create_user_profile(request: web.Request) -> web.Response:
    """POST /api/users/create - Create a new independent user profile (max 3)."""
    try:
        body = await request.json()
        name = str(body.get("name", "")).strip()
    except Exception:
        name = ""

    async with async_session_factory() as session:
        users = await get_all_users(session)
        if len(users) >= 3:
            return json_response({"error": "Достигнут лимит профилей (максимум 3)"}, 400)

        user = await create_extra_profile(session, name or f"Профиль {len(users) + 1}")
        await session.commit()
        return json_response({
            "id": user.id,
            "name": user.name,
            "telegram_id": user.telegram_id,
        }, 201)


async def handle_summary(request: web.Request) -> web.Response:
    """GET /api/summary - Complete dashboard summary."""
    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        acc_service = AccountService(session)
        sav_service = SavingsService(session)
        hist_service = HistoryService(session)

        summary = await acc_service.get_bank_summary(user_id)
        goals_overview = await sav_service.get_multi_goals_overview(user_id)
        recent_txs, _ = await hist_service.get_history(user_id, page=0, page_size=8)

        regular_accounts = [
            {
                "id": a.id,
                "name": a.name,
                "icon": a.icon,
                "balance": a.balance,
                "is_savings": a.is_savings,
            }
            for a in summary["regular_accounts"]
        ]

        savings_acc = {
            "id": summary["savings_account"].id,
            "name": summary["savings_account"].name,
            "icon": summary["savings_account"].icon,
            "balance": summary["savings_account"].balance,
        }

        goals = [
            {
                "id": g["goal"].id,
                "name": g["goal"].name,
                "target_amount": g["target"],
                "is_funded": g["is_funded"],
                "pct": g["pct"],
            }
            for g in goals_overview["goals"]
        ]

        transactions = [
            {
                "id": tx.id,
                "type": tx.type,
                "amount": tx.amount,
                "description": tx.description,
                "account_name": tx.account.name if tx.account else None,
                "category_name": tx.category.name if tx.category else None,
                "category_icon": tx.category.icon if tx.category else "📝",
                "created_at": tx.created_at,
            }
            for tx in recent_txs
        ]

        from app.database.models.user import User
        user_obj = await session.get(User, user_id)

        data = {
            "user_id": user_id,
            "user_name": user_obj.name if user_obj else f"User #{user_id}",
            "available_funds": summary["available_funds"],
            "savings_balance": summary["savings_balance"],
            "debts_given": summary["debts_given"],
            "debts_taken": summary["debts_taken"],
            "total_capital": summary["total_capital"],
            "regular_accounts": regular_accounts,
            "savings_account": savings_acc,
            "goals": goals,
            "overall_goals_pct": goals_overview["overall_pct"],
            "has_goals": goals_overview["has_goals"],
            "recent_transactions": transactions,
        }
        return json_response(data)


async def handle_get_accounts(request: web.Request) -> web.Response:
    """GET /api/accounts - List user accounts."""
    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        acc_service = AccountService(session)
        accounts = await acc_service.get_user_accounts(user_id, include_savings=True)
        return json_response([
            {
                "id": a.id,
                "name": a.name,
                "icon": a.icon,
                "balance": a.balance,
                "is_savings": a.is_savings,
            }
            for a in accounts
        ])


async def handle_create_account(request: web.Request) -> web.Response:
    """POST /api/accounts - Create new account."""
    try:
        body = await request.json()
    except Exception:
        return json_response({"error": "Invalid JSON"}, 400)

    name = str(body.get("name", "")).strip()
    icon = str(body.get("icon", "💳")).strip() or "💳"
    initial_balance = Decimal(str(body.get("initial_balance", 0)))

    if not name:
        return json_response({"error": "Название счёта обязательно"}, 400)

    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        acc_service = AccountService(session)
        account = await acc_service.create_account(user_id, name, icon, initial_balance)
        await session.commit()
        return json_response({
            "id": account.id,
            "name": account.name,
            "icon": account.icon,
            "balance": account.balance,
            "is_savings": account.is_savings,
        }, 201)


async def handle_get_categories(request: web.Request) -> web.Response:
    """GET /api/categories - List expense and income categories."""
    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        cat_service = CategoryService(session)
        expense_cats = await cat_service.get_categories_by_type(user_id, "EXPENSE")
        income_cats = await cat_service.get_categories_by_type(user_id, "INCOME")

        return json_response({
            "expense": [{"id": c.id, "name": c.name, "icon": c.icon} for c in expense_cats],
            "income": [{"id": c.id, "name": c.name, "icon": c.icon} for c in income_cats],
        })


async def handle_create_category(request: web.Request) -> web.Response:
    """POST /api/categories - Create custom category."""
    try:
        body = await request.json()
        name = str(body["name"]).strip()
        category_type = str(body["type"]).strip().upper()
        icon = str(body.get("icon", "📁")).strip() or "📁"
    except (KeyError, ValueError, TypeError) as e:
        return json_response({"error": f"Неверные данные: {e}"}, 400)

    if not name or category_type not in ("INCOME", "EXPENSE"):
        return json_response({"error": "Название и правильный тип (INCOME/EXPENSE) обязательны"}, 400)

    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        cat_service = CategoryService(session)
        cat = await cat_service.create_category(user_id, name, category_type, icon)
        await session.commit()
        return json_response({"id": cat.id, "name": cat.name, "icon": cat.icon, "type": cat.type}, 201)


async def handle_add_income(request: web.Request) -> web.Response:
    """POST /api/transactions/income"""
    try:
        body = await request.json()
        account_id = int(body["account_id"])
        raw_cat = body.get("category_id")
        category_id = int(raw_cat) if raw_cat and str(raw_cat).strip().isdigit() else None
        amount = Decimal(str(body["amount"]))
        description = body.get("description")
    except (KeyError, ValueError, TypeError) as e:
        return json_response({"error": f"Неверные данные: {e}"}, 400)

    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        fin_service = FinanceService(session)
        try:
            tx, acc = await fin_service.add_income(user_id, account_id, category_id, amount, description)
            await session.commit()
            return json_response({
                "success": True,
                "transaction_id": tx.id,
                "new_balance": acc.balance,
            })
        except ValueError as e:
            return json_response({"error": str(e)}, 400)


async def handle_add_expense(request: web.Request) -> web.Response:
    """POST /api/transactions/expense"""
    try:
        body = await request.json()
        account_id = int(body["account_id"])
        raw_cat = body.get("category_id")
        category_id = int(raw_cat) if raw_cat and str(raw_cat).strip().isdigit() else None
        amount = Decimal(str(body["amount"]))
        description = body.get("description")
    except (KeyError, ValueError, TypeError) as e:
        return json_response({"error": f"Неверные данные: {e}"}, 400)

    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        fin_service = FinanceService(session)
        try:
            tx, acc = await fin_service.add_expense(user_id, account_id, category_id, amount, description)
            await session.commit()
            return json_response({
                "success": True,
                "transaction_id": tx.id,
                "new_balance": acc.balance,
            })
        except ValueError as e:
            return json_response({"error": str(e)}, 400)


async def handle_transfer(request: web.Request) -> web.Response:
    """POST /api/transactions/transfer"""
    try:
        body = await request.json()
        from_account_id = int(body["from_account_id"])
        to_account_id = int(body["to_account_id"])
        amount = Decimal(str(body["amount"]))
    except (KeyError, ValueError, TypeError) as e:
        return json_response({"error": f"Неверные данные: {e}"}, 400)

    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        fin_service = FinanceService(session)
        try:
            tx, from_acc, to_acc = await fin_service.transfer_between_accounts(
                user_id, from_account_id, to_account_id, amount
            )
            await session.commit()
            return json_response({
                "success": True,
                "transaction_id": tx.id,
                "from_balance": from_acc.balance,
                "to_balance": to_acc.balance,
            })
        except ValueError as e:
            return json_response({"error": str(e)}, 400)


async def handle_delete_transaction(request: web.Request) -> web.Response:
    """DELETE /api/transactions/{id}"""
    try:
        tx_id = int(request.match_info["id"])
    except (KeyError, ValueError):
        return json_response({"error": "Invalid transaction ID"}, 400)

    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        fin_service = FinanceService(session)
        success = await fin_service.delete_transaction(user_id, tx_id)
        if success:
            await session.commit()
            return json_response({"success": True})
        return json_response({"error": "Транзакция не найдена"}, 404)


async def handle_get_savings(request: web.Request) -> web.Response:
    """GET /api/savings - Goals, balance overview, and financial stress load analysis."""
    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        sav_service = SavingsService(session)
        overview = await sav_service.get_multi_goals_overview(user_id)
        history = await sav_service.get_savings_history(user_id, limit=10)
        load_analysis = await sav_service.get_financial_load_analysis(user_id)

        goals = [
            {
                "id": g["goal"].id,
                "name": g["goal"].name,
                "target_amount": g["target"],
                "target_date": g["goal"].target_date.isoformat() if g["goal"].target_date else None,
                "is_funded": g["is_funded"],
                "pct": g["pct"],
            }
            for g in overview["goals"]
        ]

        txs = [
            {
                "id": tx.id,
                "type": tx.type,
                "amount": tx.amount,
                "description": tx.description,
                "created_at": tx.created_at,
            }
            for tx in history
        ]

        return json_response({
            "savings_balance": overview["savings_balance"],
            "total_target": overview["total_target"],
            "overall_pct": overview["overall_pct"],
            "goals": goals,
            "history": txs,
            "load_analysis": load_analysis,
        })


async def handle_savings_deposit(request: web.Request) -> web.Response:
    """POST /api/savings/deposit"""
    try:
        body = await request.json()
        source_account_id = int(body["source_account_id"])
        amount = Decimal(str(body["amount"]))
        description = body.get("description")
    except (KeyError, ValueError, TypeError) as e:
        return json_response({"error": f"Неверные данные: {e}"}, 400)

    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        sav_service = SavingsService(session)
        try:
            tx, src_acc, sav_acc, reached_goals = await sav_service.deposit(
                user_id, source_account_id, amount, description
            )
            await session.commit()
            return json_response({
                "success": True,
                "transaction_id": tx.id,
                "source_balance": src_acc.balance,
                "savings_balance": sav_acc.balance,
                "reached_goals": [g.name for g in reached_goals],
            })
        except ValueError as e:
            return json_response({"error": str(e)}, 400)


async def handle_savings_withdraw(request: web.Request) -> web.Response:
    """POST /api/savings/withdraw"""
    try:
        body = await request.json()
        dest_account_id = int(body["dest_account_id"])
        amount = Decimal(str(body["amount"]))
        description = body.get("description")
    except (KeyError, ValueError, TypeError) as e:
        return json_response({"error": f"Неверные данные: {e}"}, 400)

    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        sav_service = SavingsService(session)
        try:
            tx, dest_acc, sav_acc = await sav_service.withdraw(
                user_id, dest_account_id, amount, description
            )
            await session.commit()
            return json_response({
                "success": True,
                "transaction_id": tx.id,
                "dest_balance": dest_acc.balance,
                "savings_balance": sav_acc.balance,
            })
        except ValueError as e:
            return json_response({"error": str(e)}, 400)


async def handle_create_goal(request: web.Request) -> web.Response:
    """POST /api/savings/goals"""
    try:
        body = await request.json()
        name = str(body["name"]).strip()
        target_amount = Decimal(str(body["target_amount"]))
        raw_date = body.get("target_date")
        target_date = date.fromisoformat(str(raw_date)) if raw_date and str(raw_date).strip() else None
    except (KeyError, ValueError, TypeError) as e:
        return json_response({"error": f"Неверные данные: {e}"}, 400)

    if not name or target_amount <= Decimal("0"):
        return json_response({"error": "Название и сумма цели обязательны"}, 400)

    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        sav_service = SavingsService(session)
        goal = await sav_service.create_goal(user_id, name, target_amount, target_date)
        await session.commit()
        return json_response({
            "id": goal.id,
            "name": goal.name,
            "target_amount": goal.target_amount,
            "target_date": goal.target_date.isoformat() if goal.target_date else None,
        }, 201)


async def handle_delete_goal(request: web.Request) -> web.Response:
    """DELETE /api/savings/goals/{id}"""
    try:
        goal_id = int(request.match_info["id"])
    except (KeyError, ValueError):
        return json_response({"error": "Invalid goal ID"}, 400)

    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        sav_service = SavingsService(session)
        success = await sav_service.delete_goal(user_id, goal_id)
        if success:
            await session.commit()
            return json_response({"success": True})
        return json_response({"error": "Цель не найдена"}, 404)


async def handle_get_load_analysis(request: web.Request) -> web.Response:
    """GET /api/savings/load-analysis"""
    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        sav_service = SavingsService(session)
        analysis = await sav_service.get_financial_load_analysis(user_id)
        return json_response(analysis)


async def handle_update_salary(request: web.Request) -> web.Response:
    """POST /api/user/salary"""
    try:
        body = await request.json()
        raw_salary = body.get("monthly_salary")
        monthly_salary = Decimal(str(raw_salary)) if raw_salary is not None and str(raw_salary).strip() != "" else None
        pay_cycle_days = int(body.get("pay_cycle_days", 30))
    except (KeyError, ValueError, TypeError) as e:
        return json_response({"error": f"Неверные данные: {e}"}, 400)

    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        await update_user_salary(session, user_id, monthly_salary, pay_cycle_days)
        await session.commit()
        sav_service = SavingsService(session)
        analysis = await sav_service.get_financial_load_analysis(user_id)
        return json_response(analysis)


async def handle_get_debts(request: web.Request) -> web.Response:
    """GET /api/debts"""
    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        debt_service = DebtService(session)
        given = await debt_service.get_active_debts(user_id, DebtType.GIVEN.value)
        taken = await debt_service.get_active_debts(user_id, DebtType.TAKEN.value)

        return json_response({
            "given": [
                {
                    "id": d.id,
                    "person_name": d.person_name,
                    "original_amount": d.original_amount,
                    "remaining_amount": d.remaining_amount,
                    "created_at": d.created_at,
                }
                for d in given
            ],
            "taken": [
                {
                    "id": d.id,
                    "person_name": d.person_name,
                    "original_amount": d.original_amount,
                    "remaining_amount": d.remaining_amount,
                    "created_at": d.created_at,
                }
                for d in taken
            ],
        })


async def handle_give_debt(request: web.Request) -> web.Response:
    """POST /api/debts/give"""
    try:
        body = await request.json()
        person_name = str(body["person_name"]).strip()
        amount = Decimal(str(body["amount"]))
        account_id = int(body["account_id"])
    except (KeyError, ValueError, TypeError) as e:
        return json_response({"error": f"Неверные данные: {e}"}, 400)

    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        debt_service = DebtService(session)
        try:
            debt, tx, acc = await debt_service.give_debt(user_id, person_name, amount, account_id)
            await session.commit()
            return json_response({
                "success": True,
                "debt_id": debt.id,
                "new_balance": acc.balance,
            })
        except ValueError as e:
            return json_response({"error": str(e)}, 400)


async def handle_take_debt(request: web.Request) -> web.Response:
    """POST /api/debts/take"""
    try:
        body = await request.json()
        person_name = str(body["person_name"]).strip()
        amount = Decimal(str(body["amount"]))
        account_id = int(body["account_id"])
    except (KeyError, ValueError, TypeError) as e:
        return json_response({"error": f"Неверные данные: {e}"}, 400)

    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        debt_service = DebtService(session)
        try:
            debt, tx, acc = await debt_service.take_debt(user_id, person_name, amount, account_id)
            await session.commit()
            return json_response({
                "success": True,
                "debt_id": debt.id,
                "new_balance": acc.balance,
            })
        except ValueError as e:
            return json_response({"error": str(e)}, 400)


async def handle_return_debt(request: web.Request) -> web.Response:
    """POST /api/debts/return"""
    try:
        body = await request.json()
        debt_id = int(body["debt_id"])
        amount = Decimal(str(body["amount"]))
        account_id = int(body["account_id"])
    except (KeyError, ValueError, TypeError) as e:
        return json_response({"error": f"Неверные данные: {e}"}, 400)

    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        debt_service = DebtService(session)
        try:
            debt, tx, acc = await debt_service.return_debt(user_id, debt_id, amount, account_id)
            await session.commit()
            return json_response({
                "success": True,
                "remaining_amount": debt.remaining_amount,
                "is_settled": debt.is_settled,
                "new_balance": acc.balance,
            })
        except ValueError as e:
            return json_response({"error": str(e)}, 400)


async def handle_get_stats(request: web.Request) -> web.Response:
    """GET /api/stats?period=today|week|month|all"""
    period = request.query.get("period", "month")
    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        stats_service = StatisticsService(session)
        stats = await stats_service.get_period_stats(user_id, period)

        top_cats = [
            {"name": name, "icon": icon, "total": total}
            for name, icon, total in stats["top_categories"]
        ]

        return json_response({
            "title": stats["title"],
            "total_income": stats["total_income"],
            "total_expense": stats["total_expense"],
            "total_savings": stats["total_savings"],
            "total_debt_given": stats["total_debt_given"],
            "net_income": stats["net_income"],
            "top_categories": top_cats,
        })


async def handle_get_history(request: web.Request) -> web.Response:
    """GET /api/history?page=0&page_size=20"""
    page = int(request.query.get("page", 0))
    page_size = int(request.query.get("page_size", 20))

    async with async_session_factory() as session:
        user_id = await get_current_user(request, session)
        hist_service = HistoryService(session)
        items, has_next = await hist_service.get_history(user_id, page=page, page_size=page_size)

        transactions = [
            {
                "id": tx.id,
                "type": tx.type,
                "amount": tx.amount,
                "description": tx.description,
                "account_name": tx.account.name if tx.account else None,
                "category_name": tx.category.name if tx.category else None,
                "category_icon": tx.category.icon if tx.category else "📝",
                "created_at": tx.created_at,
            }
            for tx in items
        ]

        return json_response({
            "transactions": transactions,
            "has_next": has_next,
            "page": page,
        })
