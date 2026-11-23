"""
Test suite for new Flowly features:
1. Rate Limiting on auth endpoints
2. GDPR data export and account deletion
3. Auto-detect income and subscriptions
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://127.0.0.1:8000').rstrip('/')

# Test credentials — sourced from environment or defaults for CI
TEST_EMAIL = os.environ.get('TEST_EMAIL', 'test@example.com')
TEST_PASSWORD = os.environ.get('TEST_PASSWORD', 'Test123!')


class TestRateLimiting:
    """Rate limiting tests for auth endpoints"""
    
    def test_login_rate_limit_after_5_failed_attempts(self):
        """POST /api/auth/login should return 429 after 5 failed attempts"""
        # Use unique email to avoid cross-test contamination
        unique_email = f"ratelimit_login_{uuid.uuid4().hex[:8]}@test.com"
        
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Make 5 failed login attempts
        for i in range(5):
            response = session.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": unique_email, "password": "wrongpassword"}
            )
            # Should get 401 for invalid credentials
            assert response.status_code == 401, f"Attempt {i+1}: Expected 401, got {response.status_code}"
            print(f"Login attempt {i+1}: Status {response.status_code}")
        
        # 6th attempt should be rate limited (429)
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": unique_email, "password": "wrongpassword"}
        )
        assert response.status_code == 429, f"Expected 429 after 5 attempts, got {response.status_code}"
        assert "Too many attempts" in response.json().get("detail", "")
        print(f"Rate limit triggered on attempt 6: Status {response.status_code}")
    
    def test_verify_rate_limit_after_5_attempts(self):
        """POST /api/auth/verify should return 429 after 5 attempts"""
        unique_email = f"ratelimit_verify_{uuid.uuid4().hex[:8]}@test.com"
        
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Make 5 verification attempts with wrong code
        for i in range(5):
            response = session.post(
                f"{BASE_URL}/api/auth/verify",
                json={"email": unique_email, "code": "000000"}
            )
            # Should get 400 for invalid code
            assert response.status_code == 400, f"Attempt {i+1}: Expected 400, got {response.status_code}"
            print(f"Verify attempt {i+1}: Status {response.status_code}")
        
        # 6th attempt should be rate limited (429)
        response = session.post(
            f"{BASE_URL}/api/auth/verify",
            json={"email": unique_email, "code": "000000"}
        )
        assert response.status_code == 429, f"Expected 429 after 5 attempts, got {response.status_code}"
        print(f"Rate limit triggered on attempt 6: Status {response.status_code}")
    
    def test_forgot_password_rate_limit_after_3_attempts(self):
        """POST /api/auth/forgot-password should return 429 after 3 attempts"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Make 3 forgot-password attempts
        for i in range(3):
            response = session.post(
                f"{BASE_URL}/api/auth/forgot-password",
                json={"email": f"forgot_{uuid.uuid4().hex[:8]}@test.com"}
            )
            # Should get 200 (doesn't reveal if email exists)
            assert response.status_code == 200, f"Attempt {i+1}: Expected 200, got {response.status_code}"
            print(f"Forgot-password attempt {i+1}: Status {response.status_code}")
        
        # 4th attempt should be rate limited (429)
        response = session.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": f"forgot_{uuid.uuid4().hex[:8]}@test.com"}
        )
        assert response.status_code == 429, f"Expected 429 after 3 attempts, got {response.status_code}"
        print(f"Rate limit triggered on attempt 4: Status {response.status_code}")
    
    def test_reset_password_rate_limit_after_5_attempts(self):
        """POST /api/auth/reset-password should return 429 after 5 attempts"""
        unique_email = f"ratelimit_reset_{uuid.uuid4().hex[:8]}@test.com"
        
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Make 5 reset-password attempts with wrong code
        for i in range(5):
            response = session.post(
                f"{BASE_URL}/api/auth/reset-password",
                json={"email": unique_email, "code": "000000", "new_password": "NewPass123!"}
            )
            # Should get 400 for invalid code
            assert response.status_code == 400, f"Attempt {i+1}: Expected 400, got {response.status_code}"
            print(f"Reset-password attempt {i+1}: Status {response.status_code}")
        
        # 6th attempt should be rate limited (429)
        response = session.post(
            f"{BASE_URL}/api/auth/reset-password",
            json={"email": unique_email, "code": "000000", "new_password": "NewPass123!"}
        )
        assert response.status_code == 429, f"Expected 429 after 5 attempts, got {response.status_code}"
        print(f"Rate limit triggered on attempt 6: Status {response.status_code}")


