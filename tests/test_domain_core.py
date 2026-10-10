"""Unit tests for Hisoblash Domain Core, Idempotency, and Multi-Currency Ledger."""

from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.account import Account
from app.database.models.user import User
from app.services.currency_service import CurrencyService
from app.services.finance_service import FinanceService
from app.services.account_service import AccountService
from app.domain.schemas import CreateIncomeCommand, CreateExpenseCommand, TransferCommand


@pytest.mark.asyncio
async def test_idempotency_prevents_duplicate_transactions(session: AsyncSession):
    """Test that repeating a transaction with the same idempotency key does not deduct/credit twice."""
    user = User(telegram_id=888999, name="Test Ledger User")
    session.add(user)
    await session.flush()

    account = Account(
        user_id=user.id,
        name="Карта Uzcard",
        balance=Decimal("500000"),
        currency="UZS",
    )
    session.add(account)
    await session.flush()

    finance_service = FinanceService(session)
    idempotency_key = "req-uuid-12345"

    # First attempt: expense 100 000
    tx1, acc1 = await finance_service.add_expense(
        user_id=user.id,
        account_id=account.id,
        category_id=None,
        amount=Decimal("100000"),
        description="Покупка в супермаркете",
        idempotency_key=idempotency_key,
    )
    assert acc1.balance == Decimal("400000")
    assert tx1.id is not None

    # Second attempt with same key: must NOT deduct again
    tx2, acc2 = await finance_service.add_expense(
        user_id=user.id,
        account_id=account.id,
        category_id=None,
        amount=Decimal("100000"),
        description="Покупка в супермаркете",
        idempotency_key=idempotency_key,
    )
    assert acc2.balance == Decimal("400000")
    assert tx2.id == tx1.id


@pytest.mark.asyncio
async def test_reconcile_account_balance(session: AsyncSession):
    """Test that reconcile_account_balance mathematically reconstructs the exact balance from ledger entries."""
    user = User(telegram_id=777666, name="Reconcile Test")
    session.add(user)
    await session.flush()

    acc1 = Account(user_id=user.id, name="Счет А", balance=Decimal("1000000"), currency="UZS")
    acc2 = Account(user_id=user.id, name="Счет Б", balance=Decimal("0"), currency="UZS")
    session.add_all([acc1, acc2])
    await session.flush()

    finance_service = FinanceService(session)

    # 1. Income +200 000 on acc1
    await finance_service.add_income(user.id, acc1.id, None, Decimal("200000"), "Зарплата")
    # 2. Expense -50 000 on acc1
    await finance_service.add_expense(user.id, acc1.id, None, Decimal("50000"), "Обед")
    # 3. Transfer 150 000 from acc1 to acc2
    await finance_service.transfer_between_accounts(user.id, acc1.id, acc2.id, Decimal("150000"))

    # Artificial balance drift simulation (e.g. database corruption or desync)
    acc1.balance = Decimal("99999999")
    acc2.balance = Decimal("-123456")
    await session.flush()

    # Reconcile acc1: 200 000 - 50 000 - 150 000 = 0
    # Note: initial balance was not a recorded transaction in this test, so ledger sum is 0
    reconciled_1 = await finance_service.reconcile_account_balance(acc1.id)
    assert reconciled_1 == Decimal("0")

    # Reconcile acc2: transfer in +150 000 = 150 000
    reconciled_2 = await finance_service.reconcile_account_balance(acc2.id)
    assert reconciled_2 == Decimal("150000")


@pytest.mark.asyncio
async def test_currency_conversion_service(session: AsyncSession):
    """Test multi-currency conversions and calculations."""
    curr_service = CurrencyService(session)

    # Setup rates: 1 USD = 12 800 UZS, 1 EUR = 14 000 UZS
    await curr_service.update_rate("USD", Decimal("12800.00"))
    await curr_service.update_rate("EUR", Decimal("14000.00"))

    rates = {
        "USD": Decimal("12800.00"),
        "EUR": Decimal("14000.00"),
    }

    # Convert 100 USD to UZS -> 1 280 000 UZS
    in_uzs = CurrencyService.convert(Decimal("100"), "USD", "UZS", rates)
    assert in_uzs == Decimal("1280000.00")

    # Convert 1 280 000 UZS to USD -> 100 USD
    back_to_usd = CurrencyService.convert(Decimal("1280000"), "UZS", "USD", rates)
    assert back_to_usd == Decimal("100.00")
