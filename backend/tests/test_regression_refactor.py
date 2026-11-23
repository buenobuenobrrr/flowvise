"""
Regression test suite for code quality refactoring.
Tests that refactored helper functions and constants work correctly.

Refactored areas:
1. secrets.randbelow for verification codes (instead of random.randint)
2. Extracted helpers: calculate_balance_readiness, aggregate_monthly_spending
3. _build_advisor_context, _ADVISOR_SYSTEM_MESSAGE
4. _run_monte_carlo_finals, _run_monte_carlo_paths
5. _detect_spending_spikes, _detect_unusual_transactions
6. Named constants: SPENDING_SPIKE_THRESHOLD, UNUSUAL_TXN_STD_MULTIPLIER, etc.
"""
import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://127.0.0.1:8000').rstrip('/')

# Test credentials from env or defaults
TEST_EMAIL = os.environ.get('TEST_EMAIL', 'test@example.com')
TEST_PASSWORD = os.environ.get('TEST_PASSWORD', 'Test123!')


class TestAuthEndpoints:
    """Test auth endpoints after secrets.randbelow refactor"""
    
    def test_login_success(self):
        """POST /api/auth/login with correct credentials returns 200"""
        # Create a fresh user to avoid rate limiting
        unique_email = f"TEST_login_{uuid.uuid4().hex[:8]}@test.com"
        
        session = requests.Session()
        
        # Register first
        reg_response = session.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": unique_email, "name": "Login Test", "password": "LoginPass123!"}
        )
        assert reg_response.status_code == 200
        demo_code = reg_response.json()["demo_code"]
        
        # Verify
        session.post(
            f"{BASE_URL}/api/auth/verify",
            json={"email": unique_email, "code": demo_code}
        )
        
        # Now test login
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": unique_email, "password": "LoginPass123!"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == unique_email
        print(f"Login success: {data['user']['email']}")
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/user/account", json={"confirm": "DELETE"})
    
    def test_register_returns_verification_code(self):
        """POST /api/auth/register creates user and returns 6-digit verification code"""
        unique_email = f"TEST_reg_{uuid.uuid4().hex[:8]}@test.com"
        
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": unique_email, "name": "Test User", "password": "TestPass123!"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "demo_code" in data, "Should return demo_code"
        assert data["requires_verification"] is True
        
        # Verify code is 6 digits (from secrets.randbelow)
        code = data["demo_code"]
        assert len(code) == 6, f"Code should be 6 digits, got {len(code)}"
        assert code.isdigit(), f"Code should be numeric, got {code}"
        assert 100000 <= int(code) <= 999999, f"Code should be 100000-999999, got {code}"
        
        print(f"Registration successful, code: {code}")
    
    def test_verify_accepts_valid_code(self):
        """POST /api/auth/verify accepts valid code"""
        unique_email = f"TEST_verify_{uuid.uuid4().hex[:8]}@test.com"
        
        session = requests.Session()
        
        # Register first
        reg_response = session.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": unique_email, "name": "Verify Test", "password": "VerifyPass123!"}
        )
        assert reg_response.status_code == 200
        demo_code = reg_response.json()["demo_code"]
        
        # Verify with correct code
        verify_response = session.post(
            f"{BASE_URL}/api/auth/verify",
            json={"email": unique_email, "code": demo_code}
        )
        assert verify_response.status_code == 200, f"Expected 200, got {verify_response.status_code}"
        
        data = verify_response.json()
        assert "access_token" in data
        assert "user" in data
        print(f"Verification successful for {unique_email}")
        
        # Cleanup - delete the test user
        session.delete(
            f"{BASE_URL}/api/user/account",
            json={"confirm": "DELETE"}
        )
    
    def test_rate_limiting_still_works(self):
        """Rate limiting returns 429 after 5 failed logins"""
        unique_email = f"TEST_ratelimit_{uuid.uuid4().hex[:8]}@test.com"
        
        session = requests.Session()
        
        # Make 5 failed login attempts
        for i in range(5):
            response = session.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": unique_email, "password": "wrongpassword"}
            )
            assert response.status_code == 401, f"Attempt {i+1}: Expected 401, got {response.status_code}"
        
        # 6th attempt should be rate limited
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": unique_email, "password": "wrongpassword"}
        )
        assert response.status_code == 429, f"Expected 429 after 5 attempts, got {response.status_code}"
        assert "Too many attempts" in response.json().get("detail", "")
        print("Rate limiting working correctly")


