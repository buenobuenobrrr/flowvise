"""
Test Suite for SVI Risk Engine - Iteration 10
Tests the new Spending Volatility Index (SVI) risk engine features:
- SVI calculation (svi object with svi score, essential_monthly, variable_monthly, months_analyzed)
- Elastic Safety Buffer (buffer_months, buffer_amount, base_months, svi_adjustment)
- Spending Spike Detection (spike_detected, cooling_off, spike_pct)
- Smart Safe to Invest (raw_safe_to_invest, displayed_safe_to_invest, shadow_buffer_pct, frozen)
- safe_to_invest equals displayed_safe_to_invest (80% of raw)
- effective_buffer >= elastic_buffer.buffer_amount
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Module-level session to avoid rate limiting
_auth_session = None

def get_auth_session():
    """Get or create authenticated session (singleton to avoid rate limiting)"""
    global _auth_session
    if _auth_session is None:
        _auth_session = requests.Session()
        login_resp = _auth_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@example.com",
            "password": "Test123!"
        })
        if login_resp.status_code != 200:
            raise Exception(f"Login failed: {login_resp.text}")
    return _auth_session


class TestSVIRiskEngine:
    """Test the new SVI Risk Engine in investment-readiness endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get authenticated session"""
        self.session = get_auth_session()
    
    def test_investment_readiness_returns_svi_object(self):
        """Test that investment-readiness returns svi object with required fields"""
        resp = self.session.get(f"{BASE_URL}/api/analysis/investment-readiness")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Check svi object exists
        assert "svi" in data, "Missing 'svi' object in response"
        svi = data["svi"]
        
        # Check required fields in svi object
        assert "svi" in svi, "Missing 'svi' score in svi object"
        assert "essential_monthly" in svi, "Missing 'essential_monthly' in svi object"
        assert "variable_monthly" in svi, "Missing 'variable_monthly' in svi object"
        assert "months_analyzed" in svi, "Missing 'months_analyzed' in svi object"
        
        # Validate types
        assert isinstance(svi["svi"], (int, float)), "svi score should be numeric"
        assert isinstance(svi["essential_monthly"], (int, float)), "essential_monthly should be numeric"
        assert isinstance(svi["variable_monthly"], (int, float)), "variable_monthly should be numeric"
        assert isinstance(svi["months_analyzed"], int), "months_analyzed should be integer"
        
        print(f"SVI Object: svi={svi['svi']}, essential={svi['essential_monthly']}, variable={svi['variable_monthly']}, months={svi['months_analyzed']}")
    
    def test_investment_readiness_returns_elastic_buffer(self):
        """Test that investment-readiness returns elastic_buffer with required fields"""
        resp = self.session.get(f"{BASE_URL}/api/analysis/investment-readiness")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Check elastic_buffer object exists
        assert "elastic_buffer" in data, "Missing 'elastic_buffer' object in response"
        elastic = data["elastic_buffer"]
        
        # Check required fields
        assert "buffer_months" in elastic, "Missing 'buffer_months' in elastic_buffer"
        assert "buffer_amount" in elastic, "Missing 'buffer_amount' in elastic_buffer"
        assert "base_months" in elastic, "Missing 'base_months' in elastic_buffer"
        assert "svi_adjustment" in elastic, "Missing 'svi_adjustment' in elastic_buffer"
        
        # Validate types and values
        assert isinstance(elastic["buffer_months"], (int, float)), "buffer_months should be numeric"
        assert isinstance(elastic["buffer_amount"], (int, float)), "buffer_amount should be numeric"
        assert elastic["base_months"] == 3.0, f"base_months should be 3.0, got {elastic['base_months']}"
        assert isinstance(elastic["svi_adjustment"], (int, float)), "svi_adjustment should be numeric"
        
        print(f"Elastic Buffer: months={elastic['buffer_months']}, amount={elastic['buffer_amount']}, base={elastic['base_months']}, svi_adj={elastic['svi_adjustment']}")
    
    def test_investment_readiness_returns_spike_detection(self):
        """Test that investment-readiness returns spike_detection with required fields"""
        resp = self.session.get(f"{BASE_URL}/api/analysis/investment-readiness")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Check spike_detection object exists
        assert "spike_detection" in data, "Missing 'spike_detection' object in response"
        spike = data["spike_detection"]
        
        # Check required fields
        assert "spike_detected" in spike, "Missing 'spike_detected' in spike_detection"
        assert "cooling_off" in spike, "Missing 'cooling_off' in spike_detection"
        assert "spike_pct" in spike, "Missing 'spike_pct' in spike_detection"
        
        # Validate types
        assert isinstance(spike["spike_detected"], bool), "spike_detected should be boolean"
        assert isinstance(spike["cooling_off"], bool), "cooling_off should be boolean"
        assert isinstance(spike["spike_pct"], (int, float)), "spike_pct should be numeric"
        
        print(f"Spike Detection: detected={spike['spike_detected']}, cooling_off={spike['cooling_off']}, pct={spike['spike_pct']}")
    
    def test_investment_readiness_returns_safe_to_invest_engine(self):
        """Test that investment-readiness returns safe_to_invest_engine with required fields"""
        resp = self.session.get(f"{BASE_URL}/api/analysis/investment-readiness")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Check safe_to_invest_engine object exists
        assert "safe_to_invest_engine" in data, "Missing 'safe_to_invest_engine' object in response"
        safe = data["safe_to_invest_engine"]
        
        # Check required fields
        assert "raw_safe_to_invest" in safe, "Missing 'raw_safe_to_invest' in safe_to_invest_engine"
        assert "displayed_safe_to_invest" in safe, "Missing 'displayed_safe_to_invest' in safe_to_invest_engine"
        assert "shadow_buffer_pct" in safe, "Missing 'shadow_buffer_pct' in safe_to_invest_engine"
        assert "frozen" in safe, "Missing 'frozen' in safe_to_invest_engine"
        
        # Validate types
        assert isinstance(safe["raw_safe_to_invest"], (int, float)), "raw_safe_to_invest should be numeric"
        assert isinstance(safe["displayed_safe_to_invest"], (int, float)), "displayed_safe_to_invest should be numeric"
        assert isinstance(safe["shadow_buffer_pct"], (int, float)), "shadow_buffer_pct should be numeric"
        assert isinstance(safe["frozen"], bool), "frozen should be boolean"
        
        # Validate shadow_buffer_pct is 0.8 (80%)
        assert safe["shadow_buffer_pct"] == 0.8, f"shadow_buffer_pct should be 0.8, got {safe['shadow_buffer_pct']}"
        
        print(f"Safe to Invest Engine: raw={safe['raw_safe_to_invest']}, displayed={safe['displayed_safe_to_invest']}, shadow_pct={safe['shadow_buffer_pct']}, frozen={safe['frozen']}")
    
    def test_safe_to_invest_equals_displayed(self):
        """Test that safe_to_invest field equals displayed_safe_to_invest (80% of raw)"""
        resp = self.session.get(f"{BASE_URL}/api/analysis/investment-readiness")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        safe_engine = data["safe_to_invest_engine"]
        safe_to_invest = data["safe_to_invest"]
        displayed = safe_engine["displayed_safe_to_invest"]
        
        # safe_to_invest should equal displayed_safe_to_invest
        assert safe_to_invest == displayed, f"safe_to_invest ({safe_to_invest}) should equal displayed_safe_to_invest ({displayed})"
        
        # If not frozen, displayed should be 80% of raw
        if not safe_engine["frozen"]:
            raw = safe_engine["raw_safe_to_invest"]
            expected_displayed = round(raw * 0.8, 2)
            # Allow small floating point tolerance
            assert abs(displayed - expected_displayed) < 0.1, f"displayed ({displayed}) should be ~80% of raw ({raw}), expected {expected_displayed}"
        
        print(f"safe_to_invest={safe_to_invest}, displayed_safe_to_invest={displayed}")
    
    def test_effective_buffer_gte_elastic_buffer(self):
        """Test that effective_buffer >= elastic_buffer.buffer_amount"""
        resp = self.session.get(f"{BASE_URL}/api/analysis/investment-readiness")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        effective = data["effective_buffer"]
        elastic_amount = data["elastic_buffer"]["buffer_amount"]
        
        assert effective >= elastic_amount, f"effective_buffer ({effective}) should be >= elastic_buffer.buffer_amount ({elastic_amount})"
        
        print(f"effective_buffer={effective}, elastic_buffer.buffer_amount={elastic_amount}")


class TestExistingEndpoints:
    """Test that existing endpoints still work after risk engine changes"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get authenticated session"""
        self.session = get_auth_session()
    
    def test_login_still_works(self):
        """Test login endpoint still works"""
        # Use existing session to verify login worked
        resp = self.session.get(f"{BASE_URL}/api/auth/me")
        assert resp.status_code == 200, f"Auth check failed: {resp.text}"
        data = resp.json()
        assert "user_id" in data, "Missing user_id"
        assert "email" in data, "Missing email"
        print("Login endpoint working (verified via /auth/me)")
    
    def test_spending_summary_still_works(self):
        """Test spending-summary endpoint still works"""
        resp = self.session.get(f"{BASE_URL}/api/analysis/spending-summary")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "by_category" in data, "Missing by_category"
        assert "by_month" in data, "Missing by_month"
        assert "total_spending" in data, "Missing total_spending"
        assert "average_monthly_spending" in data, "Missing average_monthly_spending"
        print(f"Spending summary: total={data['total_spending']}, avg_monthly={data['average_monthly_spending']}")
    
    def test_smart_alerts_still_works(self):
        """Test smart-alerts endpoint still works"""
        resp = self.session.get(f"{BASE_URL}/api/budgets/smart-alerts")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "alerts" in data, "Missing alerts"
        assert isinstance(data["alerts"], list), "alerts should be a list"
        print(f"Smart alerts: {len(data['alerts'])} alerts")
    
    def test_monte_carlo_still_works(self):
        """Test monte-carlo simulation endpoint still works"""
        resp = self.session.post(f"{BASE_URL}/api/simulation/monte-carlo", json={
            "initial_investment": 1000,
            "monthly_contribution": 100,
            "years": 5,
            "expected_return": 0.07,
            "volatility": 0.15
        })
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "percentile_timeline" in data, "Missing percentile_timeline"
        assert "summary" in data, "Missing summary"
        # final_values is now in summary
        summary = data["summary"]
        assert "median" in summary, "Missing median in summary"
        print(f"Monte Carlo: final_median={summary.get('median', 'N/A')}")
    
    def test_health_endpoint(self):
        """Test health endpoint"""
        resp = requests.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert data.get("status") == "healthy", f"Unexpected status: {data}"
        print("Health endpoint working")
    
    def test_auth_me_endpoint(self):
        """Test auth/me endpoint"""
        resp = self.session.get(f"{BASE_URL}/api/auth/me")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert "user_id" in data, "Missing user_id"
        assert "email" in data, "Missing email"
        print(f"Auth me: {data['email']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
