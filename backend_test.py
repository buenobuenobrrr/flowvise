#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class MoneyBrainAPITester:
    def __init__(self, base_url="https://money-brain-ai.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()

    def run_test(self, name, method, endpoint, expected_status, data=None, auth_required=True):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if auth_required and self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=headers)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - {name}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 500:
                        print(f"   Response: {response_data}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ FAILED - {name}")
                print(f"   Expected status {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ FAILED - {name}")
            print(f"   Exception: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test API health"""
        return self.run_test("API Health Check", "GET", "health", 200, auth_required=False)

    def test_login(self, email="test@example.com", password="Test123!"):
        """Test login and get token"""
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password},
            auth_required=False
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   ✅ Token obtained: {self.token[:20]}...")
            return True
        return False

    def test_get_me(self):
        """Test get current user"""
        return self.run_test("Get Current User", "GET", "auth/me", 200)

    def test_investment_readiness(self):
        """Test investment readiness analysis"""
        success, response = self.run_test("Investment Readiness Analysis", "GET", "analysis/investment-readiness", 200)
        if success:
            # Check for default values as mentioned in requirements
            required_fields = ['status', 'confidence_level', 'safe_to_invest']
            for field in required_fields:
                if field not in response:
                    print(f"   ⚠️  Missing required field: {field}")
                    return False
            print(f"   ✅ Has default values - Status: {response.get('status')}, Confidence: {response.get('confidence_level')}")
        return success

    def test_simple_simulation(self):
        """Test simple portfolio simulation"""
        simulation_data = {
            "initial_investment": 1000,
            "monthly_contribution": 100,
            "years": 5,
            "expected_return": 0.07,
            "risk_level": "moderate"
        }
        success, response = self.run_test(
            "Simple Portfolio Simulation", 
            "POST", 
            "simulation/simple", 
            200, 
            data=simulation_data
        )
        if success:
            # Check for projection data
            if 'timeline' in response and 'summary' in response:
                print(f"   ✅ Projection returned - Final balance: {response['summary'].get('final_balance', 'N/A')}")
            else:
                print(f"   ⚠️  Missing timeline or summary in response")
                return False
        return success

    def test_monte_carlo_simulation(self):
        """Test Monte Carlo simulation"""
        monte_carlo_data = {
            "initial_investment": 1000,
            "monthly_contribution": 100,
            "years": 5,
            "expected_return": 0.07,
            "volatility": 0.15,
            "simulations": 100
        }
        success, response = self.run_test(
            "Monte Carlo Simulation", 
            "POST", 
            "simulation/monte-carlo", 
            200, 
            data=monte_carlo_data
        )
        if success:
            # Check for percentile data
            if 'percentile_timeline' in response and 'summary' in response:
                summary = response['summary']
                percentiles = ['p10', 'median', 'p90']
                has_percentiles = all(p in summary for p in percentiles)
                if has_percentiles:
                    print(f"   ✅ Percentile data returned - P10: {summary.get('p10')}, Median: {summary.get('median')}, P90: {summary.get('p90')}")
                else:
                    print(f"   ⚠️  Missing percentile data in summary")
                    return False
            else:
                print(f"   ⚠️  Missing percentile_timeline or summary in response")
                return False
        return success

    def test_budget_alerts(self):
        """Test budget alerts"""
        success, response = self.run_test("Budget Alerts", "GET", "budgets/alerts", 200)
        if success:
            # Check for threshold alerts structure
            if 'alerts' in response:
                print(f"   ✅ Alerts structure returned - {len(response['alerts'])} alerts")
            else:
                print(f"   ⚠️  Missing alerts in response")
                return False
        return success

    def test_spending_summary(self):
        """Test spending summary"""
        return self.run_test("Spending Summary", "GET", "analysis/spending-summary", 200)

    def test_financial_profile(self):
        """Test financial profile"""
        return self.run_test("Financial Profile", "GET", "financial-profile", 200)

    def test_investment_options(self):
        """Test investment options"""
        return self.run_test("Investment Options", "GET", "investments/options", 200)

def main():
    print("🚀 Starting Money Brain API Tests")
    print("=" * 50)
    
    tester = MoneyBrainAPITester()
    
    # Test sequence
    tests = [
        ("Health Check", tester.test_health_check),
        ("Login", tester.test_login),
        ("Get Current User", tester.test_get_me),
        ("Investment Readiness", tester.test_investment_readiness),
        ("Simple Simulation", tester.test_simple_simulation),
        ("Monte Carlo Simulation", tester.test_monte_carlo_simulation),
        ("Budget Alerts", tester.test_budget_alerts),
        ("Spending Summary", tester.test_spending_summary),
        ("Financial Profile", tester.test_financial_profile),
        ("Investment Options", tester.test_investment_options),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            if not success:
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ EXCEPTION in {test_name}: {str(e)}")
            failed_tests.append(test_name)
    
    # Print results
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print("=" * 50)
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Tests Failed: {len(failed_tests)}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "0%")
    
    if failed_tests:
        print(f"\n❌ Failed Tests: {', '.join(failed_tests)}")
        return 1
    else:
        print("\n✅ All tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())