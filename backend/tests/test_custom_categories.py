"""
Test Custom Categories Feature - Iteration 10
Tests for:
- GET /api/categories - returns default (10) + custom categories
- POST /api/categories - creates custom category
- POST /api/categories - duplicate name returns 400
- POST /api/categories - empty name returns 400
- DELETE /api/categories/{name} - removes custom category
- DELETE /api/categories/{name} - nonexistent returns 404
- Custom categories persist across requests
- POST /api/transactions with custom category name works
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Default categories as defined in server.py
DEFAULT_CATEGORIES = [
    "Food & Dining", "Shopping", "Transportation", "Entertainment",
    "Bills & Utilities", "Healthcare", "Personal Care", "Education", "Travel", "Other"
]


@pytest.fixture(scope="module")
def auth_session():
    """Login and return authenticated session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login with test credentials
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "test@example.com",
        "password": "Test123!"
    })
    
    if response.status_code != 200:
        pytest.skip(f"Login failed: {response.status_code} - {response.text}")
    
    return session


@pytest.fixture(scope="module")
def unique_category_name():
    """Generate unique category name for testing"""
    return f"TEST_Cat_{uuid.uuid4().hex[:8]}"


class TestGetCategories:
    """Tests for GET /api/categories endpoint"""
    
    def test_get_categories_returns_defaults(self, auth_session):
        """GET /api/categories returns default categories"""
        response = auth_session.get(f"{BASE_URL}/api/categories")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "default" in data, "Response should contain 'default' key"
        assert "custom" in data, "Response should contain 'custom' key"
        assert "all" in data, "Response should contain 'all' key"
        
        # Verify all 10 default categories are present
        assert len(data["default"]) == 10, f"Expected 10 default categories, got {len(data['default'])}"
        for cat in DEFAULT_CATEGORIES:
            assert cat in data["default"], f"Default category '{cat}' missing"
        
        print(f"✓ GET /api/categories returns {len(data['default'])} defaults + {len(data['custom'])} custom")
    
    def test_get_categories_all_includes_defaults_and_custom(self, auth_session):
        """GET /api/categories 'all' field includes both defaults and custom"""
        response = auth_session.get(f"{BASE_URL}/api/categories")
        
        assert response.status_code == 200
        data = response.json()
        
        # 'all' should be defaults + custom
        expected_all = data["default"] + data["custom"]
        assert data["all"] == expected_all, "'all' should equal default + custom"
        
        print(f"✓ 'all' field correctly combines defaults ({len(data['default'])}) + custom ({len(data['custom'])})")


class TestCreateCategory:
    """Tests for POST /api/categories endpoint"""
    
    def test_create_custom_category_success(self, auth_session, unique_category_name):
        """POST /api/categories with valid name creates category"""
        response = auth_session.post(f"{BASE_URL}/api/categories", json={
            "name": unique_category_name
        })
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "name" in data, "Response should contain 'name'"
        assert data["name"] == unique_category_name, f"Expected name '{unique_category_name}', got '{data['name']}'"
        
        print(f"✓ Created custom category: {unique_category_name}")
    
    def test_create_duplicate_category_returns_400(self, auth_session, unique_category_name):
        """POST /api/categories with duplicate name returns 400"""
        # First ensure the category exists (may have been created in previous test)
        auth_session.post(f"{BASE_URL}/api/categories", json={"name": unique_category_name})
        
        # Try to create duplicate
        response = auth_session.post(f"{BASE_URL}/api/categories", json={
            "name": unique_category_name
        })
        
        assert response.status_code == 400, f"Expected 400 for duplicate, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Error response should contain 'detail'"
        assert "already exists" in data["detail"].lower(), f"Error should mention 'already exists': {data['detail']}"
        
        print(f"✓ Duplicate category correctly rejected with 400")
    
    def test_create_duplicate_default_category_returns_400(self, auth_session):
        """POST /api/categories with default category name returns 400"""
        response = auth_session.post(f"{BASE_URL}/api/categories", json={
            "name": "Food & Dining"  # This is a default category
        })
        
        assert response.status_code == 400, f"Expected 400 for default duplicate, got {response.status_code}"
        
        data = response.json()
        assert "already exists" in data["detail"].lower()
        
        print(f"✓ Default category duplicate correctly rejected")
    
    def test_create_empty_name_returns_400(self, auth_session):
        """POST /api/categories with empty name returns 400"""
        response = auth_session.post(f"{BASE_URL}/api/categories", json={
            "name": ""
        })
        
        assert response.status_code == 400, f"Expected 400 for empty name, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data
        
        print(f"✓ Empty category name correctly rejected with 400")
    
    def test_create_whitespace_only_name_returns_400(self, auth_session):
        """POST /api/categories with whitespace-only name returns 400"""
        response = auth_session.post(f"{BASE_URL}/api/categories", json={
            "name": "   "
        })
        
        assert response.status_code == 400, f"Expected 400 for whitespace name, got {response.status_code}"
        
        print(f"✓ Whitespace-only category name correctly rejected")
    
    def test_create_missing_name_returns_400(self, auth_session):
        """POST /api/categories without name field returns 400"""
        response = auth_session.post(f"{BASE_URL}/api/categories", json={})
        
        assert response.status_code == 400, f"Expected 400 for missing name, got {response.status_code}"
        
        print(f"✓ Missing name field correctly rejected")


