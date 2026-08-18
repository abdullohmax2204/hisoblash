"""Pytest configuration and shared fixtures."""

import asyncio
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database.models import Base
from app.database.models.user import User
from app.database.models.account import Account
from app.database.models.category import Category


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for all tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine, monkeypatch):
    """Create a fresh database session for each test."""
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr("app.web.api.async_session_factory", session_factory)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(session: AsyncSession) -> User:
    """Create a test user."""
    user = User(telegram_id=123456789, name="Test User")
    session.add(user)
    await session.flush()
    return user


@pytest_asyncio.fixture
async def test_accounts(session: AsyncSession, test_user: User) -> dict[str, Account]:
    """Create test accounts: card, cash, and savings."""
    card = Account(
        user_id=test_user.id, name="Карта", icon="💳",
        balance=Decimal("0"), is_savings=False, sort_order=0,
    )
    cash = Account(
        user_id=test_user.id, name="Наличные", icon="💵",
        balance=Decimal("0"), is_savings=False, sort_order=1,
    )
    savings = Account(
        user_id=test_user.id, name="Накопления", icon="💵",
        balance=Decimal("0"), is_savings=True, sort_order=10,
    )
    session.add_all([card, cash, savings])
    await session.flush()
    return {"card": card, "cash": cash, "savings": savings}


@pytest_asyncio.fixture
async def test_categories(session: AsyncSession, test_user: User) -> dict[str, Category]:
    """Create test categories for income and expense."""
    income_cat = Category(
        user_id=test_user.id, name="Дизайн", icon="🎨",
        type="INCOME", sort_order=0,
    )
    expense_cat = Category(
        user_id=test_user.id, name="Еда", icon="🍔",
        type="EXPENSE", sort_order=0,
    )
    session.add_all([income_cat, expense_cat])
    await session.flush()
    return {"income": income_cat, "expense": expense_cat}
