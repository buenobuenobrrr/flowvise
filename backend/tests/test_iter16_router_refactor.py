"""
Iteration 16 — Backend regression tests for the modular router split:
  - /api/portfolio/* moved to routes/portfolio.py
  - /api/simulation/* moved to routes/simulator.py
  - core.py re-exports shared deps

Goal: ensure response shapes and behavior are byte-identical to pre-refactor,
plus all unrelated endpoints still work.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://money-brain-ai.preview.emergentagent.com",
).rstrip("/")
EMAIL = "test@example.com"
PASSWORD = "Test123!"


# ---------- Fixtures ----------

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


# ---------- Portfolio: /api/portfolio/rebalance shape ----------

class TestPortfolioRebalance:
    EXPECTED_KEYS = {
        "total_value", "current_allocation", "target_allocation",
        "drift", "moves", "needs_rebalance", "max_drift_pct",
        "summary", "risk_tolerance",
    }

    def test_rebalance_moderate_drift_shape(self, session):
        body = {
            "holdings": {"stocks": 10000, "bonds": 1000, "cash": 500,
                         "real_estate": 0, "alternative": 0},
            "risk_tolerance": "moderate",
        }
        r = session.post(f"{BASE_URL}/api/portfolio/rebalance", json=body, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Shape parity
        missing = self.EXPECTED_KEYS - set(data.keys())
        assert not missing, f"missing keys after refactor: {missing}"
        # Risk tier preserved
        assert data["risk_tolerance"] == "moderate"
        # Total = sum holdings
        assert data["total_value"] == pytest.approx(11500, abs=0.01)
        # Targets sum to 100
        assert sum(data["target_allocation"].values()) == 100
        # Drift detected (stocks heavily overweight vs moderate 60%)
        assert data["needs_rebalance"] is True
        assert data["max_drift_pct"] > 5.0
        # Moves list well-formed
        assert isinstance(data["moves"], list)
        for m in data["moves"]:
            assert {"asset_class", "current_value", "current_pct", "target_pct",
                    "target_value", "delta", "action"}.issubset(m.keys())
            assert m["action"] in ("buy", "sell")

    def test_rebalance_already_balanced_no_moves(self, session):
        # Conservative: stocks 30/bonds 50/cash 15/real_estate 5/alternative 0
        body = {
            "holdings": {"stocks": 3000, "bonds": 5000, "cash": 1500,
                         "real_estate": 500, "alternative": 0},
            "risk_tolerance": "conservative",
        }
        r = session.post(f"{BASE_URL}/api/portfolio/rebalance", json=body, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["needs_rebalance"] is False
        assert data["moves"] == []
        assert "well-balanced" in data["summary"].lower()

    def test_rebalance_zero_holdings(self, session):
        r = session.post(
            f"{BASE_URL}/api/portfolio/rebalance",
            json={"holdings": {}, "risk_tolerance": "aggressive"},
            timeout=30,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total_value"] == 0.0
        assert data["risk_tolerance"] == "aggressive"
        assert data["needs_rebalance"] is False
        assert data["moves"] == []

    def test_rebalance_unknown_risk_falls_back_to_moderate(self, session):
        r = session.post(
            f"{BASE_URL}/api/portfolio/rebalance",
            json={"holdings": {"stocks": 100}, "risk_tolerance": "ultra_yolo"},
            timeout=30,
        )
        assert r.status_code == 200
        assert r.json()["risk_tolerance"] == "moderate"

    def test_rebalance_requires_auth(self):
        r = requests.post(
            f"{BASE_URL}/api/portfolio/rebalance",
            json={"holdings": {}}, timeout=30,
        )
        assert r.status_code in (401, 403)


# ---------- Portfolio: /api/portfolio/auto-detect shape ----------

class TestPortfolioAutoDetect:
    EXTRA_KEYS = {"detected_holdings", "counted_accounts",
                  "accounts_seen", "accounts_used"}

    def test_auto_detect_shape(self, session):
        r = session.get(f"{BASE_URL}/api/portfolio/auto-detect", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Base rebalance shape
        for k in ("total_value", "current_allocation", "target_allocation",
                  "drift", "moves", "needs_rebalance", "max_drift_pct",
                  "summary", "risk_tolerance"):
            assert k in data, f"missing base key {k}"
        # Plus extras
        for k in self.EXTRA_KEYS:
            assert k in data, f"missing extra key {k}"
        assert isinstance(data["detected_holdings"], dict)
        assert isinstance(data["counted_accounts"], list)
        assert isinstance(data["accounts_seen"], int)
        assert isinstance(data["accounts_used"], int)
        assert data["accounts_used"] <= data["accounts_seen"]

    def test_auto_detect_query_param_overrides_risk(self, session):
        r1 = session.get(
            f"{BASE_URL}/api/portfolio/auto-detect?risk_tolerance=conservative",
            timeout=30,
        )
        r2 = session.get(
            f"{BASE_URL}/api/portfolio/auto-detect?risk_tolerance=aggressive",
            timeout=30,
        )
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["risk_tolerance"] == "conservative"
        assert r2.json()["risk_tolerance"] == "aggressive"
        # target allocations differ
        assert r1.json()["target_allocation"] != r2.json()["target_allocation"]


# ---------- Simulation: /api/simulation/simple ----------

class TestSimulationSimple:
    SUMMARY_KEYS = {"final_balance", "total_invested", "total_gains",
                    "return_pct", "years", "annual_return"}

    def test_simple_shape_and_math(self, session):
        body = {
            "initial_investment": 10000,
            "monthly_contribution": 500,
            "years": 10,
            "expected_return": 0.07,
            "risk_level": "moderate",
        }
        r = session.post(f"{BASE_URL}/api/simulation/simple", json=body, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "timeline" in data and isinstance(data["timeline"], list)
        assert len(data["timeline"]) <= 65   # capped ~60 points
        assert len(data["timeline"]) > 0
        assert "summary" in data
        missing = self.SUMMARY_KEYS - set(data["summary"].keys())
        assert not missing, f"summary missing keys: {missing}"
        s = data["summary"]
        assert s["years"] == 10
        assert s["annual_return"] == pytest.approx(7.0, abs=0.001)
        assert s["total_invested"] == pytest.approx(10000 + 500 * 12 * 10, abs=1.0)
        # Final > invested @ 7% return
        assert s["final_balance"] > s["total_invested"]
        # Sanity: ~106639 per smoke test (10k initial only, no contributions)
        # Re-check no-contribution variant:
        r2 = session.post(
            f"{BASE_URL}/api/simulation/simple",
            json={"initial_investment": 50000, "monthly_contribution": 0,
                  "years": 10, "expected_return": 0.07},
            timeout=30,
        )
        assert r2.status_code == 200
        s2 = r2.json()["summary"]
        # 50000 * (1.07)^10 ≈ 98357
        assert 95000 < s2["final_balance"] < 105000

    def test_simple_zero_investment(self, session):
        r = session.post(
            f"{BASE_URL}/api/simulation/simple",
            json={"initial_investment": 0, "monthly_contribution": 0,
                  "years": 5, "expected_return": 0.05},
            timeout=30,
        )
        assert r.status_code == 200
        s = r.json()["summary"]
        assert s["final_balance"] == 0
        assert s["return_pct"] == 0


# ---------- Simulation: /api/simulation/monte-carlo ----------

class TestSimulationMonteCarlo:
    SUMMARY_KEYS = {"simulations_run", "years", "total_invested",
                    "worst_case", "p10", "median", "p90", "best_case",
                    "probability_of_profit", "expected_return_pct",
                    "volatility_pct"}

    def test_monte_carlo_shape(self, session):
        body = {
            "initial_investment": 10000,
            "monthly_contribution": 200,
            "years": 10,
            "expected_return": 0.07,
            "volatility": 0.15,
            "simulations": 200,
        }
        r = session.post(f"{BASE_URL}/api/simulation/monte-carlo",
                         json=body, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "percentile_timeline" in data
        assert isinstance(data["percentile_timeline"], list)
        assert len(data["percentile_timeline"]) > 0
        first_pt = data["percentile_timeline"][0]
        for k in ("point", "year", "p10", "p25", "p50", "p75", "p90"):
            assert k in first_pt
        assert "summary" in data
        s = data["summary"]
        missing = self.SUMMARY_KEYS - set(s.keys())
        assert not missing, f"summary missing keys: {missing}"
        assert s["simulations_run"] == 200
        assert s["years"] == 10
        # Percentile order
        assert s["worst_case"] <= s["p10"] <= s["median"] <= s["p90"] <= s["best_case"]
        assert 0 <= s["probability_of_profit"] <= 100

    def test_monte_carlo_simulations_capped_at_1000(self, session):
        body = {
            "initial_investment": 1000, "monthly_contribution": 0,
            "years": 5, "expected_return": 0.07, "volatility": 0.15,
            "simulations": 5000,  # request more
        }
        r = session.post(f"{BASE_URL}/api/simulation/monte-carlo",
                         json=body, timeout=120)
        assert r.status_code == 200
        assert r.json()["summary"]["simulations_run"] == 1000


# ---------- Other endpoints (smoke regression after refactor) ----------

class TestUnrelatedEndpointsRegression:
    def test_auth_me(self, session):
        r = session.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert r.status_code == 200
        assert "user_id" in r.json()

    def test_categories(self, session):
        r = session.get(f"{BASE_URL}/api/categories", timeout=30)
        assert r.status_code == 200
        data = r.json()
        # Server returns {all, custom, default}
        assert "all" in data and "default" in data

    def test_bank_accounts(self, session):
        r = session.get(f"{BASE_URL}/api/bank-accounts", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_transactions(self, session):
        r = session.get(f"{BASE_URL}/api/transactions", timeout=30)
        assert r.status_code == 200

    def test_budgets(self, session):
        r = session.get(f"{BASE_URL}/api/budgets", timeout=30)
        assert r.status_code == 200

    def test_spending_summary(self, session):
        r = session.get(f"{BASE_URL}/api/analysis/spending-summary", timeout=30)
        assert r.status_code == 200

    def test_investment_readiness(self, session):
        r = session.get(f"{BASE_URL}/api/analysis/investment-readiness", timeout=30)
        assert r.status_code == 200

    def test_income_breakdown(self, session):
        r = session.get(f"{BASE_URL}/api/analysis/income-breakdown", timeout=30)
        assert r.status_code == 200

    def test_analysis_auto_detect(self, session):
        r = session.get(f"{BASE_URL}/api/analysis/auto-detect", timeout=30)
        assert r.status_code == 200

    def test_user_export_gdpr(self, session):
        r = session.get(f"{BASE_URL}/api/user/export", timeout=30)
        assert r.status_code == 200
        # Should be JSON dump of user data
        data = r.json()
        assert isinstance(data, dict)

    def test_tink_link(self, session):
        # POST /tink/link requires redirect_uri in body
        r = session.post(
            f"{BASE_URL}/api/tink/link",
            json={"redirect_uri": "https://example.com/callback"},
            timeout=30,
        )
        # 200 = ok; 502/503 = upstream/creds; 409 swallowed internally
        assert r.status_code in (200, 502, 503), r.text


# ---------- Security headers ----------

class TestSecurityHeaders:
    def test_security_headers_on_portfolio(self, session):
        r = session.post(
            f"{BASE_URL}/api/portfolio/rebalance",
            json={"holdings": {}}, timeout=30,
        )
        assert r.headers.get("x-content-type-options", "").lower() == "nosniff"
        assert r.headers.get("x-frame-options", "").upper() in ("DENY", "SAMEORIGIN")

    def test_security_headers_on_simulator(self, session):
        r = session.post(
            f"{BASE_URL}/api/simulation/simple",
            json={"initial_investment": 100, "years": 1}, timeout=30,
        )
        assert r.headers.get("x-content-type-options", "").lower() == "nosniff"
        assert r.headers.get("x-frame-options", "").upper() in ("DENY", "SAMEORIGIN")
