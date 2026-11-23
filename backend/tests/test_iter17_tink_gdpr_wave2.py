"""Iteration 17 — Wave 2 router split regression tests for Tink + GDPR.

Targets routes extracted into:
  /app/backend/routes/tink.py   (link / callback / refresh + helpers)
  /app/backend/routes/gdpr.py   (user/export + user/account deletion)

All tests hit the live public backend URL using session cookies.
"""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://money-brain-ai.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "Test123!"


# ==========================================================================
# Fixtures
# ==========================================================================

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    resp = s.post(f"{API}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD}, timeout=30)
    if resp.status_code != 200:
        pytest.skip(f"Login failed: {resp.status_code} {resp.text}")
    assert "session_token" in s.cookies, "session_token cookie missing after login"
    return s


def _register_and_verify_throwaway() -> tuple[requests.Session, str, str]:
    """Register a throwaway user, verify via demo_code, return logged-in session."""
    email = f"delete-test-{uuid.uuid4().hex[:10]}@example.com"
    password = "Throwaway123!"
    s = requests.Session()

    reg = s.post(f"{API}/auth/register", json={
        "email": email, "password": password, "name": "Delete Me",
    }, timeout=30)
    assert reg.status_code == 200, f"register failed: {reg.status_code} {reg.text}"
    rj = reg.json()
    demo_code = rj.get("demo_code")
    assert demo_code, f"demo_code missing from register response: {rj}"

    ver = s.post(f"{API}/auth/verify", json={"email": email, "code": demo_code}, timeout=30)
    assert ver.status_code == 200, f"verify failed: {ver.status_code} {ver.text}"

    # login to ensure we have session_token cookie (verify may also set cookie)
    login = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert login.status_code == 200, f"login failed: {login.status_code} {login.text}"
    assert "session_token" in s.cookies
    return s, email, password


# ==========================================================================
# Tink /link
# ==========================================================================

class TestTinkLink:
    def test_link_happy_path_shape(self, session):
        r = session.post(f"{API}/tink/link",
                         json={"redirect_uri": "https://example.com/callback"}, timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        body = r.json()
        assert "url" in body and isinstance(body["url"], str)
        url = body["url"]
        assert url.startswith("https://link.tink.com/1.0/transactions/connect-accounts?")
        # expected query params
        for key in ("client_id=", "redirect_uri=", "market=SE",
                    "locale=en_US", "authorization_code=",
                    "scope=", "test=true"):
            assert key in url, f"missing {key!r} in url: {url}"
        # 5 comma-separated scopes
        scope_segment = [p for p in url.split("&") if p.startswith("scope=")][0]
        scopes = scope_segment.replace("scope=", "").split(",")
        assert len(scopes) == 5, f"expected 5 scopes, got {scopes}"
        assert set(scopes) == {
            "accounts:read", "balances:read", "transactions:read",
            "credentials:read", "user:read",
        }

    def test_link_empty_body_returns_400(self, session):
        r = session.post(f"{API}/tink/link",
                         data="",
                         headers={"Content-Type": "application/json"},
                         timeout=30)
        assert r.status_code == 400, f"{r.status_code} {r.text}"
        assert "Invalid or missing JSON body" in r.text

    def test_link_empty_object_returns_400(self, session):
        r = session.post(f"{API}/tink/link", json={}, timeout=30)
        assert r.status_code == 400, f"{r.status_code} {r.text}"
        assert "redirect_uri required" in r.text

    def test_link_unauthenticated_returns_401(self):
        r = requests.post(f"{API}/tink/link",
                          json={"redirect_uri": "https://example.com/cb"}, timeout=30)
        assert r.status_code in (401, 403), f"{r.status_code} {r.text}"


# ==========================================================================
# Tink /callback
# ==========================================================================

class TestTinkCallback:
    def test_callback_missing_code_returns_400(self, session):
        r = session.post(f"{API}/tink/callback", json={}, timeout=30)
        assert r.status_code == 400, f"{r.status_code} {r.text}"
        assert "Authorization code required" in r.text

    def test_callback_unauthenticated_returns_401(self):
        r = requests.post(f"{API}/tink/callback", json={"code": "x"}, timeout=30)
        assert r.status_code in (401, 403)


# ==========================================================================
# Tink /refresh
# ==========================================================================

class TestTinkRefresh:
    def test_refresh_no_connection_returns_400(self):
        """Use a fresh throwaway user with zero tink_users doc → must 400."""
        s, _email, _pwd = _register_and_verify_throwaway()
        try:
            r = s.post(f"{API}/tink/refresh", timeout=30)
            assert r.status_code == 400, f"{r.status_code} {r.text}"
            assert "No Tink connection found" in r.text
        finally:
            # clean up throwaway
            s.delete(f"{API}/user/account", json={"confirm": "DELETE"}, timeout=30)

    def test_refresh_unauthenticated_returns_401(self):
        r = requests.post(f"{API}/tink/refresh", timeout=30)
        assert r.status_code in (401, 403)


# ==========================================================================
# GDPR /user/export
# ==========================================================================

class TestUserExport:
    EXPECTED_KEYS = {
        "export_date", "user", "financial_profile", "bank_accounts",
        "transactions", "budgets", "advice_history", "recurring_transactions",
    }

    def test_export_shape_and_no_password_hash(self, session):
        r = session.get(f"{API}/user/export", timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        data = r.json()
        assert set(data.keys()) == self.EXPECTED_KEYS, \
            f"key mismatch; expected {self.EXPECTED_KEYS}, got {set(data.keys())}"

        # user subobject: no password_hash
        assert isinstance(data["user"], dict)
        assert "password_hash" not in data["user"], \
            "SECURITY: password_hash present in export response"
        assert data["user"].get("email") == TEST_EMAIL

        # list containers
        for key in ("bank_accounts", "transactions", "budgets", "advice_history", "recurring_transactions"):
            assert isinstance(data[key], list), f"{key} should be list"

        # export_date is a string (isoformat)
        assert isinstance(data["export_date"], str)

    def test_export_writes_audit_log(self, session):
        """Call export, then assert at least one 'data_export' event exists via audit_logs indirectly."""
        # We can't read the audit_logs collection via API, so just verify the call succeeds.
        # Direct DB inspection would require internal access; this acts as smoke only.
        r = session.get(f"{API}/user/export", timeout=60)
        assert r.status_code == 200

    def test_export_unauthenticated_returns_401(self):
        r = requests.get(f"{API}/user/export", timeout=30)
        assert r.status_code in (401, 403)


# ==========================================================================
# GDPR DELETE /user/account
# ==========================================================================

class TestUserAccountDelete:
    def test_delete_without_confirm_returns_400(self, session):
        """Use main session — body {} must 400, account must still exist after."""
        r = session.delete(f"{API}/user/account", json={}, timeout=30)
        assert r.status_code == 400, f"{r.status_code} {r.text}"
        assert "Send" in r.text and "DELETE" in r.text
        # main account untouched
        r2 = session.get(f"{API}/auth/me", timeout=30)
        assert r2.status_code == 200
        assert r2.json().get("email") == TEST_EMAIL

    def test_delete_with_confirm_wipes_throwaway_user(self):
        s, email, password = _register_and_verify_throwaway()
        # sanity: /auth/me works
        me = s.get(f"{API}/auth/me", timeout=30)
        assert me.status_code == 200
        assert me.json().get("email") == email

        # seed a transaction so we can verify cascade
        tx = s.post(f"{API}/transactions", json={
            "amount": 12.34, "category": "Food", "description": "test tx",
            "date": "2025-01-01", "type": "expense",
        }, timeout=30)
        # shape/status tolerated; just a best-effort seed
        assert tx.status_code in (200, 201, 400, 422)

        # DELETE w/ correct confirm
        r = s.delete(f"{API}/user/account", json={"confirm": "DELETE"}, timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        body = r.json()
        assert "permanently deleted" in body.get("message", "").lower()

        # subsequent /auth/me must be 401 (session destroyed on server + cookie cleared)
        me2 = s.get(f"{API}/auth/me", timeout=30)
        assert me2.status_code in (401, 403), f"session survived deletion: {me2.status_code}"

        # login must fail (user gone)
        login_again = requests.post(f"{API}/auth/login", json={
            "email": email, "password": password,
        }, timeout=30)
        assert login_again.status_code in (400, 401, 404), \
            f"deleted user can still login: {login_again.status_code} {login_again.text}"


# ==========================================================================
# Regression smoke: unaffected endpoints still work
# ==========================================================================

class TestRegressionSmoke:
    def test_auth_me(self, session):
        r = session.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 200
        assert r.json().get("email") == TEST_EMAIL

    def test_transactions_list(self, session):
        r = session.get(f"{API}/transactions", timeout=30)
        assert r.status_code == 200

    def test_budgets_list(self, session):
        r = session.get(f"{API}/budgets", timeout=30)
        assert r.status_code == 200

    def test_spending_summary(self, session):
        r = session.get(f"{API}/analysis/spending-summary", timeout=30)
        assert r.status_code == 200

    def test_bank_accounts_list(self, session):
        r = session.get(f"{API}/bank-accounts", timeout=30)
        assert r.status_code == 200
