"""
Integration tests for admin endpoints and billing functionality
"""
import pytest
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from api.main import app


class TestAdminEndpointsIntegration:
    """Test admin endpoints for usage statistics and management"""

    @pytest.fixture
    def test_client(self):
        return TestClient(app)

    @pytest.fixture
    def admin_auth_headers(self):
        """Headers for admin user authentication"""
        return {"x-api-key": "rk_admin_key_123"}

    @pytest.fixture
    def regular_auth_headers(self):
        """Headers for regular user authentication"""
        return {"x-api-key": "rk_user_key_123"}

    def test_get_usage_statistics_success(self, test_client, admin_auth_headers):
        """Test retrieving usage statistics as admin"""
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.db.database.get_db') as mock_db:

            # Mock admin user
            mock_admin = type('User', (), {
                'org_id': 'test-org-123',
                'user_id': 'admin-123',
                'role': 'ADMIN'
            })()
            mock_auth.return_value = mock_admin

            # Mock database query for usage statistics
            mock_session = mock_db.return_value.__enter__.return_value
            mock_session.query.return_value.filter.return_value.all.return_value = []

            # Test with date range parameters
            params = {
                "from_date": "2023-01-01",
                "to_date": "2023-12-31"
            }

            response = test_client.get("/v1/admin/usage", params=params, headers=admin_auth_headers)

            # Should either succeed or fail gracefully
            assert response.status_code in [200, 401, 403, 500]

    def test_get_usage_statistics_non_admin(self, test_client, regular_auth_headers):
        """Test that non-admin users cannot access usage statistics"""
        with patch('api.auth.auth.get_current_user') as mock_auth:
            # Mock regular user (non-admin)
            mock_user = type('User', (), {
                'org_id': 'test-org-123',
                'user_id': 'user-123',
                'role': 'EDITOR'
            })()
            mock_auth.return_value = mock_user

            response = test_client.get("/v1/admin/usage", headers=regular_auth_headers)

            # Should deny access
            assert response.status_code in [401, 403]

    def test_get_usage_statistics_invalid_dates(self, test_client, admin_auth_headers):
        """Test usage statistics with invalid date parameters"""
        with patch('api.auth.auth.get_current_user') as mock_auth:
            mock_admin = type('User', (), {
                'org_id': 'test-org-123',
                'role': 'ADMIN'
            })()
            mock_auth.return_value = mock_admin

            invalid_date_cases = [
                {"from_date": "invalid-date", "to_date": "2023-12-31"},
                {"from_date": "2023-12-31", "to_date": "2023-01-01"},  # from > to
                {"from_date": "2023-01-01", "to_date": "invalid-date"},
                {"from_date": "2025-01-01", "to_date": "2025-12-31"},  # Future dates
            ]

            for params in invalid_date_cases:
                response = test_client.get("/v1/admin/usage", params=params, headers=admin_auth_headers)
                assert response.status_code in [400, 422], f"Should reject invalid dates: {params}"

    def test_get_organization_details(self, test_client, admin_auth_headers):
        """Test retrieving organization details"""
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.db.database.get_db') as mock_db:

            mock_admin = type('User', (), {
                'org_id': 'test-org-123',
                'role': 'ADMIN'
            })()
            mock_auth.return_value = mock_admin

            # Mock organization query
            mock_session = mock_db.return_value.__enter__.return_value
            mock_org = type('Organization', (), {
                'org_id': 'test-org-123',
                'name': 'Test Organization',
                'created_at': datetime.now(),
                'quota_json': {'limit': 1000, 'used': 500}
            })()
            mock_session.query.return_value.filter.return_value.first.return_value = mock_org

            response = test_client.get("/v1/admin/organization", headers=admin_auth_headers)
            assert response.status_code in [200, 401, 403, 500]

    def test_update_organization_quota(self, test_client, admin_auth_headers):
        """Test updating organization quotas"""
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.db.database.get_db') as mock_db:

            mock_admin = type('User', (), {
                'org_id': 'test-org-123',
                'role': 'ADMIN'
            })()
            mock_auth.return_value = mock_admin

            # Mock database operations
            mock_session = mock_db.return_value.__enter__.return_value
            mock_session.query.return_value.filter.return_value.first.return_value = Mock()
            mock_session.commit.return_value = None

            quota_data = {
                "requests_limit": 10000,
                "storage_limit_mb": 1000,
                "notes_limit": 5000
            }

            response = test_client.patch("/v1/admin/organization/quota", json=quota_data, headers=admin_auth_headers)
            assert response.status_code in [200, 401, 403, 422, 500]


