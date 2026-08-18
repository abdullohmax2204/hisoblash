"""Tests for financial load allocation and salary stress analyzer."""

from datetime import date, timedelta
from decimal import Decimal
import pytest

from app.database.models.user import User
from app.services.savings_service import SavingsService
from app.services.user_service import update_user_salary, ensure_user_exists


@pytest.mark.asyncio
async def test_financial_load_analysis_green_level(session, test_user):
    """Test load stress calculation resulting in GREEN level (<= 30%)."""
    sav_service = SavingsService(session)

    # User salary: 10,000,000 UZS / month
    await update_user_salary(session, test_user.id, Decimal("10000000"), pay_cycle_days=30)

    # Create goal: 6,000,000 UZS due in 6 months => ~1,000,000 / month (10% of salary -> GREEN)
    target_date = date.today() + timedelta(days=180)
    await sav_service.create_goal(test_user.id, "Новый Телефон", Decimal("6000000"), target_date)
    await session.commit()

    analysis = await sav_service.get_financial_load_analysis(test_user.id)
    assert analysis["stress_level"] == "green"
    assert analysis["stress_icon"] == "🟢"
    assert analysis["stress_pct"] <= 30.0
    assert len(analysis["goals"]) == 1
    assert analysis["goals"][0]["required_monthly"] > 0
    assert analysis["goals"][0]["required_15day"] == analysis["goals"][0]["required_monthly"] / 2.0


@pytest.mark.asyncio
async def test_financial_load_analysis_yellow_level(session, test_user):
    """Test load stress calculation resulting in YELLOW level (31% - 60%)."""
    sav_service = SavingsService(session)

    # User salary: 10,000,000 UZS / month
    await update_user_salary(session, test_user.id, Decimal("10000000"), pay_cycle_days=15)

    # Create goal: 24,000,000 UZS due in 6 months => ~4,000,000 / month (40% of salary -> YELLOW)
    target_date = date.today() + timedelta(days=180)
    await sav_service.create_goal(test_user.id, "Машина предоплата", Decimal("24000000"), target_date)
    await session.commit()

    analysis = await sav_service.get_financial_load_analysis(test_user.id)
    assert analysis["stress_level"] == "yellow"
    assert analysis["stress_icon"] == "🟡"
    assert 30.0 < analysis["stress_pct"] <= 60.0


@pytest.mark.asyncio
async def test_financial_load_analysis_red_level(session, test_user):
    """Test load stress calculation resulting in RED level (> 60%)."""
    sav_service = SavingsService(session)

    # User salary: 5,000,000 UZS / month
    await update_user_salary(session, test_user.id, Decimal("5000000"), pay_cycle_days=30)

    # Create goal: 20,000,000 UZS due in 4 months => ~5,000,000 / month (100% of salary -> RED)
    target_date = date.today() + timedelta(days=120)
    await sav_service.create_goal(test_user.id, "Квартира ремонт", Decimal("20000000"), target_date)
    await session.commit()

    analysis = await sav_service.get_financial_load_analysis(test_user.id)
    assert analysis["stress_level"] == "red"
    assert analysis["stress_icon"] == "🔴"
    assert analysis["stress_pct"] > 60.0
