"""Category service — manages income and expense categories."""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.category import Category


class CategoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_categories_by_type(self, user_id: int, category_type: str) -> list[Category]:
        """Get all active categories for a user (including global system categories), auto-seeding if empty."""
        cat_type = category_type.upper()
        query = (
            select(Category)
            .where(
                (Category.user_id == user_id) | (Category.user_id == None),
                func.upper(Category.type) == cat_type,
                Category.is_active == True,
            )
            .order_by(Category.sort_order, Category.id)
        )
        result = await self.session.execute(query)
        categories = list(result.scalars().all())

        if not categories and user_id:
            from app.services.user_service import DEFAULT_INCOME_CATEGORIES, DEFAULT_EXPENSE_CATEGORIES
            defaults = DEFAULT_INCOME_CATEGORIES if cat_type == "INCOME" else DEFAULT_EXPENSE_CATEGORIES
            created = []
            for cat_data in defaults:
                cat = Category(
                    user_id=user_id,
                    type=cat_type,
                    **cat_data,
                )
                self.session.add(cat)
                created.append(cat)
            await self.session.flush()
            return created

        return categories

    async def get_category_by_id(self, category_id: int) -> Category | None:
        return await self.session.get(Category, category_id)

    async def create_category(self, user_id: int, name: str, category_type: str, icon: str = "📁") -> Category:
        """Create new custom category for user."""
        cat = Category(
            user_id=user_id,
            name=name.strip(),
            type=category_type.upper(),
            icon=icon.strip() or "📁",
            is_active=True,
        )
        self.session.add(cat)
        await self.session.flush()
        return cat
