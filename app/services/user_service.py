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
    telegram_id: int | None = None,
    name: str = "",
) -> User:
    """Get or create the single master personal finance user.

    All authorized Telegram accounts access this single master personal finance profile.
    """
    from app.core.config import settings

    target_tg_id = settings.admin_user_id
    query = select(User).where(User.telegram_id == target_tg_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if user is not None:
        return user

    # Create master user
    master_name = name if (telegram_id == target_tg_id and name) else "Admin User"
    logger.info("Creating master user: telegram_id=%d name=%s", target_tg_id, master_name)
    user = User(telegram_id=target_tg_id, name=master_name)
    session.add(user)
    await session.flush()  # Get user.id

    # Create default accounts
    for acc_data in DEFAULT_ACCOUNTS:
        account = Account(
            user_id=user.id,
            balance=Decimal("0"),
            currency="UZS",
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
    logger.info("Created master user with defaults: user_id=%d", user.id)
    return user


async def update_user_salary(
    session: AsyncSession,
    user_id: int,
    monthly_salary: Decimal | None,
    pay_cycle_days: int = 30,
) -> User:
    """Update user's monthly salary and pay cycle period (15 or 30 days)."""
    user = await session.get(User, user_id)
    if not user:
        raise ValueError("Пользователь не найден")

    if monthly_salary is not None and monthly_salary < Decimal("0"):
        raise ValueError("Зарплата не может быть отрицательной")

    if pay_cycle_days not in (15, 30):
        pay_cycle_days = 30

    user.monthly_salary = monthly_salary
    user.pay_cycle_days = pay_cycle_days
    await session.flush()
    return user


async def get_all_users(session: AsyncSession) -> list[User]:
    """Get the master user profile list."""
    master = await ensure_user_exists(session)
    return [master]