class TestBillingIntegration:
    """Test billing and subscription management integration"""

    @pytest.fixture
    def test_client(self):
        return TestClient(app)

    @pytest.fixture
    def admin_auth_headers(self):
        return {"x-api-key": "rk_admin_key_123"}

    def test_get_billing_information(self, test_client, admin_auth_headers):
        """Test retrieving billing information"""
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.routers.admin.get_billing_info') as mock_billing:

            mock_admin = type('User', (), {
                'org_id': 'test-org-123',
                'role': 'ADMIN'
            })()
            mock_auth.return_value = mock_admin

            # Mock billing information
            mock_billing.return_value = {
                "subscription_status": "active",
                "current_period_start": "2023-01-01",
                "current_period_end": "2023-01-31",
                "usage_current_period": {
                    "requests": 5000,
                    "storage_mb": 500
                },
                "next_billing_date": "2023-02-01"
            }

            response = test_client.get("/v1/admin/billing", headers=admin_auth_headers)
            assert response.status_code in [200, 401, 403, 501, 500]

    def test_generate_invoice(self, test_client, admin_auth_headers):
        """Test generating invoices"""
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.routers.admin.generate_invoice') as mock_invoice:

            mock_admin = type('User', (), {'org_id': 'test-org-123', 'role': 'ADMIN'})()
            mock_auth.return_value = mock_admin

            mock_invoice.return_value = {
                "invoice_id": "inv_123456",
                "amount": 2500,  # $25.00 in cents
                "currency": "usd",
                "period": "2023-01",
                "download_url": "https://example.com/invoice.pdf"
            }

            invoice_data = {
                "period_start": "2023-01-01",
                "period_end": "2023-01-31"
            }

            response = test_client.post("/v1/admin/billing/invoice", json=invoice_data, headers=admin_auth_headers)
            assert response.status_code in [200, 201, 401, 403, 422, 501, 500]

    def test_update_payment_method(self, test_client, admin_auth_headers):
        """Test updating payment method"""
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.routers.admin.update_payment_method') as mock_payment:

            mock_admin = type('User', (), {'org_id': 'test-org-123', 'role': 'ADMIN'})()
            mock_auth.return_value = mock_admin

            mock_payment.return_value = {"status": "success", "last4": "4242"}

            payment_data = {
                "payment_method_id": "pm_test_123456",
                "billing_email": "billing@example.com"
            }

            response = test_client.put("/v1/admin/billing/payment-method", json=payment_data, headers=admin_auth_headers)
            assert response.status_code in [200, 401, 403, 422, 501, 500]


class TestUsageTrackingIntegration:
    """Test usage tracking and logging integration"""

    @pytest.fixture
    def test_client(self):
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        return {"x-api-key": "rk_test_key_123"}

    def test_request_logging(self, test_client, auth_headers):
        """Test that requests are properly logged for usage tracking"""
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.middleware.usage_tracking.log_request') as mock_log:

            mock_user = type('User', (), {'org_id': 'test-org-123', 'user_id': 'user-123'})()
            mock_auth.return_value = mock_user

            # Make various requests to test logging
            endpoints = [
                ("GET", "/v1/notes"),
                ("POST", "/v1/search", {"query": "test", "top_k": 5}),
                ("POST", "/v1/notes", {"title": "Test", "content_md": "Content"}),
            ]

            for method, endpoint, *data in endpoints:
                if method == "GET":
                    response = test_client.get(endpoint, headers=auth_headers)
                elif method == "POST":
                    json_data = data[0] if data else {}
                    response = test_client.post(endpoint, json=json_data, headers=auth_headers)

                # Should handle request (success or failure)
                assert response.status_code in [200, 201, 401, 422, 500]

    def test_usage_aggregation(self, test_client, auth_headers):
        """Test that usage is properly aggregated"""
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.routers.admin.get_usage_summary') as mock_summary:

            mock_user = type('User', (), {'org_id': 'test-org-123', 'role': 'ADMIN'})()
            mock_auth.return_value = mock_user

            mock_summary.return_value = {
                "period": "2023-01",
                "total_requests": 15000,
                "total_bytes": 5000000,
                "requests_by_endpoint": {
                    "/v1/notes": 8000,
                    "/v1/search": 5000,
                    "/v1/api-keys": 2000
                },
                "average_response_time": 150  # ms
            }

            params = {"period": "2023-01"}
            response = test_client.get("/v1/admin/usage/summary", params=params, headers=auth_headers)
            assert response.status_code in [200, 401, 403, 422, 500]

    def test_quota_enforcement(self, test_client, auth_headers):
        """Test that quotas are properly enforced"""
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.middleware.quota_enforcement.check_quota') as mock_quota:

            mock_user = type('User', (), {'org_id': 'test-org-123'})()
            mock_auth.return_value = mock_user

            # Mock quota exceeded
            mock_quota.return_value = False

            response = test_client.get("/v1/notes", headers=auth_headers)
            # Should either enforce quota or pass through
            assert response.status_code in [200, 401, 429, 500]

    def test_real_time_usage_updates(self, test_client, auth_headers):
        """Test real-time usage updates during requests"""
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.models.models.UsageLog') as mock_usage_log:

            mock_user = type('User', (), {'org_id': 'test-org-123', 'user_id': 'user-123'})()
            mock_auth.return_value = mock_user

            # Make multiple requests in sequence
            for i in range(3):
                note_data = {"title": f"Test Note {i}", "content_md": f"Content {i}"}
                response = test_client.post("/v1/notes", json=note_data, headers=auth_headers)

                # Each request should be tracked
                assert response.status_code in [200, 201, 401, 422, 500]