class TestAnalysisEndpoints:
    """Test analysis endpoints with refactored helpers"""
    
    @pytest.fixture
    def auth_session(self):
        """Create authenticated session with fresh user"""
        unique_email = f"TEST_analysis_{uuid.uuid4().hex[:8]}@test.com"
        session = requests.Session()
        
        # Register
        reg_response = session.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": unique_email, "name": "Analysis Test", "password": "AnalysisPass123!"}
        )
        if reg_response.status_code != 200:
            pytest.skip(f"Registration failed: {reg_response.status_code}")
        
        demo_code = reg_response.json()["demo_code"]
        
        # Verify
        verify_response = session.post(
            f"{BASE_URL}/api/auth/verify",
            json={"email": unique_email, "code": demo_code}
        )
        if verify_response.status_code != 200:
            pytest.skip(f"Verification failed: {verify_response.status_code}")
        
        yield session
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/user/account", json={"confirm": "DELETE"})
    
    def test_spending_summary_returns_valid_data(self, auth_session):
        """GET /api/analysis/spending-summary returns valid data"""
        response = auth_session.get(f"{BASE_URL}/api/analysis/spending-summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify structure - uses aggregate_monthly_spending helper
        assert "total_spending" in data
        assert "average_monthly_spending" in data
        assert "by_category" in data
        assert isinstance(data["by_category"], dict)
        
        print(f"Spending summary: total={data['total_spending']}, avg={data['average_monthly_spending']}")
    
    def test_investment_readiness_returns_status(self, auth_session):
        """GET /api/analysis/investment-readiness returns status field"""
        response = auth_session.get(f"{BASE_URL}/api/analysis/investment-readiness")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Uses calculate_investment_readiness or calculate_balance_readiness helpers
        assert "status" in data, "Should have status field"
        assert data["status"] in ["excellent", "good", "moderate", "not_recommended"]
        assert "safe_to_invest" in data
        assert "confidence_level" in data
        
        print(f"Investment readiness: status={data['status']}, safe_to_invest={data['safe_to_invest']}")
    
    def test_auto_detect_returns_pattern_data(self, auth_session):
        """GET /api/analysis/auto-detect returns pattern data"""
        response = auth_session.get(f"{BASE_URL}/api/analysis/auto-detect")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "detected_income" in data
        assert "detected_subscriptions" in data
        assert isinstance(data["detected_income"], list)
        assert isinstance(data["detected_subscriptions"], list)
        
        print(f"Auto-detect: income patterns={len(data['detected_income'])}, sub patterns={len(data['detected_subscriptions'])}")


class TestBudgetEndpoints:
    """Test budget endpoints with refactored smart alerts"""
    
    @pytest.fixture
    def auth_session(self):
        """Create authenticated session with fresh user"""
        unique_email = f"TEST_budget_{uuid.uuid4().hex[:8]}@test.com"
        session = requests.Session()
        
        # Register
        reg_response = session.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": unique_email, "name": "Budget Test", "password": "BudgetPass123!"}
        )
        if reg_response.status_code != 200:
            pytest.skip(f"Registration failed: {reg_response.status_code}")
        
        demo_code = reg_response.json()["demo_code"]
        
        # Verify
        verify_response = session.post(
            f"{BASE_URL}/api/auth/verify",
            json={"email": unique_email, "code": demo_code}
        )
        if verify_response.status_code != 200:
            pytest.skip(f"Verification failed: {verify_response.status_code}")
        
        yield session
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/user/account", json={"confirm": "DELETE"})
    
    def test_smart_alerts_returns_alerts_array(self, auth_session):
        """GET /api/budgets/smart-alerts returns alerts array"""
        response = auth_session.get(f"{BASE_URL}/api/budgets/smart-alerts")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Uses _detect_spending_spikes and _detect_unusual_transactions helpers
        assert "alerts" in data
        assert isinstance(data["alerts"], list)
        
        # If there are alerts, verify structure
        for alert in data["alerts"]:
            assert "type" in alert
            assert alert["type"] in ["spending_spike", "unusual_transaction"]
            assert "message" in alert
        
        print(f"Smart alerts: {len(data['alerts'])} alerts found")


