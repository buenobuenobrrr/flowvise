"""MVP happy-path tests: Auth → Accounts → Spending → Budgets.

Runs against a live local API (uvicorn + Mongo). Set:
  REACT_APP_BACKEND_URL=http://127.0.0.1:8000
"""
from __future__ import annotations

import os
import time
import uuid

import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
API = f"{BASE}/api"


def _unique_user():
    suffix = uuid.uuid4().hex[:8]
    return {
        "name": "MVP Tester",
        "email": f"mvp.{suffix}@example.com",
        "password": "TestPass123!",
    }


@pytest.fixture(scope="module")
def session_user():
    """Register + verify a fresh user; yield (token, email, password)."""
    user = _unique_user()
    reg = requests.post(f"{API}/auth/register", json=user, timeout=15)
    assert reg.status_code == 200, reg.text
    body = reg.json()
    assert body.get("requires_verification") is True
    code = body["demo_code"]
    assert code and len(str(code)) == 6

    ver = requests.post(
        f"{API}/auth/verify",
        json={"email": user["email"], "code": code},
        timeout=15,
    )
    assert ver.status_code == 200, ver.text
    token = ver.json()["access_token"]
    assert token
    return token, user["email"], user["password"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def test_health():
    r = requests.get(f"{API}/health", timeout=10)
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_login_and_me(session_user):
    token, email, password = session_user
    login = requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )
    assert login.status_code == 200, login.text
    assert login.json()["access_token"]

    me = requests.get(f"{API}/auth/me", headers=_auth(token), timeout=10)
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_demo_accounts_spending_budgets(session_user):
    token, _, _ = session_user
    headers = _auth(token)

    link = requests.post(f"{API}/plaid/link-token", headers=headers, timeout=15)
    assert link.status_code == 200

    exchange = requests.post(
        f"{API}/plaid/exchange-token",
        headers=headers,
        json={"public_token": "demo", "institution_name": "N26"},
        timeout=15,
    )
    assert exchange.status_code == 200, exchange.text
    assert exchange.json()["transactions_imported"] > 0

    accounts = requests.get(f"{API}/bank-accounts", headers=headers, timeout=15)
    assert accounts.status_code == 200
    assert len(accounts.json()) >= 1

    spending = requests.get(f"{API}/analysis/spending-summary", headers=headers, timeout=15)
    assert spending.status_code == 200
    assert spending.json()["transaction_count"] >= 1

    readiness = requests.get(
        f"{API}/analysis/investment-readiness", headers=headers, timeout=15
    )
    assert readiness.status_code == 200
    assert "safe_to_invest" in readiness.json()

    budget = requests.post(
        f"{API}/budgets",
        headers=headers,
        json={"category": "Food & Dining", "limit": 400, "period": "monthly"},
        timeout=15,
    )
    assert budget.status_code == 200, budget.text
    budget_id = budget.json()["budget_id"]

    budgets = requests.get(f"{API}/budgets", headers=headers, timeout=15)
    assert budgets.status_code == 200
    assert any(b["budget_id"] == budget_id for b in budgets.json())

    alerts = requests.get(f"{API}/budgets/alerts", headers=headers, timeout=15)
    assert alerts.status_code == 200
    assert "alerts" in alerts.json()


def test_ai_advisor_stubs_without_key(session_user):
    token, _, _ = session_user
    r = requests.post(
        f"{API}/advisor/advice",
        headers=_auth(token),
        json={"question": "Should I invest?"},
        timeout=15,
    )
    # Without emergentintegrations / key, expect graceful 503
    assert r.status_code == 503, r.text
