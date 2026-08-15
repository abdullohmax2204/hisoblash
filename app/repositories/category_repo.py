"""Category repository."""

from sqlalchemy import select

from app.database.models.category import Category
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    model = Category

    async def get_by_type(self, user_id: int, category_type: str) -> list[Category]:
        """Get all active categories of a given type for a user.

        Returns both system categories (user_id=None) and user-created ones.
        """
        query = (
            select(Category)
            .where(
                (Category.user_id == user_id) | (Category.user_id == None)
            )
            .where(Category.type == category_type)
            .where(Category.is_active == True)
            .order_by(Category.sort_order, Category.id)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
