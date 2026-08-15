"""Placeholder tests — will be expanded in Phase 3-7."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User
from app.database.models.account import Account


async def test_user_creation(test_user: User):
    """Test that a user is created correctly."""
    assert test_user.id is not None
    assert test_user.telegram_id == 123456789
    assert test_user.name == "Test User"


async def test_account_creation(test_accounts: dict[str, Account]):
    """Test that accounts are created with zero balance."""
    assert test_accounts["card"].balance == Decimal("0")
    assert test_accounts["cash"].balance == Decimal("0")
    assert test_accounts["savings"].balance == Decimal("0")
    assert test_accounts["savings"].is_savings is True
    assert test_accounts["card"].is_savings is False
