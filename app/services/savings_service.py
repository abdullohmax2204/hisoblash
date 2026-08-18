"""Savings service — deposits, withdrawals, and multi-goal tracking with goal notifications."""

from decimal import Decimal
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.account import Account
from app.database.models.saving_goal import SavingGoal
from app.database.models.transaction import Transaction, TransactionType

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

    async def create_goal(self, user_id: int, name: str, target_amount: Decimal) -> SavingGoal:
        """Add a new savings goal."""
        clean_name = name[:40].strip()
        if not clean_name:
            raise ValueError("Название цели не может быть пустым")

        goal = SavingGoal(
            user_id=user_id,
            name=clean_name,
            target_amount=target_amount,
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
