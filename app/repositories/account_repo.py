"""Account repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.account import Account
from app.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    model = Account

    async def get_user_accounts(
        self, user_id: int, include_savings: bool = True, active_only: bool = True
    ) -> list[Account]:
        """Get all accounts for a user, ordered by sort_order."""
        query = select(Account).where(Account.user_id == user_id)
        if not include_savings:
            query = query.where(Account.is_savings == False)
        if active_only:
            query = query.where(Account.is_active == True)
        query = query.order_by(Account.sort_order, Account.id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_savings_account(self, user_id: int) -> Account | None:
        """Get the savings account for a user."""
        query = (
            select(Account)
            .where(Account.user_id == user_id)
            .where(Account.is_savings == True)
            .where(Account.is_active == True)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_regular_accounts(self, user_id: int) -> list[Account]:
        """Get only regular (non-savings) accounts."""
        return await self.get_user_accounts(user_id, include_savings=False)
