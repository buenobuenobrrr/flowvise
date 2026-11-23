"""
Tests for iteration_12 — bank disconnect cascade + Tink Link delegated-auth.

Covers:
  - POST /api/tink/link returns URL with delegated authorization params
    (authorization_code, scope, market, locale, test=true).
  - DELETE /api/bank-accounts/{account_id} returns transactions_removed
    and actually drops db.transactions count by that number.
  - Last-bank-of-source orphan cleanup for legacy plaid txns without account_id.
  - Last-Tink-account removal drops db.tink_users mapping (assert /tink/refresh -> 400).
  - Newly created mock txns all have account_id pointing to a created bank_account.
  - audit_log entry 'bank_account_disconnected' with required fields.
  - Existing security/auth flow: login + register weak password 400 + headers + GDPR export.
  - GET /api/analysis/investment-readiness still 200 after disconnect.
  - Unit-check _import_tink_data sets account_id from tink_to_internal map.
"""
import os
import sys
import uuid
import pytest
import requests
from urllib.parse import urlparse, parse_qs

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
EMAIL = "test@example.com"
PASSWORD = "Test123!"

# Provide direct DB access so we can verify cascade counts deterministically.
sys.path.insert(0, "/app/backend")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_database")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
import asyncio  # noqa: E402

mongo_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = mongo_client[os.environ["DB_NAME"]]


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def user_id(session):
    me = session.get(f"{BASE_URL}/api/auth/me", timeout=20)
    assert me.status_code == 200
    return me.json()["user_id"]


# ---------- Tink Link delegated-auth URL ----------

class TestTinkLinkDelegatedAuth:
    def test_tink_link_url_has_delegated_auth_params(self, session):
        r = session.post(f"{BASE_URL}/api/tink/link",
                         json={"redirect_uri": "http://127.0.0.1:3000/dashboard/accounts"},
                         timeout=60)
        # If Tink sandbox is reachable we expect 200; if upstream Tink is failing we get 502.
        if r.status_code == 502:
            pytest.skip(f"Tink sandbox upstream unavailable: {r.text}")
        assert r.status_code == 200, f"{r.status_code} {r.text}"

        url = r.json()["url"]
        assert url.startswith("https://link.tink.com/1.0/transactions/connect-accounts?"), url
        q = parse_qs(urlparse(url).query)

        # Required params (delegated-auth flow)
        assert "authorization_code" in q and q["authorization_code"][0], "missing authorization_code"
        assert q.get("scope", [""])[0] == \
            "accounts:read,balances:read,transactions:read,credentials:read,user:read"
        assert q.get("market", [""])[0] == "SE"
        assert q.get("locale", [""])[0] == "en_US"
        assert q.get("test", [""])[0] == "true"
        assert q.get("client_id", [""])[0], "client_id missing"
        assert "redirect_uri" in q


# ---------- Disconnect cascade ----------

def _txn_count(user_id):
    return _run(db.transactions.count_documents({"user_id": user_id}))


def _acc_count(user_id, source=None):
    q = {"user_id": user_id}
    if source:
        q["source"] = source
    return _run(db.bank_accounts.count_documents(q))


