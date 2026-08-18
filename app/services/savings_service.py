"""Savings service — deposits, withdrawals, and multi-goal tracking with goal notifications."""

from datetime import date, datetime, timedelta
from decimal import Decimal
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.account import Account
from app.database.models.saving_goal import SavingGoal
from app.database.models.transaction import Transaction, TransactionType
from app.database.models.user import User

logger = logging.getLogger(__name__)


class SavingsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_savings_account(self, user_id: int) -> Account:
        query = select(Account).where(Account.user_id == user_id, Account.is_savings == True)
        result = await self.session.execute(query)
        acc = result.scalar_one_or_none()
        if not acc:
            acc = Account(
                user_id=user_id,
                name="Накопления",
                icon="💵",
                balance=Decimal("0"),
                is_savings=True,
                sort_order=99,
            )
            self.session.add(acc)
            await self.session.flush()
        return acc

    async def get_active_goals(self, user_id: int) -> list[SavingGoal]:
        """Get all active savings goals for the user, ordered by creation date."""
        query = (
            select(SavingGoal)
            .where(SavingGoal.user_id == user_id, SavingGoal.is_active == True)
            .order_by(SavingGoal.created_at.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_goal_by_id(self, goal_id: int, user_id: int) -> SavingGoal | None:
        query = select(SavingGoal).where(SavingGoal.id == goal_id, SavingGoal.user_id == user_id, SavingGoal.is_active == True)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_goal(
        self, user_id: int, name: str, target_amount: Decimal, target_date: date | None = None
    ) -> SavingGoal:
        """Add a new savings goal."""
        clean_name = name[:40].strip()
        if not clean_name:
            raise ValueError("Название цели не может быть пустым")

        goal = SavingGoal(
            user_id=user_id,
            name=clean_name,
            target_amount=target_amount,
            target_date=target_date,
            is_active=True,
        )
        self.session.add(goal)
        await self.session.flush()
        return goal

    async def delete_goal(self, user_id: int, goal_id: int) -> bool:
        """Deactivate a savings goal."""
        goal = await self.get_goal_by_id(goal_id, user_id)
        if not goal:
            return False
        goal.is_active = False
        await self.session.flush()
        return True

    async def get_multi_goals_overview(self, user_id: int) -> dict:
        """Calculate overview for multiple savings goals:
        - Current savings balance
        - List of goals with individual status and allocated progress
        - Total sum needed across all goals
        - Overall progress percentage
        - Goals that are fully funded
        """
        savings_account = await self.get_savings_account(user_id)
        balance = savings_account.balance
        goals = await self.get_active_goals(user_id)

        total_target = sum((g.target_amount for g in goals), Decimal("0"))

        overall_pct = 0
        if total_target > Decimal("0"):
            overall_pct = min(int((balance / total_target) * 100), 100)

        # Calculate progress for each goal sequentially based on priority/order
        remaining_pool = balance
        goals_info = []

        for goal in goals:
            target = goal.target_amount
            # How much of current balance can cover this goal
            is_funded = balance >= target
            pct = min(int((balance / target) * 100), 100) if target > 0 else 100

            goals_info.append({
                "goal": goal,
                "target": target,
                "is_funded": is_funded,
                "pct": pct,
            })

        return {
            "savings_balance": balance,
            "goals": goals_info,
            "total_target": total_target,
            "overall_pct": overall_pct,
            "has_goals": len(goals) > 0,
        }

    async def check_newly_reached_goals(
        self, user_id: int, old_balance: Decimal, new_balance: Decimal
    ) -> list[SavingGoal]:
        """Check if depositing money caused any goals to be newly reached."""
        if new_balance <= old_balance:
            return []

        goals = await self.get_active_goals(user_id)
        reached = []
        for goal in goals:
            if goal.target_amount > old_balance and goal.target_amount <= new_balance:
                reached.append(goal)
        return reached

    async def deposit(
        self,
        user_id: int,
        source_account_id: int,
        amount: Decimal,
        description: str | None = None,
    ) -> tuple[Transaction, Account, Account, list[SavingGoal]]:
        """Deposit into savings and return newly reached goals if any."""
        if amount <= Decimal("0"):
            raise ValueError("Сумма должна быть больше нуля")

        source_acc = await self.session.get(Account, source_account_id)
        if not source_acc or source_acc.user_id != user_id:
            raise ValueError("Счет списания не найден")

        if source_acc.balance < amount:
            raise ValueError(f"Недостаточно средств на счете {source_acc.name}")

        savings_acc = await self.get_savings_account(user_id)
        old_savings_balance = savings_acc.balance

        source_acc.balance -= amount
        savings_acc.balance += amount

        tx = Transaction(
            user_id=user_id,
            account_id=source_acc.id,
            related_account_id=savings_acc.id,
            type=TransactionType.SAVING.value,
            amount=amount,
            description=description or "Отложено в накопления",
        )
        self.session.add(tx)
        await self.session.flush()

        newly_reached = await self.check_newly_reached_goals(user_id, old_savings_balance, savings_acc.balance)

        return tx, source_acc, savings_acc, newly_reached

    async def withdraw(
        self,
        user_id: int,
        dest_account_id: int,
        amount: Decimal,
        description: str | None = None,
    ) -> tuple[Transaction, Account, Account]:
        if amount <= Decimal("0"):
            raise ValueError("Сумма должна быть больше нуля")

        savings_acc = await self.get_savings_account(user_id)
        if savings_acc.balance < amount:
            raise ValueError(f"Недостаточно средств в накоплениях. Доступно: {savings_acc.balance:,.0f} сум".replace(",", " "))

        dest_acc = await self.session.get(Account, dest_account_id)
        if not dest_acc or dest_acc.user_id != user_id:
            raise ValueError("Счет зачисления не найден")

        savings_acc.balance -= amount
        dest_acc.balance += amount

        tx = Transaction(
            user_id=user_id,
            account_id=dest_acc.id,
            related_account_id=savings_acc.id,
            type=TransactionType.SAVING_WITHDRAW.value,
            amount=amount,
            description=description or "Возврат из накоплений",
        )
        self.session.add(tx)
        await self.session.flush()

        return tx, dest_acc, savings_acc

    async def get_savings_history(self, user_id: int, limit: int = 10) -> list[Transaction]:
        query = (
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.type.in_([TransactionType.SAVING.value, TransactionType.SAVING_WITHDRAW.value]),
            )
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_financial_load_analysis(self, user_id: int) -> dict:
        """Calculate financial load/stress on monthly or 15-day salary:
        - Analyzes target_date for each active goal.
        - Calculates required monthly contribution per goal.
        - Calculates total monthly & 15-day required savings.
        - Compares against user's monthly_salary (or average monthly income over last 30 days).
        - Returns stress level (green, yellow, red), percentage, and recommendations.
        """
        user = await self.session.get(User, user_id)
        goals = await self.get_active_goals(user_id)
        savings_account = await self.get_savings_account(user_id)
        savings_balance = savings_account.balance

        # Determine monthly salary/income
        monthly_income = Decimal("0")
        if user and user.monthly_salary and user.monthly_salary > Decimal("0"):
            monthly_income = user.monthly_salary
        else:
            # Fallback: calculate total income over last 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            income_stmt = select(func.coalesce(func.sum(Transaction.amount), Decimal("0"))).where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.INCOME.value,
                Transaction.created_at >= thirty_days_ago,
            )
            res = await self.session.execute(income_stmt)
            monthly_income = res.scalar() or Decimal("0")

        today = date.today()
        goal_load_items = []
        total_required_monthly = Decimal("0")
        total_remaining_target = Decimal("0")

        # Sequentially subtract savings balance from goals to know remaining needed for each
        running_balance = savings_balance

        for g in goals:
            already_covered = min(running_balance, g.target_amount)
            running_balance = max(Decimal("0"), running_balance - already_covered)
            needed = g.target_amount - already_covered
            total_remaining_target += needed

            months_left = 1.0
            days_left = 0
            if g.target_date:
                days_left = (g.target_date - today).days
                if days_left > 0:
                    months_left = max(1.0, round(days_left / 30.44, 1))
                else:
                    months_left = 1.0

            required_monthly = (needed / Decimal(str(months_left))) if needed > 0 else Decimal("0")
            required_15day = required_monthly / Decimal("2")
            total_required_monthly += required_monthly

            goal_load_items.append({
                "id": g.id,
                "name": g.name,
                "target_amount": float(g.target_amount),
                "target_date": g.target_date.isoformat() if g.target_date else None,
                "days_left": days_left,
                "months_left": months_left,
                "remaining_needed": float(needed),
                "required_monthly": float(required_monthly),
                "required_15day": float(required_15day),
            })

        total_required_15day = total_required_monthly / Decimal("2")

        load_percentage = 0.0
        if monthly_income > Decimal("0"):
            load_percentage = round(float((total_required_monthly / monthly_income) * 100), 1)

        status = "green"
        status_text = "🟢 Бюджет не напряжен"
        recommendation = "Отличная финансовая нагрузка! Вы комфортно достигнете всех целей."

        if load_percentage > 60:
            status = "red"
            status_text = "🔴 Перегрузка бюджета!"
            recommendation = "Внимание: цели требуют более 60% вашего дохода. Рекомендуем продлить сроки целей или снизить суммы."
        elif load_percentage > 30:
            status = "yellow"
            status_text = "🟡 Умеренная нагрузка"
            recommendation = "Нагрузка ощутима для бюджета. См. детальный план отчислений."
        elif monthly_income == 0 and total_required_monthly > 0:
            status = "yellow"
            status_text = "🟡 Укажите ваш доход"
            recommendation = "Укажите ежемесячную зарплату в настройках, чтобы рассчитать процент нагрузки."

        stress_icon = "🟢" if status == "green" else ("🟡" if status == "yellow" else "🔴")
        status_text_clean = status_text.replace("🟢 ", "").replace("🟡 ", "").replace("🔴 ", "")

        return {
            "monthly_income": float(monthly_income),
            "monthly_salary_configured": bool(user and user.monthly_salary),
            "pay_cycle_days": user.pay_cycle_days if user else 30,
            "total_required_monthly": float(total_required_monthly),
            "total_required_15day": float(total_required_15day),
            "total_remaining_target": float(total_remaining_target),
            "load_percentage": load_percentage,
            "stress_pct": load_percentage,
            "status": status,
            "stress_level": status,
            "status_text": status_text,
            "stress_level_ru": status_text_clean,
            "stress_icon": stress_icon,
            "recommendation": recommendation,
            "goals_load": goal_load_items,
            "goals": goal_load_items,
        }
