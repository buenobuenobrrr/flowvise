"""Portfolio + Simulator + AI Advisor paths against a live local API.

Requires uvicorn + Mongo. Set:
  REACT_APP_BACKEND_URL=http://127.0.0.1:8000

OPENAI_API_KEY should be unset (or empty) for the 503 advisor assertion.
With a key present, the advisor success path is skipped unless
FLOWWISE_TEST_OPENAI=1 is set (avoids accidental billed calls in CI).
"""
from __future__ import annotations

import os
import uuid
from unittest import mock

import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
API = f"{BASE}/api"


def _unique_user():
    suffix = uuid.uuid4().hex[:8]
    return {
        "name": "Portfolio Tester",
        "email": f"portfolio.{suffix}@example.com",
        "password": "TestPass123!",
    }


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def session_user():
    user = _unique_user()
    reg = requests.post(f"{API}/auth/register", json=user, timeout=15)
    assert reg.status_code == 200, reg.text
    code = reg.json()["demo_code"]

    ver = requests.post(
        f"{API}/auth/verify",
        json={"email": user["email"], "code": code},
        timeout=15,
    )
    assert ver.status_code == 200, ver.text
    token = ver.json()["access_token"]
    return token, user


@pytest.fixture(scope="module")
def demo_linked(session_user):
    token, _ = session_user
    headers = _auth(token)
    exchange = requests.post(
        f"{API}/plaid/exchange-token",
        headers=headers,
        json={"public_token": "demo", "institution_name": "N26"},
        timeout=15,
    )
    assert exchange.status_code == 200, exchange.text
    body = exchange.json()
    assert body["transactions_imported"] > 0
    types = {a["type"] for a in body["accounts"]}
    assert "checking" in types
    assert "savings" in types
    assert "investment" in types
    return token


def test_portfolio_rebalance_manual(session_user):
    token, _ = session_user
    r = requests.post(
        f"{API}/portfolio/rebalance",
        headers=_auth(token),
        json={
            "holdings": {
                "stocks": 10000,
                "bonds": 2000,
                "cash": 1000,
                "real_estate": 0,
                "alternative": 0,
            },
            "risk_tolerance": "moderate",
        },
        timeout=15,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total_value"] == 13000
    assert data["risk_tolerance"] == "moderate"
    assert "current_allocation" in data
    assert "target_allocation" in data
    assert "moves" in data
    assert data["needs_rebalance"] is True


def test_portfolio_auto_detect_from_demo(demo_linked):
    token = demo_linked
    r = requests.get(
        f"{API}/portfolio/auto-detect?risk_tolerance=moderate",
        headers=_auth(token),
        timeout=15,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total_value"] > 0
    assert data["accounts_used"] >= 3
    assert data["detected_holdings"]["cash"] > 0
    assert data["detected_holdings"]["stocks"] > 0
    assert "current_allocation" in data
    assert "moves" in data


def test_simulation_simple(session_user):
    token, _ = session_user
    r = requests.post(
        f"{API}/simulation/simple",
        headers=_auth(token),
        json={
            "initial_investment": 5000,
            "monthly_contribution": 200,
            "years": 10,
            "expected_return": 0.07,
            "risk_level": "moderate",
        },
        timeout=15,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["summary"]["final_balance"] > data["summary"]["total_invested"]
    assert len(data["timeline"]) > 0


def test_simulation_monte_carlo(session_user):
    token, _ = session_user
    r = requests.post(
        f"{API}/simulation/monte-carlo",
        headers=_auth(token),
        json={
            "initial_investment": 5000,
            "monthly_contribution": 200,
            "years": 5,
            "expected_return": 0.07,
            "volatility": 0.15,
            "simulations": 100,
        },
        timeout=60,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["summary"]["simulations_run"] == 100
    assert data["summary"]["median"] > 0
    assert len(data["percentile_timeline"]) > 0


def test_advisor_503_without_openai_key(session_user):
    if os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is set in this environment")
    token, _ = session_user
    r = requests.post(
        f"{API}/advisor/advice",
        headers=_auth(token),
        json={"question": "Should I rebalance?"},
        timeout=15,
    )
    assert r.status_code == 503, r.text
    assert "OPENAI_API_KEY" in r.json().get("detail", "")


def test_advisor_history_empty_ok(session_user):
    token, _ = session_user
    r = requests.get(f"{API}/advisor/history", headers=_auth(token), timeout=15)
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


@pytest.mark.skipif(
    os.environ.get("FLOWWISE_TEST_OPENAI") != "1" or not os.environ.get("OPENAI_API_KEY"),
    reason="Set FLOWWISE_TEST_OPENAI=1 and OPENAI_API_KEY to exercise live advisor",
)
def test_advisor_live_openai(session_user):
    token, _ = session_user
    r = requests.post(
        f"{API}/advisor/advice",
        headers=_auth(token),
        json={"question": "Give a one-sentence emergency fund tip."},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("advice")
    assert "disclaimer" in data


def test_advisor_openai_helper_mocked():
    """Unit-level: OpenAI path returns content when client succeeds."""
    import asyncio
    import sys
    from pathlib import Path

    from cryptography.fernet import Fernet

    backend = str(Path(__file__).resolve().parents[1])
    if backend not in sys.path:
        sys.path.insert(0, backend)

    os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
    os.environ.setdefault("DB_NAME", "flowvise_test_import")
    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())
    os.environ.setdefault("COOKIE_SECURE", "false")

    import server as srv  # noqa: WPS433

    class _Msg:
        content = "Mocked AI tip: keep 3-6 months cash."

    class _Choice:
        message = _Msg()

    class _Completion:
        choices = [_Choice()]

    class _Completions:
        async def create(self, **kwargs):
            return _Completion()

    class _Chat:
        completions = _Completions()

    class _Client:
        def __init__(self, **kwargs):
            self.chat = _Chat()

    async def _run():
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False):
            with mock.patch("openai.AsyncOpenAI", _Client):
                text = await srv._call_openai_advisor("sys", "user q")
                assert "Mocked AI tip" in text

    asyncio.run(_run())