class TestDeleteCategory:
    """Tests for DELETE /api/categories/{name} endpoint"""
    
    def test_delete_custom_category_success(self, auth_session):
        """DELETE /api/categories/{name} removes custom category"""
        # First create a category to delete
        cat_name = f"TEST_Delete_{uuid.uuid4().hex[:8]}"
        create_res = auth_session.post(f"{BASE_URL}/api/categories", json={"name": cat_name})
        assert create_res.status_code in [200, 201], f"Failed to create category for deletion test"
        
        # Delete it
        response = auth_session.delete(f"{BASE_URL}/api/categories/{cat_name}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify it's gone
        get_res = auth_session.get(f"{BASE_URL}/api/categories")
        data = get_res.json()
        assert cat_name not in data["custom"], f"Category '{cat_name}' should be removed"
        
        print(f"✓ Deleted custom category: {cat_name}")
    
    def test_delete_nonexistent_category_returns_404(self, auth_session):
        """DELETE /api/categories/{name} with nonexistent returns 404"""
        fake_name = f"NONEXISTENT_{uuid.uuid4().hex[:8]}"
        
        response = auth_session.delete(f"{BASE_URL}/api/categories/{fake_name}")
        
        assert response.status_code == 404, f"Expected 404 for nonexistent, got {response.status_code}"
        
        print(f"✓ Nonexistent category delete correctly returns 404")
    
    def test_delete_url_encoded_category(self, auth_session):
        """DELETE /api/categories/{name} works with URL-encoded names"""
        # Create category with special characters
        cat_name = f"TEST Cat & Special {uuid.uuid4().hex[:6]}"
        create_res = auth_session.post(f"{BASE_URL}/api/categories", json={"name": cat_name})
        
        if create_res.status_code in [200, 201]:
            # Delete with URL encoding
            import urllib.parse
            encoded_name = urllib.parse.quote(cat_name, safe='')
            response = auth_session.delete(f"{BASE_URL}/api/categories/{encoded_name}")
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            print(f"✓ URL-encoded category deletion works")
        else:
            print(f"⚠ Skipped URL encoding test - category creation failed")


class TestCategoryPersistence:
    """Tests for category persistence across requests"""
    
    def test_custom_categories_persist(self, auth_session):
        """Custom categories persist across multiple GET requests"""
        # Create a unique category
        cat_name = f"TEST_Persist_{uuid.uuid4().hex[:8]}"
        create_res = auth_session.post(f"{BASE_URL}/api/categories", json={"name": cat_name})
        assert create_res.status_code in [200, 201]
        
        # Verify it appears in multiple subsequent GET requests
        for i in range(3):
            get_res = auth_session.get(f"{BASE_URL}/api/categories")
            assert get_res.status_code == 200
            data = get_res.json()
            assert cat_name in data["custom"], f"Category should persist (request {i+1})"
            assert cat_name in data["all"], f"Category should be in 'all' (request {i+1})"
        
        # Cleanup
        auth_session.delete(f"{BASE_URL}/api/categories/{cat_name}")
        
        print(f"✓ Custom category persists across multiple requests")


class TestTransactionWithCustomCategory:
    """Tests for creating transactions with custom categories"""
    
    def test_create_transaction_with_custom_category(self, auth_session):
        """POST /api/transactions with custom category name works"""
        # Create a custom category
        cat_name = f"TEST_TxnCat_{uuid.uuid4().hex[:8]}"
        create_cat_res = auth_session.post(f"{BASE_URL}/api/categories", json={"name": cat_name})
        assert create_cat_res.status_code in [200, 201], "Failed to create custom category"
        
        # Create transaction with custom category
        txn_data = {
            "amount": 42.50,
            "category": cat_name,
            "description": "Test transaction with custom category",
            "date": "2026-01-15",
            "type": "expense"
        }
        
        response = auth_session.post(f"{BASE_URL}/api/transactions", json=txn_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "transaction_id" in data, "Response should contain transaction_id"
        
        # Verify transaction was created with correct category
        txn_id = data["transaction_id"]
        get_txns = auth_session.get(f"{BASE_URL}/api/transactions")
        assert get_txns.status_code == 200
        
        txns = get_txns.json()
        created_txn = next((t for t in txns if t["transaction_id"] == txn_id), None)
        assert created_txn is not None, "Created transaction should be retrievable"
        assert created_txn["category"] == cat_name, f"Transaction category should be '{cat_name}'"
        
        # Cleanup
        auth_session.delete(f"{BASE_URL}/api/transactions/{txn_id}")
        auth_session.delete(f"{BASE_URL}/api/categories/{cat_name}")
        
        print(f"✓ Transaction created with custom category: {cat_name}")


class TestCategoriesAuth:
    """Tests for authentication on category endpoints"""
    
    def test_get_categories_requires_auth(self):
        """GET /api/categories without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/categories")
        
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        
        print(f"✓ GET /api/categories requires authentication")
    
    def test_post_categories_requires_auth(self):
        """POST /api/categories without auth returns 401"""
        response = requests.post(f"{BASE_URL}/api/categories", json={"name": "Unauthorized"})
        
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        
        print(f"✓ POST /api/categories requires authentication")
    
    def test_delete_categories_requires_auth(self):
        """DELETE /api/categories/{name} without auth returns 401"""
        response = requests.delete(f"{BASE_URL}/api/categories/SomeCategory")
        
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        
        print(f"✓ DELETE /api/categories requires authentication")


# Cleanup fixture to remove test categories after all tests
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_categories(auth_session):
    """Cleanup TEST_ prefixed categories after tests"""
    yield
    
    # Get all categories and delete TEST_ prefixed ones
    try:
        response = auth_session.get(f"{BASE_URL}/api/categories")
        if response.status_code == 200:
            data = response.json()
            for cat in data.get("custom", []):
                if cat.startswith("TEST_"):
                    auth_session.delete(f"{BASE_URL}/api/categories/{cat}")
                    print(f"Cleaned up test category: {cat}")
    except Exception as e:
        print(f"Cleanup warning: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
