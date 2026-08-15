"""User service — ensures user exists and creates default data."""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User
from app.database.models.account import Account
from app.database.models.category import Category

logger = logging.getLogger(__name__)

# Default accounts created for new users
DEFAULT_ACCOUNTS = [
    {"name": "Карта", "icon": "💳", "is_savings": False, "sort_order": 0},
    {"name": "Наличные", "icon": "💵", "is_savings": False, "sort_order": 1},
    {"name": "Другой счет", "icon": "🏦", "is_savings": False, "sort_order": 2},
    {"name": "Накопления", "icon": "💵", "is_savings": True, "sort_order": 10},
]

# Default income categories
DEFAULT_INCOME_CATEGORIES = [
    {"name": "Работа", "icon": "💼", "sort_order": 0},
    {"name": "Дизайн", "icon": "🎨", "sort_order": 1},
    {"name": "Программирование", "icon": "💻", "sort_order": 2},
    {"name": "Продажи", "icon": "🛒", "sort_order": 3},
    {"name": "Подарок", "icon": "🎁", "sort_order": 4},
    {"name": "Другое", "icon": "➕", "sort_order": 5},
]

# Default expense categories
DEFAULT_EXPENSE_CATEGORIES = [
    {"name": "Еда", "icon": "🍔", "sort_order": 0},
    {"name": "Транспорт", "icon": "🚕", "sort_order": 1},
    {"name": "Одежда", "icon": "👕", "sort_order": 2},
    {"name": "Техника", "icon": "💻", "sort_order": 3},
    {"name": "Игры", "icon": "🎮", "sort_order": 4},
    {"name": "Учёба", "icon": "📚", "sort_order": 5},
    {"name": "Дом", "icon": "🏠", "sort_order": 6},
    {"name": "Связь", "icon": "📱", "sort_order": 7},
    {"name": "Подарки", "icon": "🎁", "sort_order": 8},
    {"name": "Другое", "icon": "💳", "sort_order": 9},
]


async def ensure_user_exists(
    session: AsyncSession,
    telegram_id: int,
    name: str,
) -> User:
    """Get or create a user with default accounts and categories.

    If the user already exists, returns them immediately.
    If new, creates default accounts and income/expense categories.
    """
    query = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if user is not None:
        return user

    # Create new user
    logger.info("Creating new user: telegram_id=%d name=%s", telegram_id, name)
    user = User(telegram_id=telegram_id, name=name)
    session.add(user)
    await session.flush()  # Get user.id

    # Create default accounts
    for acc_data in DEFAULT_ACCOUNTS:
        account = Account(
            user_id=user.id,
            balance=Decimal("0"),
            **acc_data,
        )
        session.add(account)

    # Create default income categories
    for cat_data in DEFAULT_INCOME_CATEGORIES:
        category = Category(
            user_id=user.id,
            type="INCOME",
            **cat_data,
        )
        session.add(category)

    # Create default expense categories
    for cat_data in DEFAULT_EXPENSE_CATEGORIES:
        category = Category(
            user_id=user.id,
            type="EXPENSE",
            **cat_data,
        )
        session.add(category)

    await session.flush()
    logger.info("Created user with defaults: user_id=%d", user.id)
    return user
