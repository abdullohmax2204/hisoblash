"""Statistics service — calculates financial summaries for various periods."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.category import Category
from app.database.models.transaction import Transaction, TransactionType

logger = logging.getLogger(__name__)


class StatisticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_period_stats(
        self,
        user_id: int,
        period: str,  # "today", "week", "month", "all"
    ) -> dict:
        """Calculate income, expenses, savings deposited, debts given, and net diff for a period."""
        now = datetime.now()
        date_from = None

        if period == "today":
            date_from = datetime(now.year, now.month, now.day)
            title = f"СЕГОДНЯ ({now.strftime('%d.%m.%Y')})"
        elif period == "week":
            # Start of current week (Monday)
            start_of_week = now - timedelta(days=now.weekday())
            date_from = datetime(start_of_week.year, start_of_week.month, start_of_week.day)
            title = "ЭТА НЕДЕЛЯ"
        elif period == "month":
            date_from = datetime(now.year, now.month, 1)
            months_ru = [
                "", "ЯНВАРЬ", "ФЕВРАЛЬ", "МАРТ", "АПРЕЛЬ", "МАЙ", "ИЮНЬ",
                "ИЮЛЬ", "АВГУСТ", "СЕНТЯБРЬ", "ОКТЯБРЬ", "НОЯБРЬ", "ДЕКАБРЬ"
            ]
            title = f"{months_ru[now.month]} {now.year}"
        else:
            title = "ЗА ВСЁ ВРЕМЯ"

        # Query sums by type
        async def get_sum(tx_type: str) -> Decimal:
            q = (
                select(func.coalesce(func.sum(Transaction.amount), 0))
                .where(Transaction.user_id == user_id, Transaction.type == tx_type)
            )
            if date_from:
                q = q.where(Transaction.created_at >= date_from)
            res = await self.session.execute(q)
            return Decimal(str(res.scalar() or 0))

        total_income = await get_sum(TransactionType.INCOME.value)
        total_expense = await get_sum(TransactionType.EXPENSE.value)
        total_savings = await get_sum(TransactionType.SAVING.value)
        total_debt_given = await get_sum(TransactionType.DEBT_GIVEN.value)

        net_income = total_income - total_expense

        # Category breakdown for expenses
        q_cats = (
            select(
                Category.name,
                Category.icon,
                func.sum(Transaction.amount).label("cat_total"),
            )
            .join(Category, Transaction.category_id == Category.id)
            .where(Transaction.user_id == user_id, Transaction.type == TransactionType.EXPENSE.value)
        )
        if date_from:
            q_cats = q_cats.where(Transaction.created_at >= date_from)
        q_cats = q_cats.group_by(Category.id).order_by(func.sum(Transaction.amount).desc()).limit(5)
        res_cats = await self.session.execute(q_cats)
        top_categories = res_cats.all()

        return {
            "title": title,
            "total_income": total_income,
            "total_expense": total_expense,
            "total_savings": total_savings,
            "total_debt_given": total_debt_given,
            "net_income": net_income,
            "top_categories": top_categories,
        }
