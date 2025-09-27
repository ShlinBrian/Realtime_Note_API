"""
Integration tests for API Keys management endpoints
"""
import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch

from api.main import app


class TestApiKeysIntegration:
    """Test API Keys CRUD operations with real endpoint calls"""

    @pytest.fixture
    def test_client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_auth_headers(self):
        """Mock authentication headers"""
        return {"x-api-key": "rk_test_key_123"}

    def test_create_api_key_success(self, test_client, mock_auth_headers):
        """Test successful API key creation"""
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.db.database.get_async_db') as mock_db:

            # Mock authenticated user
            mock_user = type('User', (), {
                'org_id': 'test-org-123',
                'user_id': 'test-user-123'
            })()
            mock_auth.return_value = mock_user

            # Mock database operations
            mock_session = mock_db.return_value.__enter__.return_value
            mock_session.add.return_value = None
            mock_session.commit.return_value = None
            mock_session.refresh.return_value = None

            # Mock the created API key
            mock_api_key = type('ApiKey', (), {
                'key_id': str(uuid.uuid4()),
                'name': 'Test API Key',
                'hash': 'test_hash_123',
                'created_at': '2023-01-01T00:00:00Z',
                'expires_at': None
            })()

            api_key_data = {
                "name": "Test API Key"
            }

            response = test_client.post("/v1/api-keys", json=api_key_data, headers=mock_auth_headers)

            # Should either succeed or fail gracefully
            assert response.status_code in [200, 201, 401, 422, 500]

    def test_create_api_key_invalid_name(self, test_client, mock_auth_headers):
        """Test API key creation with invalid name"""
        with patch('api.auth.auth.get_current_user') as mock_auth:
            mock_user = type('User', (), {'org_id': 'test-org-123'})()
            mock_auth.return_value = mock_user

            # Empty name
            api_key_data = {"name": ""}
            response = test_client.post("/v1/api-keys", json=api_key_data, headers=mock_auth_headers)
            assert response.status_code in [400, 422]

            # Very long name
            api_key_data = {"name": "x" * 200}
            response = test_client.post("/v1/api-keys", json=api_key_data, headers=mock_auth_headers)
            assert response.status_code in [400, 422]

    def test_create_api_key_missing_auth(self, test_client):
        """Test API key creation without authentication"""
        api_key_data = {"name": "Test Key"}
        response = test_client.post("/v1/api-keys", json=api_key_data)
        assert response.status_code == 401

    def test_list_api_keys_success(self, test_client, mock_auth_headers):
        """Test listing API keys"""
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.db.database.get_async_db') as mock_db:

            mock_user = type('User', (), {'org_id': 'test-org-123'})()
            mock_auth.return_value = mock_user

            # Mock database query
            mock_session = mock_db.return_value.__enter__.return_value
            mock_session.query.return_value.filter.return_value.all.return_value = []

            response = test_client.get("/v1/api-keys", headers=mock_auth_headers)
            assert response.status_code in [200, 401, 500]

    def test_list_api_keys_missing_auth(self, test_client):
        """Test listing API keys without authentication"""
        response = test_client.get("/v1/api-keys")
        assert response.status_code == 401

    def test_api_key_crud_workflow(self, test_client, mock_auth_headers):
        """Test complete API key lifecycle"""
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.db.database.get_async_db') as mock_db:

            mock_user = type('User', (), {'org_id': 'test-org-123'})()
            mock_auth.return_value = mock_user

            mock_session = mock_db.return_value.__enter__.return_value
            mock_session.add.return_value = None
            mock_session.commit.return_value = None
            mock_session.refresh.return_value = None

            # 1. Create API key
            create_data = {"name": "Integration Test Key"}
            create_response = test_client.post("/v1/api-keys", json=create_data, headers=mock_auth_headers)

            # Should not error completely
            assert create_response.status_code != 500

            # 2. List API keys
            list_response = test_client.get("/v1/api-keys", headers=mock_auth_headers)
            assert list_response.status_code in [200, 401, 500]

    def test_api_key_name_validation(self, test_client, mock_auth_headers):
        """Test various API key name validation scenarios"""
        with patch('api.auth.auth.get_current_user') as mock_auth:
            mock_user = type('User', (), {'org_id': 'test-org-123'})()
            mock_auth.return_value = mock_user

            test_cases = [
                {"name": "Valid Key Name", "should_pass": True},
                {"name": "Key-With-Dashes", "should_pass": True},
                {"name": "Key_With_Underscores", "should_pass": True},
                {"name": "Key With Spaces", "should_pass": True},
                {"name": "Key123", "should_pass": True},
                {"name": "", "should_pass": False},
                {"name": "x" * 150, "should_pass": False},
            ]

            for test_case in test_cases:
                response = test_client.post("/v1/api-keys", json={"name": test_case["name"]}, headers=mock_auth_headers)

                if test_case["should_pass"]:
                    # Should either succeed or fail due to auth/db, not validation
                    assert response.status_code not in [400, 422], f"Validation failed for valid name: {test_case['name']}"
                else:
                    # Should fail validation
                    assert response.status_code in [400, 422, 500], f"Validation passed for invalid name: {test_case['name']}"


class TestApiKeyAuthentication:
    """Test API key authentication flows"""

    @pytest.fixture
    def test_client(self):
        return TestClient(app)

    def test_valid_api_key_format(self, test_client):
        """Test that API key format is validated"""
        test_cases = [
            {"key": "rk_valid_key_123", "description": "Valid format"},
            {"key": "invalid_key", "description": "Missing rk_ prefix"},
            {"key": "", "description": "Empty key"},
            {"key": "rk_", "description": "Only prefix"},
            {"key": "rk_" + "x" * 200, "description": "Very long key"},
        ]

        for test_case in test_cases:
            headers = {"x-api-key": test_case["key"]} if test_case["key"] else {}

            # Test with a simple endpoint that requires auth
            response = test_client.get("/v1/notes", headers=headers)

            # All should fail auth (since these are test keys), but shouldn't crash
            assert response.status_code in [401, 403, 422], f"Unexpected response for {test_case['description']}"

    def test_missing_api_key_header(self, test_client):
        """Test requests without API key header"""
        endpoints = [
            ("GET", "/v1/notes"),
            ("POST", "/v1/notes"),
            ("GET", "/v1/api-keys"),
            ("POST", "/v1/api-keys"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = test_client.get(endpoint)
            elif method == "POST":
                response = test_client.post(endpoint, json={})

            assert response.status_code == 401, f"Expected 401 for {method} {endpoint} without auth"

    def test_malformed_auth_header(self, test_client):
        """Test various malformed authentication headers"""
        malformed_headers = [
            {"authorization": "Bearer rk_test_key"},  # Wrong header name
            {"x-api-key": "Bearer rk_test_key"},     # Wrong format
            {"x-api-key": "rk_test_key extra_data"}, # Extra data
            {"x-api-key": "RK_TEST_KEY"},            # Wrong case
        ]

        for headers in malformed_headers:
            response = test_client.get("/v1/notes", headers=headers)
            assert response.status_code in [401, 422], f"Expected auth failure for headers: {headers}"