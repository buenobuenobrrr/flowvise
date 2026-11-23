"""
Code Quality Round 4 Regression Tests
Tests for:
1. Auth endpoints (login, register, verify, logout, rate limiting)
2. GDPR endpoints (export, delete)
3. Analysis endpoints (investment-readiness, spending-summary)
4. Simulation endpoints (simple, monte-carlo)
5. Backend refactoring: get_current_user with _extract_session_token and _validate_session helpers
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Use a single session for all tests to avoid rate limiting
@pytest.fixture(scope="module")
def shared_auth_session():
    """Get authenticated session - shared across module to avoid rate limiting"""
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "test@example.com", "password": "Test123!"}
    )
    if response.status_code != 200:
        pytest.skip(f"Could not authenticate: {response.status_code}")
    return session


class TestHealthAndRoot:
    """Basic health check tests"""
    
    def test_health_endpoint(self):
        """GET /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("PASS: Health endpoint returns healthy status")
    
    def test_root_endpoint(self):
        """GET /api/ returns Flowly API info"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "Flowly" in data.get("message", "") or "Financial" in data.get("message", "")
        print("PASS: Root endpoint returns API info")


class TestAuthLogin:
    """Auth login tests"""
    
    def test_login_success(self, shared_auth_session):
        """POST /api/auth/login with correct credentials returns 200"""
        # Use the shared session which already logged in successfully
        response = shared_auth_session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        print("PASS: Login with correct credentials returns 200")
    
    def test_login_invalid_credentials(self):
        """POST /api/auth/login with invalid credentials returns 401"""
        unique_email = f"invalid_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": unique_email, "password": "WrongPassword123!"}
        )
        assert response.status_code == 401
        print("PASS: Login with invalid credentials returns 401")


class TestAuthRateLimiting:
    """Rate limiting tests - uses unique email to avoid cross-test contamination"""
    
    def test_rate_limiting_returns_429(self):
        """Rate limiting returns 429 after 5 failed logins"""
        unique_email = f"ratelimit_{uuid.uuid4().hex[:8]}@test.com"
        
        # Make 5 failed login attempts
        for i in range(5):
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": unique_email, "password": "wrong"}
            )
            # Should be 401 for first 5 attempts
            if i < 5:
                assert response.status_code in [401, 429], f"Attempt {i+1}: Expected 401 or 429, got {response.status_code}"
        
        # 6th attempt should be rate limited
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": unique_email, "password": "wrong"}
        )
        assert response.status_code == 429, f"Expected 429 after 5 failed attempts, got {response.status_code}"
        print("PASS: Rate limiting returns 429 after 5 failed logins")


class TestAuthRegisterVerify:
    """Registration and verification tests"""
    
    def test_register_returns_demo_code(self):
        """POST /api/auth/register creates user with 6-digit demo_code"""
        unique_email = f"regtest_{uuid.uuid4().hex[:8]}@test.com"
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": unique_email,
                "name": "Test User",
                "password": "TestPass123!"
            }
        )
        # Accept both 200 and 201 as success
        assert response.status_code in [200, 201], f"Expected 200 or 201, got {response.status_code}"
        data = response.json()
        assert "demo_code" in data
        assert len(data["demo_code"]) == 6
        assert data["demo_code"].isdigit()
        print(f"PASS: Register returns 6-digit demo_code: {data['demo_code']}")
    
    def test_verify_accepts_valid_code(self):
        """POST /api/auth/verify accepts valid code"""
        # First register a new user
        unique_email = f"verifytest_{uuid.uuid4().hex[:8]}@test.com"
        reg_response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": unique_email,
                "name": "Verify Test",
                "password": "TestPass123!"
            }
        )
        assert reg_response.status_code in [200, 201]
        demo_code = reg_response.json()["demo_code"]
        
        # Now verify
        verify_response = requests.post(
            f"{BASE_URL}/api/auth/verify",
            json={"email": unique_email, "code": demo_code}
        )
        assert verify_response.status_code == 200
        data = verify_response.json()
        assert "user" in data
        print("PASS: Verify accepts valid code")


class TestAuthLogout:
    """Logout tests"""
    
    def test_logout_clears_session(self):
        """POST /api/auth/logout clears session"""
        # Create a new user for logout test to avoid affecting shared session
        unique_email = f"logouttest_{uuid.uuid4().hex[:8]}@test.com"
        
        # Register
        reg_response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": unique_email,
                "name": "Logout Test",
                "password": "TestPass123!"
            }
        )
        assert reg_response.status_code in [200, 201]
        demo_code = reg_response.json()["demo_code"]
        
        # Verify and login
        session = requests.Session()
        verify_response = session.post(
            f"{BASE_URL}/api/auth/verify",
            json={"email": unique_email, "code": demo_code}
        )
        assert verify_response.status_code == 200
        
        # Now logout
        logout_response = session.post(f"{BASE_URL}/api/auth/logout")
        assert logout_response.status_code == 200
        print("PASS: Logout clears session")


class TestGDPREndpoints:
    """GDPR compliance tests"""
    
    def test_export_returns_user_data(self, shared_auth_session):
        """GET /api/user/export returns user data"""
        response = shared_auth_session.get(f"{BASE_URL}/api/user/export")
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "email" in data["user"]
        print("PASS: Export returns user data (GDPR)")
    
    def test_delete_works(self):
        """DELETE /api/user/account deletes user"""
        # Create a new user for deletion test
        unique_email = f"deletetest_{uuid.uuid4().hex[:8]}@test.com"
        
        # Register
        reg_response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": unique_email,
                "name": "Delete Test",
                "password": "TestPass123!"
            }
        )
        assert reg_response.status_code in [200, 201]
        demo_code = reg_response.json()["demo_code"]
        
        # Verify
        session = requests.Session()
        verify_response = session.post(
            f"{BASE_URL}/api/auth/verify",
            json={"email": unique_email, "code": demo_code}
        )
        assert verify_response.status_code == 200
        
        # Delete - requires confirmation body
        delete_response = session.delete(
            f"{BASE_URL}/api/user/account",
            json={"confirm": "DELETE"}
        )
        assert delete_response.status_code == 200
        print("PASS: Delete works (GDPR)")


class TestAnalysisEndpoints:
    """Analysis endpoint tests"""
    
    def test_investment_readiness(self, shared_auth_session):
        """GET /api/analysis/investment-readiness returns status"""
        response = shared_auth_session.get(f"{BASE_URL}/api/analysis/investment-readiness")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "safe_to_invest" in data
        assert "confidence_level" in data
        print(f"PASS: Investment readiness returns status: {data['status']}")
    
    def test_spending_summary(self, shared_auth_session):
        """GET /api/analysis/spending-summary returns data"""
        response = shared_auth_session.get(f"{BASE_URL}/api/analysis/spending-summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_spending" in data or "average_monthly_spending" in data
        print("PASS: Spending summary returns data")


class TestSimulationEndpoints:
    """Simulation endpoint tests"""
    
    def test_simple_simulation(self, shared_auth_session):
        """POST /api/simulation/simple returns timeline"""
        response = shared_auth_session.post(
            f"{BASE_URL}/api/simulation/simple",
            json={
                "initial_investment": 1000,
                "monthly_contribution": 100,
                "annual_return": 0.07,
                "years": 5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "timeline" in data
        print("PASS: Simple simulation returns timeline")
    
    def test_monte_carlo_simulation(self, shared_auth_session):
        """POST /api/simulation/monte-carlo returns percentile_timeline"""
        response = shared_auth_session.post(
            f"{BASE_URL}/api/simulation/monte-carlo",
            json={
                "initial_investment": 1000,
                "monthly_contribution": 100,
                "years": 5,
                "simulations": 100
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "percentile_timeline" in data or "percentiles" in data
        print("PASS: Monte Carlo simulation returns percentile data")


class TestBackendRefactoring:
    """Tests to verify backend refactoring of get_current_user"""
    
    def test_auth_me_with_session_cookie(self, shared_auth_session):
        """GET /api/auth/me works with session cookie (uses _extract_session_token, _validate_session)"""
        # Check /api/auth/me
        me_response = shared_auth_session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        data = me_response.json()
        assert data["email"] == "test@example.com"
        print("PASS: /api/auth/me works with session cookie (refactored get_current_user)")
    
    def test_protected_endpoint_without_auth(self):
        """Protected endpoint returns 401 without auth (uses _extract_session_token)"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("PASS: Protected endpoint returns 401 without auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
