"""History service — retrieves paginated transaction history."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.transaction import Transaction


class HistoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_history(self, user_id: int, page: int = 0, page_size: int = 6) -> tuple[list[Transaction], bool]:
        """Fetch transactions for user with pagination. Returns (transactions, has_next_page)."""
        offset = page * page_size
        query = (
            select(Transaction)
            .options(
                selectinload(Transaction.category),
                selectinload(Transaction.account),
                selectinload(Transaction.debt),
            )
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .offset(offset)
            .limit(page_size + 1)
        )
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        has_next = len(items) > page_size
        return items[:page_size], has_next

    async def get_transaction_by_id(self, transaction_id: int, user_id: int) -> Transaction | None:
        query = (
            select(Transaction)
            .options(
                selectinload(Transaction.category),
                selectinload(Transaction.account),
                selectinload(Transaction.debt),
            )
            .where(Transaction.id == transaction_id, Transaction.user_id == user_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
