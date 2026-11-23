"""
Iteration 15 — Backend tests for:
  A. POST /api/tink/link stale-user auto-recovery (tink_user_id purged by Tink sandbox)
  B. NEW Portfolio Rebalancing endpoints:
       - POST /api/portfolio/rebalance
       - GET  /api/portfolio/auto-detect
  C. Regression: login, security headers, /tink/link, GDPR export, disconnect cascade
"""
import os
import sys
import uuid
import asyncio
import pytest
import requests
from urllib.parse import urlparse, parse_qs

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://money-brain-ai.preview.emergentagent.com",
).rstrip("/")
EMAIL = "test@example.com"
PASSWORD = "Test123!"

sys.path.insert(0, "/app/backend")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_database")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

_mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
_db = _mongo[os.environ["DB_NAME"]]


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ---------------- Fixtures ----------------

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def user_id(session):
    r = session.get(f"{BASE_URL}/api/auth/me", timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["user_id"]


@pytest.fixture()
def saved_profile_risk(user_id):
    """Snapshot + restore financial_profiles.risk_tolerance so we don't pollute state."""
    original = _run(_db.financial_profiles.find_one({"user_id": user_id}, {"_id": 0, "risk_tolerance": 1}))
    orig_risk = (original or {}).get("risk_tolerance")
    yield
    if orig_risk is None:
        _run(_db.financial_profiles.update_one(
            {"user_id": user_id}, {"$unset": {"risk_tolerance": ""}}
        ))
    else:
        _run(_db.financial_profiles.update_one(
            {"user_id": user_id}, {"$set": {"risk_tolerance": orig_risk}}, upsert=True
        ))


def _assert_valid_tink_link_url(url: str):
    assert url.startswith("https://link.tink.com/1.0/transactions/connect-accounts?"), url
    q = parse_qs(urlparse(url).query)
    assert q.get("authorization_code", [""])[0], "missing authorization_code"
    assert q.get("scope", [""])[0] == \
        "accounts:read,balances:read,transactions:read,credentials:read,user:read"
    assert q.get("market", [""])[0] == "SE"
    assert q.get("test", [""])[0] == "true"


# ---------------- A. Tink stale-user auto-recovery ----------------

class TestTinkStaleUserRecovery:
    def test_tink_link_recovers_from_corrupt_tink_user_id(self, session, user_id):
        # First call to ensure a tink_users doc exists (warms up)
        r0 = session.post(
            f"{BASE_URL}/api/tink/link",
            json={"redirect_uri": f"{BASE_URL}/tink/callback"},
            timeout=60,
        )
        assert r0.status_code == 200, f"initial /tink/link failed: {r0.status_code} {r0.text}"

        # Corrupt the tink_user_id to a value Tink will 404 on
        fake_id = f"stale-user-{uuid.uuid4().hex[:12]}"
        upd = _run(_db.tink_users.update_one(
            {"external_user_id": user_id},
            {"$set": {"tink_user_id": fake_id}},
        ))
        assert upd.matched_count == 1, "no tink_users doc to corrupt (pre-warm failed?)"

        # Call /tink/link again — backend should hit 404, wipe mapping, recreate, and still return URL
        r1 = session.post(
            f"{BASE_URL}/api/tink/link",
            json={"redirect_uri": f"{BASE_URL}/tink/callback"},
            timeout=60,
        )
        assert r1.status_code == 200, f"recovery /tink/link failed: {r1.status_code} {r1.text}"
        data = r1.json()
        assert "url" in data
        _assert_valid_tink_link_url(data["url"])

        # The stored tink_user_id MUST have changed (not still the fake one)
        doc = _run(_db.tink_users.find_one({"external_user_id": user_id}, {"_id": 0}))
        assert doc is not None, "tink_users doc missing after recovery"
        assert doc.get("tink_user_id") and doc["tink_user_id"] != fake_id, \
            f"tink_user_id still stale: {doc.get('tink_user_id')}"


# ---------------- B1. POST /api/portfolio/rebalance ----------------

class TestPortfolioRebalanceEndpoint:
    def test_moderate_drift_returns_correct_shape_and_moves(self, session):
        payload = {
            "holdings": {
                "stocks": 15000, "bonds": 3000, "cash": 2000,
                "real_estate": 0, "alternative": 0,
            },
            "risk_tolerance": "moderate",
        }
        r = session.post(f"{BASE_URL}/api/portfolio/rebalance", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()

        assert d["total_value"] == 20000.0
        assert d["risk_tolerance"] == "moderate"
        assert d["current_allocation"]["stocks"] == 75.0
        assert d["target_allocation"]["stocks"] == 60
        assert d["drift"]["stocks"] == 15.0
        assert d["needs_rebalance"] is True
        assert d["max_drift_pct"] == 15.0
        assert "overweight" in d["summary"].lower() or "rebalance" in d["summary"].lower()

        # Moves sorted by |delta| desc
        deltas = [abs(m["delta"]) for m in d["moves"]]
        assert deltas == sorted(deltas, reverse=True), f"moves not sorted desc: {deltas}"

        moves_by_asset = {m["asset_class"]: m for m in d["moves"]}
        assert "stocks" in moves_by_asset, "missing stocks move"
        assert moves_by_asset["stocks"]["action"] == "sell"
        assert moves_by_asset["stocks"]["delta"] == -3000.0

        assert "bonds" in moves_by_asset, "missing bonds move"
        assert moves_by_asset["bonds"]["action"] == "buy"
        assert moves_by_asset["bonds"]["delta"] == 2000.0

    def test_falls_back_to_profile_risk_tolerance(self, session, user_id, saved_profile_risk):
        _run(_db.financial_profiles.update_one(
            {"user_id": user_id},
            {"$set": {"risk_tolerance": "aggressive"}},
            upsert=True,
        ))
        payload = {"holdings": {"stocks": 15000, "bonds": 3000, "cash": 2000}}
        r = session.post(f"{BASE_URL}/api/portfolio/rebalance", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["risk_tolerance"] == "aggressive"
        assert d["target_allocation"]["stocks"] == 80

    def test_all_zero_holdings(self, session):
        payload = {
            "holdings": {"stocks": 0, "bonds": 0, "cash": 0, "real_estate": 0, "alternative": 0},
            "risk_tolerance": "moderate",
        }
        r = session.post(f"{BASE_URL}/api/portfolio/rebalance", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total_value"] == 0
        assert d["needs_rebalance"] is False
        assert d["moves"] == []
        assert "add holdings" in d["summary"].lower()

    def test_no_rebalance_when_matches_target(self, session):
        # Aggressive target: stocks 80, bonds 5, cash 2, real_estate 8, alternative 5
        payload = {
            "holdings": {
                "stocks": 8000, "bonds": 500, "cash": 200,
                "real_estate": 800, "alternative": 500,
            },
            "risk_tolerance": "aggressive",
        }
        r = session.post(f"{BASE_URL}/api/portfolio/rebalance", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["needs_rebalance"] is False, f"expected balanced, got drift={d.get('drift')}"
        assert d["summary"] == "Your portfolio is well-balanced. No rebalancing needed right now."

    def test_unknown_risk_falls_back_to_moderate(self, session):
        payload = {
            "holdings": {"stocks": 10000, "bonds": 10000},
            "risk_tolerance": "extreme",
        }
        r = session.post(f"{BASE_URL}/api/portfolio/rebalance", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["risk_tolerance"] == "moderate"
        assert d["target_allocation"] == {
            "stocks": 60, "bonds": 25, "cash": 5, "real_estate": 7, "alternative": 3
        }


# ---------------- B2. GET /api/portfolio/auto-detect ----------------

class TestPortfolioAutoDetect:
    def test_auto_detect_with_zero_accounts(self, session, user_id):
        # Clean bank_accounts for the user to guarantee 0-account state
        _run(_db.bank_accounts.delete_many({"user_id": user_id}))
        r = session.get(f"{BASE_URL}/api/portfolio/auto-detect", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total_value"] == 0
        assert d["accounts_used"] == 0
        assert d["accounts_seen"] == 0
        assert d["detected_holdings"] == {"stocks": 0, "bonds": 0, "cash": 0, "real_estate": 0, "alternative": 0}
        assert d["needs_rebalance"] is False
        # Shape parity with rebalance
        for key in ("current_allocation", "target_allocation", "drift", "moves", "summary", "risk_tolerance"):
            assert key in d, f"missing key {key}"

    def test_auto_detect_with_seeded_accounts(self, session, user_id):
        # Clean + seed
        _run(_db.bank_accounts.delete_many({"user_id": user_id}))
        seeded = [
            {"user_id": user_id, "account_id": f"TEST_sav_{uuid.uuid4().hex[:6]}",
             "name": "TEST Savings", "type": "savings", "balance": 5000, "institution": "TEST"},
            {"user_id": user_id, "account_id": f"TEST_chk_{uuid.uuid4().hex[:6]}",
             "name": "TEST Checking", "type": "checking", "balance": 2000, "institution": "TEST"},
            {"user_id": user_id, "account_id": f"TEST_inv_{uuid.uuid4().hex[:6]}",
             "name": "TEST Investment", "type": "investment", "balance": 10000, "institution": "TEST"},
        ]
        _run(_db.bank_accounts.insert_many([dict(s) for s in seeded]))
        try:
            r = session.get(f"{BASE_URL}/api/portfolio/auto-detect", timeout=30)
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["total_value"] == 17000
            assert d["detected_holdings"]["cash"] == 7000
            assert d["detected_holdings"]["stocks"] == 10000
            assert d["accounts_seen"] == 3
            assert d["accounts_used"] == 3
        finally:
            # Cleanup so other flows (self-heal etc.) aren't perturbed
            _run(_db.bank_accounts.delete_many({"user_id": user_id, "account_id": {"$regex": "^TEST_"}}))


# ---------------- C. Regression ----------------

class TestRegression:
    def test_login_works(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"email": EMAIL, "password": PASSWORD}, timeout=20)
        assert r.status_code == 200, r.text

    def test_security_headers_present(self, session):
        r = session.get(f"{BASE_URL}/api/auth/me", timeout=20)
        headers_lower = {k.lower(): v for k, v in r.headers.items()}
        # Some of: X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security, Referrer-Policy
        assert "x-content-type-options" in headers_lower
        assert headers_lower["x-content-type-options"].lower() == "nosniff"
        assert "x-frame-options" in headers_lower

    def test_gdpr_export(self, session):
        r = session.get(f"{BASE_URL}/api/user/export", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "export_date" in d
        # Should contain some user-scoped data sections
        assert any(k in d for k in ("user", "profile", "bank_accounts", "transactions"))

    def test_tink_link_still_works(self, session):
        r = session.post(
            f"{BASE_URL}/api/tink/link",
            json={"redirect_uri": f"{BASE_URL}/tink/callback"},
            timeout=60,
        )
        assert r.status_code == 200, f"/tink/link failed: {r.status_code} {r.text}"
        _assert_valid_tink_link_url(r.json()["url"])

    def test_bank_disconnect_cascade_still_works(self, session, user_id):
        # Seed a mock account, then disconnect and verify cascade.
        acc_id = f"TEST_disc_{uuid.uuid4().hex[:6]}"
        _run(_db.bank_accounts.insert_one({
            "user_id": user_id, "account_id": acc_id,
            "name": "TEST Disc", "type": "checking", "balance": 100,
            "institution": "TEST", "source": "plaid",
        }))
        _run(_db.transactions.insert_one({
            "user_id": user_id, "account_id": acc_id,
            "transaction_id": f"TEST_tx_{uuid.uuid4().hex[:6]}",
            "amount": 10.0, "type": "expense", "category": "other",
            "description": "TEST", "source": "plaid",
        }))

        r = session.delete(f"{BASE_URL}/api/bank-accounts/{acc_id}", timeout=30)
        assert r.status_code in (200, 204), r.text

        remaining = _run(_db.bank_accounts.count_documents(
            {"user_id": user_id, "account_id": acc_id}))
        assert remaining == 0, "account not deleted"
        txns_left = _run(_db.transactions.count_documents(
            {"user_id": user_id, "account_id": acc_id}))
        assert txns_left == 0, "transactions not cascaded"
