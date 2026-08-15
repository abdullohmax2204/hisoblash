"""Transaction repository."""

from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.transaction import Transaction
from app.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    model = Transaction

    async def get_user_transactions(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        transaction_type: str | None = None,
    ) -> list[Transaction]:
        """Get user transactions with optional filtering, newest first."""
        query = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
        )

        if date_from:
            query = query.where(Transaction.created_at >= date_from)
        if date_to:
            query = query.where(Transaction.created_at <= date_to)
        if transaction_type:
            query = query.where(Transaction.type == transaction_type)

        query = query.order_by(Transaction.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_sum_by_type(
        self,
        user_id: int,
        transaction_type: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        """Get the total sum of transactions of a given type in a period."""
        query = (
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .where(Transaction.user_id == user_id)
            .where(Transaction.type == transaction_type)
        )
        if date_from:
            query = query.where(Transaction.created_at >= date_from)
        if date_to:
            query = query.where(Transaction.created_at <= date_to)

        result = await self.session.execute(query)
        return int(result.scalar() or 0)
