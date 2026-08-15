"""Comprehensive tests for financial logic, MVP scenario, comments, multi-goals, and celebrations."""

from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User
from app.database.models.account import Account
from app.database.models.category import Category
from app.services.account_service import AccountService
from app.services.finance_service import FinanceService
from app.services.savings_service import SavingsService
from app.services.debt_service import DebtService
from app.services.statistics_service import StatisticsService


@pytest.mark.asyncio
async def test_mvp_scenario(
    session: AsyncSession,
    test_user: User,
    test_accounts: dict[str, Account],
    test_categories: dict[str, Category],
):
    """Test the exact MVP scenario from Section 41 of the specification."""
    acc_service = AccountService(session)
    fin_service = FinanceService(session)
    sav_service = SavingsService(session)
    dbt_service = DebtService(session)

    card = test_accounts["card"]
    design_cat = test_categories["income"]
    food_cat = test_categories["expense"]

    # --- Initial State: Card = 3 000 000 ---
    card.balance = Decimal("3000000")
    await session.flush()

    summary = await acc_service.get_bank_summary(test_user.id)
    assert summary["available_funds"] == Decimal("3000000")
    assert summary["savings_balance"] == Decimal("0")
    assert summary["debts_given"] == Decimal("0")
    assert summary["total_capital"] == Decimal("3000000")

    # --- Step 1: Income +500 000 ---
    await fin_service.add_income(
        user_id=test_user.id,
        account_id=card.id,
        category_id=design_cat.id,
        amount=Decimal("500000"),
        description="Фриланс дизайн",
    )
    assert card.balance == Decimal("3500000")
    summary = await acc_service.get_bank_summary(test_user.id)
    assert summary["total_capital"] == Decimal("3500000")

    # --- Step 2: Expense -100 000 ---
    await fin_service.add_expense(
        user_id=test_user.id,
        account_id=card.id,
        category_id=food_cat.id,
        amount=Decimal("100000"),
        description="Супермаркет Корзинка",
    )
    assert card.balance == Decimal("3400000")
    summary = await acc_service.get_bank_summary(test_user.id)
    assert summary["total_capital"] == Decimal("3400000")

    # --- Step 3: Savings 500 000 ---
    await sav_service.deposit(
        user_id=test_user.id,
        source_account_id=card.id,
        amount=Decimal("500000"),
    )
    assert card.balance == Decimal("2900000")
    summary = await acc_service.get_bank_summary(test_user.id)
    assert summary["available_funds"] == Decimal("2900000")
    assert summary["savings_balance"] == Decimal("500000")
    assert summary["total_capital"] == Decimal("3400000")  # Capital unchanged!

    # --- Step 4: Debt Given 300 000 ---
    debt, _, _ = await dbt_service.give_debt(
        user_id=test_user.id,
        person_name="Азиз",
        amount=Decimal("300000"),
        account_id=card.id,
    )
    assert card.balance == Decimal("2600000")
    summary = await acc_service.get_bank_summary(test_user.id)
    assert summary["available_funds"] == Decimal("2600000")
    assert summary["savings_balance"] == Decimal("500000")
    assert summary["debts_given"] == Decimal("300000")
    assert summary["total_capital"] == Decimal("3400000")  # Capital unchanged!

    # --- Step 5: Debt Returned 100 000 ---
    await dbt_service.return_debt(
        user_id=test_user.id,
        debt_id=debt.id,
        amount=Decimal("100000"),
        account_id=card.id,
    )
    assert card.balance == Decimal("2700000")
    summary = await acc_service.get_bank_summary(test_user.id)
    assert summary["available_funds"] == Decimal("2700000")
    assert summary["savings_balance"] == Decimal("500000")
    assert summary["debts_given"] == Decimal("200000")
    assert summary["total_capital"] == Decimal("3400000")  # Capital unchanged!


@pytest.mark.asyncio
async def test_multiple_savings_goals_and_notifications(
    session: AsyncSession,
    test_user: User,
    test_accounts: dict[str, Account],
):
    """Test having 3 goals simultaneously, total target sum, and notification upon reaching a goal."""
    sav_service = SavingsService(session)
    card = test_accounts["card"]
    card.balance = Decimal("10000000")

    # Add 3 goals
    g1 = await sav_service.create_goal(test_user.id, "Наушники", Decimal("1000000"))
    g2 = await sav_service.create_goal(test_user.id, "Отпуск", Decimal("5000000"))
    g3 = await sav_service.create_goal(test_user.id, "Ноутбук", Decimal("15000000"))

    overview = await sav_service.get_multi_goals_overview(test_user.id)
    assert len(overview["goals"]) == 3
    assert overview["total_target"] == Decimal("21000000")  # 1M + 5M + 15M
    assert overview["savings_balance"] == Decimal("0")
    assert overview["overall_pct"] == 0

    # Deposit 2 000 000 -> Goal 1 (Наушники 1M) is newly reached!
    _, _, sav_acc, newly_reached = await sav_service.deposit(
        user_id=test_user.id,
        source_account_id=card.id,
        amount=Decimal("2000000"),
    )
    assert sav_acc.balance == Decimal("2000000")
    assert len(newly_reached) == 1
    assert newly_reached[0].name == "Наушники"

    # Deposit another 4 000 000 (total in savings = 6 000 000) -> Goal 2 (Отпуск 5M) reached!
    _, _, sav_acc, newly_reached2 = await sav_service.deposit(
        user_id=test_user.id,
        source_account_id=card.id,
        amount=Decimal("4000000"),
    )
    assert sav_acc.balance == Decimal("6000000")
    assert len(newly_reached2) == 1
    assert newly_reached2[0].name == "Отпуск"

    # Check updated overview
    overview = await sav_service.get_multi_goals_overview(test_user.id)
    assert overview["goals"][0]["is_funded"] is True  # Наушники funded
    assert overview["goals"][1]["is_funded"] is True  # Отпуск funded
    assert overview["goals"][2]["is_funded"] is False  # Ноутбук not yet


@pytest.mark.asyncio
async def test_insufficient_funds_protection(
    session: AsyncSession,
    test_user: User,
    test_accounts: dict[str, Account],
    test_categories: dict[str, Category],
):
    """Test that expense fails when balance is insufficient."""
    fin_service = FinanceService(session)
    card = test_accounts["card"]
    food_cat = test_categories["expense"]
    card.balance = Decimal("50000")

    with pytest.raises(ValueError, match="Недостаточно средств"):
        await fin_service.add_expense(
            user_id=test_user.id,
            account_id=card.id,
            category_id=food_cat.id,
            amount=Decimal("100000"),
        )


@pytest.mark.asyncio
async def test_transaction_delete_rollback(
    session: AsyncSession,
    test_user: User,
    test_accounts: dict[str, Account],
    test_categories: dict[str, Category],
):
    """Test that deleting a transaction restores account balance."""
    fin_service = FinanceService(session)
    card = test_accounts["card"]
    card.balance = Decimal("1000000")

    # Add income with description
    tx, _ = await fin_service.add_income(
        user_id=test_user.id,
        account_id=card.id,
        category_id=test_categories["income"].id,
        amount=Decimal("200000"),
        description="Дизайн логотипа",
    )
    assert card.balance == Decimal("1200000")
    assert tx.description == "Дизайн логотипа"

    # Delete income -> balance restored to 1 000 000
    success = await fin_service.delete_transaction(test_user.id, tx.id)
    assert success is True
    assert card.balance == Decimal("1000000")
