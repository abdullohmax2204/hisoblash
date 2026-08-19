"""Tests for Telegram Mini App REST API and auth."""

from decimal import Decimal
import hashlib
import hmac
import json
import pytest
from aiohttp.test_utils import TestClient, TestServer

from app.database.database import async_session_factory
from app.database.models.account import Account
from app.database.models.category import Category
from app.database.models.user import User
from app.web.auth import validate_telegram_init_data, get_authenticated_user_id
from app.web.server import create_web_app


def generate_mock_init_data(bot_token: str, user_id: int = 123456789, first_name: str = "TestUser") -> str:
    """Generate valid Telegram initData query string for testing."""
    user_dict = {
        "id": user_id,
        "first_name": first_name,
        "username": "testuser",
    }
    user_json = json.dumps(user_dict, separators=(",", ":"))
    
    data_dict = {
        "auth_date": "1700000000",
        "query_id": "AAHdF6IQAAAAAN0XohD_test",
        "user": user_json,
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data_dict.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    hash_val = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    
    return f"auth_date=1700000000&query_id=AAHdF6IQAAAAAN0XohD_test&user={user_json}&hash={hash_val}"


def test_telegram_auth_validation():
    token = "123456:ABC-DEF-GHI"
    valid_init_data = generate_mock_init_data(token, user_id=987654, first_name="Alex")
    
    # Test valid validation
    user = validate_telegram_init_data(valid_init_data, token)
    assert user is not None
    assert user["id"] == 987654
    assert user["first_name"] == "Alex"

    # Test invalid hash
    tampered_data = valid_init_data.replace("Alex", "Bob")
    assert validate_telegram_init_data(tampered_data, token) is None

    # Test empty
    assert validate_telegram_init_data("", token) is None


@pytest.mark.asyncio
async def test_web_app_endpoints(session, test_user, test_accounts, test_categories):
    """Test REST API endpoints with TestClient."""
    app = create_web_app()
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()

    try:
        # 1. Healthcheck
        resp = await client.get("/health")
        assert resp.status == 200
        text = await resp.text()
        assert "OK" in text

        # 2. Get Summary & Categories
        resp = await client.get("/api/summary")
        assert resp.status == 200
        summary = await resp.json()
        assert "total_capital" in summary
        assert "available_funds" in summary

        resp = await client.get("/api/categories")
        assert resp.status == 200
        cats = await resp.json()
        assert "expense" in cats
        assert "income" in cats

        resp = await client.post("/api/categories", json={"name": "Новая категория", "type": "EXPENSE", "icon": "🎁"})
        assert resp.status == 201
        new_cat = await resp.json()
        assert new_cat["name"] == "Новая категория"

        # 3. Create Account
        resp = await client.post("/api/accounts", json={"name": "Второй счет", "icon": "💳", "initial_balance": 100000})
        assert resp.status == 201
        new_acc = await resp.json()
        assert new_acc["name"] == "Второй счет"
        assert new_acc["balance"] == 100000

        # 4. Add Income
        resp = await client.post("/api/transactions/income", json={
            "account_id": new_acc["id"],
            "category_id": test_categories["income"].id,
            "amount": 50000,
            "description": "Зарплата",
        })
        assert resp.status == 200
        inc_data = await resp.json()
        assert inc_data["new_balance"] == 150000

        # 5. Add Expense
        resp = await client.post("/api/transactions/expense", json={
            "account_id": new_acc["id"],
            "category_id": test_categories["expense"].id,
            "amount": 20000,
            "description": "Обед",
        })
        assert resp.status == 200
        exp_data = await resp.json()
        assert exp_data["new_balance"] == 130000

        # 6. Savings Goals & Deposit
        resp = await client.post("/api/savings/goals", json={"name": "Новый телефон", "target_amount": 500000})
        assert resp.status == 201
        goal = await resp.json()
        assert goal["name"] == "Новый телефон"

        resp = await client.post("/api/savings/deposit", json={
            "source_account_id": new_acc["id"],
            "amount": 30000,
            "description": "Копилка",
        })
        assert resp.status == 200
        sav_data = await resp.json()
        assert sav_data["savings_balance"] >= 30000

        # 7. Debts: Give & Return
        resp = await client.post("/api/debts/give", json={
            "person_name": "Алишер",
            "amount": 25000,
            "account_id": new_acc["id"],
        })
        assert resp.status == 200
        debt_res = await resp.json()
        debt_id = debt_res["debt_id"]

        resp = await client.get("/api/debts")
        assert resp.status == 200
        debts = await resp.json()
        assert len(debts["given"]) >= 1

        resp = await client.post("/api/debts/return", json={
            "debt_id": debt_id,
            "amount": 25000,
            "account_id": new_acc["id"],
        })
        assert resp.status == 200
        ret_res = await resp.json()
        assert ret_res["is_settled"] is True

        # 8. Stats & History
        resp = await client.get("/api/stats?period=month")
        assert resp.status == 200
        stats = await resp.json()
        assert "total_income" in stats

        resp = await client.get("/api/history?page=0&page_size=10")
        assert resp.status == 200
        history = await resp.json()
        assert len(history["transactions"]) > 0

        # 9. Multi-User Profile Switcher API
        resp = await client.get("/api/users")
        assert resp.status == 200
        users_data = await resp.json()
        assert "users" in users_data
        assert "current_user_id" in users_data

        resp = await client.post("/api/users/create", json={"name": "Тестовый профиль 2"})
        assert resp.status == 201
        new_profile = await resp.json()
        assert new_profile["name"] == "Тестовый профиль 2"
        new_profile_id = new_profile["id"]

        # Switch to new profile via header X-Profile-Id
        resp = await client.get("/api/summary", headers={"X-Profile-Id": str(new_profile_id)})
        assert resp.status == 200
        new_summary = await resp.json()
        assert new_summary["user_name"] == "Тестовый профиль 2"

        # Rename profile
        resp = await client.post("/api/users/rename", json={"user_id": new_profile_id, "name": "Работа"})
        assert resp.status == 200
        renamed = await resp.json()
        assert renamed["name"] == "Работа"

        # Delete profile
        resp = await client.post("/api/users/delete", json={"user_id": new_profile_id})
        assert resp.status == 200
        del_res = await resp.json()
        assert del_res["success"] is True

    finally:
        await client.close()
