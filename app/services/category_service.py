"""Category service — manages income and expense categories."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.category import Category


class CategoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_categories_by_type(self, user_id: int, category_type: str) -> list[Category]:
        """Get all active categories for a user (including global system categories)."""
        query = (
            select(Category)
            .where(
                (Category.user_id == user_id) | (Category.user_id == None),
                Category.type == category_type,
                Category.is_active == True,
            )
            .order_by(Category.sort_order, Category.id)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_category_by_id(self, category_id: int) -> Category | None:
        return await self.session.get(Category, category_id)