class TestDisconnectCascade:
    def test_mock_exchange_creates_accounts_with_account_id(self, session, user_id):
        # Clean any pre-existing plaid data first to make assertions deterministic
        _run(db.bank_accounts.delete_many({"user_id": user_id, "source": "plaid"}))
        _run(db.transactions.delete_many({"user_id": user_id, "source": "plaid"}))

        r = session.post(f"{BASE_URL}/api/plaid/exchange-token",
                         json={"institution_name": "TEST_DemoBank"}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["accounts"]) >= 1
        assert data["transactions_imported"] > 0

        created_acc_ids = {a["account_id"] for a in data["accounts"]}
        # Verify every created mock txn has account_id pointing at one of the new accounts
        txns = _run(db.transactions.find(
            {"user_id": user_id, "source": "plaid"}, {"_id": 0, "account_id": 1}
        ).to_list(1000))
        assert len(txns) > 0
        assert all(t.get("account_id") in created_acc_ids for t in txns), \
            "some plaid txns missing account_id link"

    def test_disconnect_one_account_cascades_transactions(self, session, user_id):
        accounts = _run(db.bank_accounts.find(
            {"user_id": user_id, "source": "plaid"}, {"_id": 0}
        ).to_list(100))
        assert len(accounts) >= 1
        target = accounts[0]["account_id"]

        before_txns = _run(db.transactions.count_documents(
            {"user_id": user_id, "account_id": target}))
        assert before_txns > 0

        total_before = _txn_count(user_id)

        r = session.delete(f"{BASE_URL}/api/bank-accounts/{target}", timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("message") == "Account disconnected"
        assert body.get("transactions_removed") == before_txns, \
            f"expected {before_txns} removed, got {body.get('transactions_removed')}"

        total_after = _txn_count(user_id)
        assert total_before - total_after == before_txns

        # Audit log entry
        log = _run(db.audit_logs.find_one(
            {"user_id": user_id, "action": "bank_account_disconnected",
             "details.account_id": target},
            sort=[("timestamp", -1)]
        ))
        assert log is not None, "audit log bank_account_disconnected not written"
        assert log["details"].get("source") == "plaid"
        assert log["details"].get("transactions_removed") == before_txns

    def test_disconnect_last_plaid_wipes_orphan_legacy_txns(self, session, user_id):
        # Insert a legacy orphan txn (no account_id) to simulate pre-cascade data
        orphan_id = f"txn_orphan_{uuid.uuid4().hex[:8]}"
        _run(db.transactions.insert_one({
            "transaction_id": orphan_id, "user_id": user_id,
            "amount": 9.99, "category": "TEST_orphan", "description": "TEST_orphan",
            "date": "2025-01-01", "type": "expense", "source": "plaid",
            # intentionally no account_id
        }))
        # Confirm orphan present
        assert _run(db.transactions.count_documents(
            {"user_id": user_id, "transaction_id": orphan_id})) == 1

        # Disconnect remaining plaid accounts one by one until none left
        remaining = _run(db.bank_accounts.find(
            {"user_id": user_id, "source": "plaid"}, {"_id": 0, "account_id": 1}
        ).to_list(100))
        assert len(remaining) >= 1

        last_resp = None
        for acc in remaining:
            last_resp = session.delete(
                f"{BASE_URL}/api/bank-accounts/{acc['account_id']}", timeout=20)
            assert last_resp.status_code == 200, last_resp.text

        # Now zero plaid accounts remain
        assert _acc_count(user_id, "plaid") == 0
        # Orphan must have been wiped on the last delete
        assert _run(db.transactions.count_documents(
            {"user_id": user_id, "transaction_id": orphan_id})) == 0
        # And the response of the last delete should report at least the orphan
        assert last_resp.json().get("transactions_removed") >= 1

    def test_disconnect_last_tink_account_removes_tink_users_mapping(self, user_id):
        # Insert a fake tink bank_account + tink_users mapping
        tink_acc_id = f"tink_TEST_{uuid.uuid4().hex[:8]}"
        _run(db.bank_accounts.insert_one({
            "account_id": tink_acc_id, "user_id": user_id, "source": "tink",
            "name": "TEST_Tink", "institution": "TEST", "type": "checking",
            "balance": 0, "mask": "0000", "is_connected": True,
            "tink_account_id": "tinkacc_TEST",
        }))
        _run(db.tink_users.update_one(
            {"external_user_id": user_id},
            {"$set": {"external_user_id": user_id, "tink_user_id": "TEST_tu",
                      "access_token": "TEST"}}, upsert=True))
        assert _run(db.tink_users.find_one({"external_user_id": user_id})) is not None

        # Login with a fresh session to use the disconnect endpoint
        s = requests.Session()
        s.post(f"{BASE_URL}/api/auth/login",
               json={"email": EMAIL, "password": PASSWORD}, timeout=20)
        r = s.delete(f"{BASE_URL}/api/bank-accounts/{tink_acc_id}", timeout=20)
        assert r.status_code == 200, r.text

        # tink_users mapping for this user should now be gone
        assert _run(db.tink_users.find_one({"external_user_id": user_id})) is None

        # /api/tink/refresh should now return 400 'No Tink connection found'
        r2 = s.post(f"{BASE_URL}/api/tink/refresh", json={}, timeout=20)
        assert r2.status_code == 400, r2.text
        assert "No Tink connection" in r2.text or "no tink" in r2.text.lower()

    def test_risk_engine_still_works_after_disconnects(self, session):
        r = session.get(f"{BASE_URL}/api/analysis/investment-readiness", timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        # Fields differ across responses but should contain at least one expected key
        assert any(k in body for k in ("svi", "safe_to_invest", "score", "metrics"))


# ---------- Existing security/auth still intact ----------

class TestSecurityRegression:
    def test_login_ok(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": EMAIL, "password": PASSWORD}, timeout=20)
        assert r.status_code == 200

    def test_register_weak_password_rejected(self):
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"TEST_weak_{uuid.uuid4().hex[:6]}@example.com",
            "password": "weak", "name": "Weak"
        }, timeout=20)
        assert r.status_code == 400

    def test_security_headers_present(self):
        r = requests.get(f"{BASE_URL}/api/health", timeout=20)
        assert r.status_code == 200
        for h in ("x-content-type-options", "x-frame-options",
                  "strict-transport-security", "referrer-policy"):
            assert h in {k.lower() for k in r.headers.keys()}, f"missing {h}"

    def test_gdpr_export(self, session):
        r = session.get(f"{BASE_URL}/api/user/export", timeout=30)
        assert r.status_code == 200


# ---------- Unit-check _import_tink_data linking ----------

class TestImportTinkAccountIdLinking:
    def test_parse_tink_transaction_extracts_tink_account_id(self):
        from server import _parse_tink_transaction
        v1 = {"id": "t1", "amount": -10, "description": "x",
              "date": "2025-01-01", "accountId": "acc-1"}
        out = _parse_tink_transaction(v1)
        assert out["tink_account_id"] == "acc-1"

        v2 = {"id": "t2", "amount": {"value": {"unscaledValue": "-1000", "scale": "2"}},
              "descriptions": {"display": "y"},
              "dates": {"booked": "2025-01-02"}, "accountId": "acc-2"}
        out2 = _parse_tink_transaction(v2)
        assert out2["tink_account_id"] == "acc-2"

    def test_import_links_internal_account_id(self):
        """Run _import_tink_data with monkeypatched fetchers and verify
        transactions get internal account_id from tink_to_internal map."""
        import server
        uid = f"TEST_unit_{uuid.uuid4().hex[:6]}"

        async def fake_accounts(token, retries=3):
            return [{"id": "tinkA", "name": "TEST_A", "balance": 100,
                     "type": "CHECKING", "accountNumber": "0001"}]

        async def fake_txns(token, retries=3):
            return [{"id": "ttx1", "amount": -5, "description": "TEST_txn",
                     "date": "2025-01-01", "accountId": "tinkA"}]

        orig_acc, orig_txn = server._fetch_tink_accounts, server._fetch_tink_transactions
        server._fetch_tink_accounts = fake_accounts
        server._fetch_tink_transactions = fake_txns
        # Patch the long sleep inside _import_tink_data
        import asyncio as _a
        orig_sleep = _a.sleep
        async def fast_sleep(_): return None
        _a.sleep = fast_sleep
        try:
            res = _run(server._import_tink_data(uid, "TEST_token"))
        finally:
            server._fetch_tink_accounts = orig_acc
            server._fetch_tink_transactions = orig_txn
            _a.sleep = orig_sleep

        assert res["accounts_imported"] == 1
        assert res["transactions_imported"] == 1

        acc = _run(db.bank_accounts.find_one(
            {"user_id": uid, "tink_account_id": "tinkA"}, {"_id": 0}))
        assert acc is not None
        internal_id = acc["account_id"]

        txn = _run(db.transactions.find_one(
            {"user_id": uid, "tink_transaction_id": "ttx1"}, {"_id": 0}))
        assert txn is not None
        assert txn["account_id"] == internal_id, \
            f"expected internal {internal_id}, got {txn['account_id']}"

        # Cleanup
        _run(db.bank_accounts.delete_many({"user_id": uid}))
        _run(db.transactions.delete_many({"user_id": uid}))


# ---------- Tink token encryption round-trip ----------

class TestTinkEncryptionRoundTrip:
    def test_encrypt_decrypt_round_trip(self):
        from server import encrypt_sensitive, decrypt_sensitive
        plain = "tink_test_token_" + uuid.uuid4().hex
        enc = encrypt_sensitive(plain)
        assert enc != plain, "encrypted output must differ from plaintext"
        assert isinstance(enc, str) and len(enc) > 0
        # decrypt round-trips back
        assert decrypt_sensitive(enc) == plain
        # backward-compat: plain (non-encrypted) returns as-is
        assert decrypt_sensitive("not-encrypted-legacy-value") == "not-encrypted-legacy-value"