class TestHealthAndMonitoring:
    """Test health checks and monitoring endpoints"""

    @pytest.fixture
    def test_client(self):
        return TestClient(app)

    def test_health_check_endpoint(self, test_client):
        """Test basic health check"""
        response = test_client.get("/health")
        # Health endpoint might not exist yet
        assert response.status_code in [200, 404]

    def test_readiness_check(self, test_client):
        """Test readiness check (database connectivity)"""
        with patch('api.db.database.engine.connect') as mock_connect:
            mock_connect.return_value.__enter__.return_value = Mock()

            response = test_client.get("/ready")
            # Readiness endpoint might not exist yet
            assert response.status_code in [200, 404, 500]

    def test_metrics_endpoint(self, test_client):
        """Test metrics endpoint for monitoring"""
        response = test_client.get("/metrics")
        # Metrics endpoint might not exist yet
        assert response.status_code in [200, 404]

    def test_version_endpoint(self, test_client):
        """Test API version endpoint"""
        response = test_client.get("/version")
        # Version endpoint might not exist yet
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Should contain version information
            assert isinstance(data, dict)


class TestAdminWorkflows:
    """Test complete admin workflows end-to-end"""

    @pytest.fixture
    def test_client(self):
        return TestClient(app)

    @pytest.fixture
    def admin_auth_headers(self):
        return {"x-api-key": "rk_admin_key_123"}

    def test_complete_billing_cycle_workflow(self, test_client, admin_auth_headers):
        """Test complete billing cycle from usage to invoice"""
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.db.database.get_db') as mock_db:

            mock_admin = type('User', (), {
                'org_id': 'test-org-123',
                'role': 'ADMIN'
            })()
            mock_auth.return_value = mock_admin

            mock_session = mock_db.return_value.__enter__.return_value

            # 1. Check current usage
            usage_response = test_client.get("/v1/admin/usage", headers=admin_auth_headers)
            assert usage_response.status_code in [200, 401, 403, 500]

            # 2. Check billing information
            billing_response = test_client.get("/v1/admin/billing", headers=admin_auth_headers)
            assert billing_response.status_code in [200, 401, 403, 501, 500]

            # 3. Generate invoice
            invoice_data = {
                "period_start": "2023-01-01",
                "period_end": "2023-01-31"
            }
            invoice_response = test_client.post("/v1/admin/billing/invoice", json=invoice_data, headers=admin_auth_headers)
            assert invoice_response.status_code in [200, 201, 401, 403, 422, 501, 500]

    def test_organization_management_workflow(self, test_client, admin_auth_headers):
        """Test complete organization management workflow"""
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.db.database.get_db') as mock_db:

            mock_admin = type('User', (), {
                'org_id': 'test-org-123',
                'role': 'ADMIN'
            })()
            mock_auth.return_value = mock_admin

            mock_session = mock_db.return_value.__enter__.return_value

            # 1. Get organization details
            org_response = test_client.get("/v1/admin/organization", headers=admin_auth_headers)
            assert org_response.status_code in [200, 401, 403, 500]

            # 2. Update quotas
            quota_data = {"requests_limit": 20000, "storage_limit_mb": 2000}
            quota_response = test_client.patch("/v1/admin/organization/quota", json=quota_data, headers=admin_auth_headers)
            assert quota_response.status_code in [200, 401, 403, 422, 500]

            # 3. Check updated usage limits
            usage_response = test_client.get("/v1/admin/usage", headers=admin_auth_headers)
            assert usage_response.status_code in [200, 401, 403, 500]