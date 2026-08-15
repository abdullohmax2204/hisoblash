"""Debt repository."""

from sqlalchemy import select

from app.database.models.debt import Debt
from app.repositories.base import BaseRepository


class DebtRepository(BaseRepository[Debt]):
    model = Debt

    async def get_active_debts(self, user_id: int, debt_type: str) -> list[Debt]:
        """Get all unsettled debts of a given type for a user."""
        query = (
            select(Debt)
            .where(Debt.user_id == user_id)
            .where(Debt.type == debt_type)
            .where(Debt.is_settled == False)
            .order_by(Debt.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all_debts(self, user_id: int, debt_type: str) -> list[Debt]:
        """Get all debts of a given type (including settled)."""
        query = (
            select(Debt)
            .where(Debt.user_id == user_id)
            .where(Debt.type == debt_type)
            .order_by(Debt.is_settled, Debt.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