class TestGdprEndpoints:
    """Test GDPR endpoints"""
    
    @pytest.fixture
    def auth_session(self):
        """Create authenticated session with fresh user"""
        unique_email = f"TEST_gdpr_{uuid.uuid4().hex[:8]}@test.com"
        session = requests.Session()
        
        # Register
        reg_response = session.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": unique_email, "name": "GDPR Test", "password": "GdprPass123!"}
        )
        if reg_response.status_code != 200:
            pytest.skip(f"Registration failed: {reg_response.status_code}")
        
        demo_code = reg_response.json()["demo_code"]
        
        # Verify
        verify_response = session.post(
            f"{BASE_URL}/api/auth/verify",
            json={"email": unique_email, "code": demo_code}
        )
        if verify_response.status_code != 200:
            pytest.skip(f"Verification failed: {verify_response.status_code}")
        
        yield session
        
        # Cleanup (may already be deleted by test)
        try:
            session.delete(f"{BASE_URL}/api/user/account", json={"confirm": "DELETE"})
        except:
            pass
    
    def test_export_returns_user_data(self, auth_session):
        """GET /api/user/export returns user data"""
        response = auth_session.get(f"{BASE_URL}/api/user/export")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "export_date" in data
        assert "user" in data
        assert "financial_profile" in data
        assert "transactions" in data
        assert "bank_accounts" in data
        assert "budgets" in data
        
        # Verify password_hash is not exposed
        assert "password_hash" not in data.get("user", {})
        
        print(f"GDPR export: user={data['user'].get('email')}")


class TestSimulationEndpoints:
    """Test simulation endpoints with refactored Monte Carlo helpers"""
    
    @pytest.fixture
    def auth_session(self):
        """Create authenticated session with fresh user"""
        unique_email = f"TEST_sim_{uuid.uuid4().hex[:8]}@test.com"
        session = requests.Session()
        
        # Register
        reg_response = session.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": unique_email, "name": "Simulation Test", "password": "SimPass123!"}
        )
        if reg_response.status_code != 200:
            pytest.skip(f"Registration failed: {reg_response.status_code}")
        
        demo_code = reg_response.json()["demo_code"]
        
        # Verify
        verify_response = session.post(
            f"{BASE_URL}/api/auth/verify",
            json={"email": unique_email, "code": demo_code}
        )
        if verify_response.status_code != 200:
            pytest.skip(f"Verification failed: {verify_response.status_code}")
        
        yield session
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/user/account", json={"confirm": "DELETE"})
    
    def test_simple_simulation_returns_timeline(self, auth_session):
        """POST /api/simulation/simple returns timeline"""
        response = auth_session.post(
            f"{BASE_URL}/api/simulation/simple",
            json={
                "initial_investment": 5000,
                "monthly_contribution": 200,
                "years": 10,
                "expected_return": 0.07,
                "risk_level": "moderate"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "timeline" in data
        assert "summary" in data
        assert isinstance(data["timeline"], list)
        assert len(data["timeline"]) > 0
        
        # Verify timeline structure
        first_point = data["timeline"][0]
        assert "month" in first_point
        assert "year" in first_point
        assert "balance" in first_point
        
        print(f"Simple simulation: final_balance={data['summary']['final_balance']}")
    
    def test_monte_carlo_returns_percentile_timeline(self, auth_session):
        """POST /api/simulation/monte-carlo returns percentile_timeline"""
        response = auth_session.post(
            f"{BASE_URL}/api/simulation/monte-carlo",
            json={
                "initial_investment": 5000,
                "monthly_contribution": 200,
                "years": 10,
                "expected_return": 0.07,
                "volatility": 0.15,
                "simulations": 100  # Smaller for faster test
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Uses _run_monte_carlo_finals and _run_monte_carlo_paths helpers
        assert "percentile_timeline" in data
        assert "summary" in data
        assert isinstance(data["percentile_timeline"], list)
        assert len(data["percentile_timeline"]) > 0
        
        # Verify percentile timeline structure
        first_point = data["percentile_timeline"][0]
        assert "p10" in first_point
        assert "p25" in first_point
        assert "p50" in first_point
        assert "p75" in first_point
        assert "p90" in first_point
        
        # Verify summary
        summary = data["summary"]
        assert "simulations_run" in summary
        assert "probability_of_profit" in summary
        assert "median" in summary
        
        print(f"Monte Carlo: median={summary['median']}, prob_profit={summary['probability_of_profit']}%")


class TestHealthAndBasics:
    """Basic health check tests"""
    
    def test_health_endpoint(self):
        """GET /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"Health check: {data}")
    
    def test_root_endpoint(self):
        """GET /api/ returns API info"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "Flowly" in data.get("message", "")
        print(f"Root endpoint: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