class TestGDPR:
    """GDPR data export and account deletion tests"""
    
    @pytest.fixture
    def auth_session(self):
        """Create authenticated session with test user"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login with test credentials
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        if response.status_code == 200:
            # Store token in cookie jar (httpOnly cookie)
            return session
        elif response.status_code == 403:
            # Email not verified - skip test
            pytest.skip("Test user email not verified")
        else:
            pytest.skip(f"Could not authenticate: {response.status_code}")
    
    def test_export_user_data_requires_auth(self):
        """GET /api/user/export should return 401 without auth"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/user/export")
        assert response.status_code == 401
        print(f"Export without auth: Status {response.status_code}")
    
    def test_export_user_data_returns_json(self, auth_session):
        """GET /api/user/export should return all user data as JSON"""
        response = auth_session.get(f"{BASE_URL}/api/user/export")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify structure
        assert "export_date" in data
        assert "user" in data
        assert "financial_profile" in data
        assert "transactions" in data
        assert "bank_accounts" in data
        assert "budgets" in data
        
        # Verify user data doesn't contain password_hash
        assert "password_hash" not in data.get("user", {})
        
        print(f"Export data keys: {list(data.keys())}")
        print(f"User data: {data.get('user', {}).get('email')}")
    
    def test_delete_account_requires_confirmation(self, auth_session):
        """DELETE /api/user/account with wrong confirmation should return 400"""
        response = auth_session.delete(
            f"{BASE_URL}/api/user/account",
            json={"confirm": "WRONG"}
        )
        assert response.status_code == 400
        assert "DELETE" in response.json().get("detail", "")
        print(f"Delete without proper confirmation: Status {response.status_code}")
    
    def test_delete_account_requires_auth(self):
        """DELETE /api/user/account should return 401 without auth"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        response = session.delete(
            f"{BASE_URL}/api/user/account",
            json={"confirm": "DELETE"}
        )
        assert response.status_code == 401
        print(f"Delete without auth: Status {response.status_code}")
    
    def test_delete_account_with_new_user(self):
        """DELETE /api/user/account with correct confirmation should delete user"""
        # Create a NEW user specifically for deletion test
        unique_email = f"TEST_delete_{uuid.uuid4().hex[:8]}@test.com"
        
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Register new user
        register_response = session.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": unique_email, "name": "Delete Test User", "password": "DeleteMe123!"}
        )
        assert register_response.status_code == 200, f"Registration failed: {register_response.status_code}"
        
        # Get verification code from response (demo mode)
        demo_code = register_response.json().get("demo_code")
        assert demo_code, "No demo code returned"
        
        # Verify email
        verify_response = session.post(
            f"{BASE_URL}/api/auth/verify",
            json={"email": unique_email, "code": demo_code}
        )
        assert verify_response.status_code == 200, f"Verification failed: {verify_response.status_code}"
        
        # Now delete the account
        delete_response = session.delete(
            f"{BASE_URL}/api/user/account",
            json={"confirm": "DELETE"}
        )
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.status_code}"
        assert "deleted" in delete_response.json().get("message", "").lower()
        
        # Verify user can no longer access protected endpoints
        me_response = session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 401, "User should not be able to access /me after deletion"
        
        print(f"Account deletion successful for {unique_email}")


class TestAutoDetect:
    """Auto-detect income and subscriptions tests"""
    
    @pytest.fixture
    def auth_session(self):
        """Create authenticated session with test user"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login with test credentials
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        if response.status_code == 200:
            return session
        elif response.status_code == 403:
            pytest.skip("Test user email not verified")
        else:
            pytest.skip(f"Could not authenticate: {response.status_code}")
    
    def test_auto_detect_requires_auth(self):
        """GET /api/analysis/auto-detect should return 401 without auth"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/analysis/auto-detect")
        assert response.status_code == 401
        print(f"Auto-detect without auth: Status {response.status_code}")
    
    def test_auto_detect_returns_structure(self, auth_session):
        """GET /api/analysis/auto-detect should return detected patterns"""
        response = auth_session.get(f"{BASE_URL}/api/analysis/auto-detect")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify structure
        assert "detected_income" in data
        assert "detected_subscriptions" in data
        assert isinstance(data["detected_income"], list)
        assert isinstance(data["detected_subscriptions"], list)
        
        # May have estimated values or message about needing more transactions
        if "estimated_monthly_income" in data:
            assert isinstance(data["estimated_monthly_income"], (int, float))
        if "estimated_monthly_subscriptions" in data:
            assert isinstance(data["estimated_monthly_subscriptions"], (int, float))
        
        print(f"Auto-detect response: {data}")
    
    def test_auto_detect_apply_requires_auth(self):
        """POST /api/analysis/auto-detect/apply should return 401 without auth"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        response = session.post(
            f"{BASE_URL}/api/analysis/auto-detect/apply",
            json={"income": 5000}
        )
        assert response.status_code == 401
        print(f"Auto-detect apply without auth: Status {response.status_code}")
    
    def test_auto_detect_apply_updates_profile(self, auth_session):
        """POST /api/analysis/auto-detect/apply should update financial profile"""
        # Get current profile
        profile_before = auth_session.get(f"{BASE_URL}/api/financial-profile").json()
        original_income = profile_before.get("income", 0)
        
        # Apply auto-detected values
        test_income = 7500.50
        test_subs = {"Netflix": 15.99, "Spotify": 9.99}
        
        response = auth_session.post(
            f"{BASE_URL}/api/analysis/auto-detect/apply",
            json={
                "income": test_income,
                "subscriptions": test_subs,
                "fixed_costs": 500
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("income") == test_income
        assert data.get("subscriptions") == test_subs
        assert data.get("fixed_costs") == 500
        
        # Restore original income
        auth_session.put(
            f"{BASE_URL}/api/financial-profile",
            json={"income": original_income, "subscriptions": {}, "fixed_costs": 0}
        )
        
        print(f"Auto-detect apply successful: income={test_income}, subs={test_subs}")


class TestHealthAndBasics:
    """Basic health check tests"""
    
    def test_health_endpoint(self):
        """GET /api/health should return healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"Health check: {data}")
    
    def test_root_endpoint(self):
        """GET /api/ should return API info"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "Flowly" in data.get("message", "")
        print(f"Root endpoint: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
