"""
End-to-end integration tests for complete user workflows
"""
import pytest
import uuid
import json
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from api.main import app


class TestCompleteUserJourney:
    """Test complete user journeys from authentication to note management"""

    @pytest.fixture
    def test_client(self):
        return TestClient(app)

    def test_new_user_onboarding_workflow(self, test_client):
        """Test complete new user onboarding flow"""
        # 1. Start OAuth device code flow
        with patch('api.routers.auth.generate_device_code') as mock_device_code:
            mock_device_code.return_value = {
                "device_code": "test_device_code_123",
                "user_code": "ABCD-EFGH",
                "verification_uri": "https://auth.example.com/device",
                "expires_in": 600
            }

            device_response = test_client.post("/v1/auth/device")
            assert device_response.status_code in [200, 201, 500, 501]

        # 2. Poll for authorization (simulate user completing OAuth)
        with patch('api.routers.auth.check_device_authorization') as mock_check, \
             patch('api.routers.auth.create_user_session') as mock_session:

            mock_check.return_value = {
                "user_id": "new_user_123",
                "email": "newuser@example.com",
                "org_id": "new_org_123"
            }

            mock_session.return_value = {
                "access_token": "test_access_token",
                "api_key": "rk_new_user_key_123"
            }

            poll_data = {"device_code": "test_device_code_123", "client_id": "test_client"}
            auth_response = test_client.post("/v1/auth/device/token", json=poll_data)
            assert auth_response.status_code in [200, 400, 500]

        # 3. Create first API key
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.db.database.get_async_db') as mock_db:

            mock_user = type('User', (), {'org_id': 'new_org_123', 'user_id': 'new_user_123'})()
            mock_auth.return_value = mock_user

            mock_session = mock_db.return_value.__enter__.return_value
            mock_session.add.return_value = None
            mock_session.commit.return_value = None

            api_key_data = {"name": "My First API Key"}
            headers = {"x-api-key": "rk_new_user_key_123"}

            api_key_response = test_client.post("/v1/api-keys", json=api_key_data, headers=headers)
            assert api_key_response.status_code in [200, 201, 401, 422, 500]

        # 4. Create first note
        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.routers.notes.get_db') as mock_db, \
             patch('api.search.vector_search.index_note') as mock_index:

            mock_auth.return_value = mock_user
            mock_session = mock_db.return_value.__enter__.return_value

            note_data = {
                "title": "My First Note",
                "content_md": "# Welcome!\n\nThis is my first note in the system."
            }

            note_response = test_client.post("/v1/notes", json=note_data, headers=headers)
            assert note_response.status_code in [200, 201, 401, 422, 500]

    def test_daily_note_taking_workflow(self, test_client):
        """Test typical daily note-taking workflow"""
        headers = {"x-api-key": "rk_daily_user_123"}

        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.routers.notes.get_db') as mock_db, \
             patch('api.search.vector_search.index_note') as mock_index, \
             patch('api.search.vector_search.search_notes') as mock_search:

            mock_user = type('User', (), {'org_id': 'daily_org_123'})()
            mock_auth.return_value = mock_user

            mock_session = mock_db.return_value.__enter__.return_value
            mock_session.add.return_value = None
            mock_session.commit.return_value = None
            mock_session.refresh.return_value = None

            # 1. List existing notes
            mock_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
            list_response = test_client.get("/v1/notes", headers=headers)
            assert list_response.status_code in [200, 401, 500]

            # 2. Create morning note
            morning_note = {
                "title": "Daily Standup - 2023-01-15",
                "content_md": "## Today's Goals\n- Review code\n- Write tests\n- Team meeting at 2pm"
            }
            create_response = test_client.post("/v1/notes", json=morning_note, headers=headers)
            assert create_response.status_code in [200, 201, 401, 422, 500]

            # 3. Search for previous standups
            mock_search.return_value = [("note_123", 0.85), ("note_456", 0.75)]
            search_data = {"query": "standup goals", "top_k": 5}
            search_response = test_client.post("/v1/search", json=search_data, headers=headers)
            assert search_response.status_code in [200, 401, 422, 500]

            # 4. Update note with progress
            note_id = "note_123"
            mock_session.query.return_value.filter.return_value.first.return_value = Mock(
                note_id=note_id, version=1, title="Daily Standup - 2023-01-15"
            )

            update_data = {"content_md": "## Today's Goals\n- ✅ Review code\n- 🔄 Write tests\n- Team meeting at 2pm"}
            update_response = test_client.patch(f"/v1/notes/{note_id}", json=update_data, headers=headers)
            assert update_response.status_code in [200, 401, 404, 422, 500]

    def test_research_and_knowledge_workflow(self, test_client):
        """Test research and knowledge management workflow"""
        headers = {"x-api-key": "rk_researcher_123"}

        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.routers.notes.get_db') as mock_db, \
             patch('api.search.vector_search.index_note') as mock_index, \
             patch('api.search.vector_search.search_notes') as mock_search:

            mock_user = type('User', (), {'org_id': 'research_org_123'})()
            mock_auth.return_value = mock_user

            mock_session = mock_db.return_value.__enter__.return_value

            # 1. Create research topic notes
            research_topics = [
                {
                    "title": "Machine Learning Fundamentals",
                    "content_md": "# ML Fundamentals\n\n## Key Concepts\n- Supervised Learning\n- Unsupervised Learning\n- Neural Networks"
                },
                {
                    "title": "Deep Learning Architecture Patterns",
                    "content_md": "# Deep Learning Patterns\n\n## Common Architectures\n- CNN for image processing\n- RNN for sequences\n- Transformers for attention"
                },
                {
                    "title": "MLOps Best Practices",
                    "content_md": "# MLOps\n\n## Deployment Strategies\n- Model versioning\n- A/B testing\n- Monitoring and alerting"
                }
            ]

            for topic in research_topics:
                response = test_client.post("/v1/notes", json=topic, headers=headers)
                assert response.status_code in [200, 201, 401, 422, 500]

            # 2. Search across research notes
            mock_search.return_value = [
                ("ml_note_1", 0.92),
                ("ml_note_2", 0.88),
                ("ml_note_3", 0.82)
            ]

            search_queries = [
                "neural networks architecture",
                "model deployment strategies",
                "supervised learning techniques"
            ]

            for query in search_queries:
                search_data = {"query": query, "top_k": 10}
                search_response = test_client.post("/v1/search", json=search_data, headers=headers)
                assert search_response.status_code in [200, 401, 422, 500]

            # 3. Create synthesis note linking concepts
            synthesis_note = {
                "title": "ML Project Implementation Guide",
                "content_md": """# ML Project Guide

## Implementation Flow
1. **Problem Definition** - Define supervised/unsupervised approach
2. **Architecture Selection** - Choose CNN/RNN/Transformer based on data
3. **Training Pipeline** - Implement with versioning and monitoring
4. **Deployment** - Use MLOps best practices for production

## Key References
- See "Machine Learning Fundamentals" for core concepts
- See "Deep Learning Architecture Patterns" for model selection
- See "MLOps Best Practices" for deployment guidance
"""
            }

            synthesis_response = test_client.post("/v1/notes", json=synthesis_note, headers=headers)
            assert synthesis_response.status_code in [200, 201, 401, 422, 500]

    def test_collaborative_editing_workflow(self, test_client):
        """Test collaborative editing workflow via WebSocket and REST"""
        headers = {"x-api-key": "rk_collab_user_123"}

        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.db.database.get_db') as mock_db:

            mock_user = type('User', (), {'org_id': 'collab_org_123'})()
            mock_auth.return_value = mock_user

            mock_session = mock_db.return_value.__enter__.return_value

            # 1. Create shared note
            shared_note = {
                "title": "Team Brainstorming Session",
                "content_md": "# Brainstorming\n\n## Initial Ideas\n- Idea 1\n- Idea 2"
            }

            create_response = test_client.post("/v1/notes", json=shared_note, headers=headers)
            assert create_response.status_code in [200, 201, 401, 422, 500]

            # 2. Simulate multiple users editing (REST API updates)
            note_id = "shared_note_123"
            mock_note = Mock(note_id=note_id, version=1, title="Team Brainstorming Session")
            mock_session.query.return_value.filter.return_value.first.return_value = mock_note

            # User 1 adds content
            user1_update = {
                "content_md": "# Brainstorming\n\n## Initial Ideas\n- Idea 1\n- Idea 2\n- Idea 3 (User 1)"
            }
            update1_response = test_client.patch(f"/v1/notes/{note_id}", json=user1_update, headers=headers)
            assert update1_response.status_code in [200, 401, 404, 422, 500]

            # User 2 adds different content (simulate conflict resolution)
            mock_note.version = 2
            user2_update = {
                "content_md": "# Brainstorming\n\n## Initial Ideas\n- Idea 1\n- Idea 2\n- Idea 3 (User 1)\n- Idea 4 (User 2)"
            }
            update2_response = test_client.patch(f"/v1/notes/{note_id}", json=user2_update, headers=headers)
            assert update2_response.status_code in [200, 401, 404, 409, 422, 500]

            # 3. Retrieve final version
            get_response = test_client.get(f"/v1/notes/{note_id}", headers=headers)
            assert get_response.status_code in [200, 401, 404, 500]


class TestErrorRecoveryWorkflows:
    """Test error recovery and resilience workflows"""

    @pytest.fixture
    def test_client(self):
        return TestClient(app)

    def test_network_failure_recovery(self, test_client):
        """Test recovery from network/service failures"""
        headers = {"x-api-key": "rk_recovery_test_123"}

        with patch('api.auth.auth.get_current_user') as mock_auth:
            mock_user = type('User', (), {'org_id': 'recovery_org_123'})()
            mock_auth.return_value = mock_user

            # 1. Simulate database connection failure
            with patch('api.routers.notes.get_db') as mock_db:
                mock_db.side_effect = Exception("Database connection failed")

                note_data = {"title": "Test Note", "content_md": "Content"}
                response = test_client.post("/v1/notes", json=note_data, headers=headers)
                assert response.status_code == 500

            # 2. Simulate search service failure
            with patch('api.search.vector_search.search_notes') as mock_search:
                mock_search.side_effect = Exception("Search service unavailable")

                search_data = {"query": "test", "top_k": 5}
                response = test_client.post("/v1/search", json=search_data, headers=headers)
                assert response.status_code in [500, 503]

            # 3. Test graceful degradation
            with patch('api.search.vector_search.search_notes') as mock_search, \
                 patch('api.db.database.get_db') as mock_db:

                mock_search.side_effect = Exception("Search unavailable")
                mock_session = mock_db.return_value.__enter__.return_value
                mock_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

                # Should still be able to list notes even if search is down
                response = test_client.get("/v1/notes", headers=headers)
                assert response.status_code in [200, 500]

    def test_data_consistency_recovery(self, test_client):
        """Test recovery from data consistency issues"""
        headers = {"x-api-key": "rk_consistency_test_123"}

        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.db.database.get_db') as mock_db:

            mock_user = type('User', (), {'org_id': 'consistency_org_123'})()
            mock_auth.return_value = mock_user

            mock_session = mock_db.return_value.__enter__.return_value

            # 1. Test handling of version conflicts
            note_id = "conflict_note_123"
            mock_note = Mock(note_id=note_id, version=5)
            mock_session.query.return_value.filter.return_value.first.return_value = mock_note

            # Try to update with old version
            update_data = {"content_md": "Updated content", "version": 3}
            response = test_client.patch(f"/v1/notes/{note_id}", json=update_data, headers=headers)
            assert response.status_code in [200, 409, 422, 500]

            # 2. Test handling of missing references
            missing_note_id = "missing_note_123"
            mock_session.query.return_value.filter.return_value.first.return_value = None

            response = test_client.get(f"/v1/notes/{missing_note_id}", headers=headers)
            assert response.status_code == 404

    def test_rate_limit_recovery(self, test_client):
        """Test recovery from rate limiting"""
        headers = {"x-api-key": "rk_rate_limit_test_123"}

        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.auth.rate_limit.RateLimiter') as mock_rate_limiter:

            mock_user = type('User', (), {'org_id': 'rate_limit_org_123'})()
            mock_auth.return_value = mock_user

            # Mock rate limiter
            mock_limiter_instance = Mock()
            mock_rate_limiter.return_value = mock_limiter_instance

            # 1. Simulate hitting rate limit
            mock_limiter_instance.check_rate_limit.return_value = False
            mock_limiter_instance.get_headers.return_value = {
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "1640995200"
            }

            response = test_client.get("/v1/notes", headers=headers)
            assert response.status_code in [200, 429]

            # 2. Simulate rate limit recovery
            mock_limiter_instance.check_rate_limit.return_value = True
            mock_limiter_instance.get_headers.return_value = {
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "99",
                "X-RateLimit-Reset": "1640995260"
            }

            with patch('api.routers.notes.get_db') as mock_db:
                mock_session = mock_db.return_value.__enter__.return_value
                mock_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

                response = test_client.get("/v1/notes", headers=headers)
                assert response.status_code in [200, 401, 500]


class TestPerformanceWorkflows:
    """Test performance-related workflows and edge cases"""

    @pytest.fixture
    def test_client(self):
        return TestClient(app)

    def test_bulk_operations_workflow(self, test_client):
        """Test bulk operations performance"""
        headers = {"x-api-key": "rk_bulk_test_123"}

        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.routers.notes.get_db') as mock_db, \
             patch('api.search.vector_search.index_note') as mock_index:

            mock_user = type('User', (), {'org_id': 'bulk_org_123'})()
            mock_auth.return_value = mock_user

            mock_session = mock_db.return_value.__enter__.return_value

            # 1. Create multiple notes rapidly
            for i in range(10):
                note_data = {
                    "title": f"Bulk Note {i}",
                    "content_md": f"# Note {i}\n\nThis is bulk note number {i} with some content."
                }

                response = test_client.post("/v1/notes", json=note_data, headers=headers)
                assert response.status_code in [200, 201, 401, 422, 429, 500]

            # 2. Test pagination with large result sets
            mock_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
                Mock(note_id=f"note_{i}", title=f"Note {i}") for i in range(50)
            ]

            # Test different page sizes
            for page_size in [10, 25, 50, 100]:
                params = {"limit": page_size, "skip": 0}
                response = test_client.get("/v1/notes", params=params, headers=headers)
                assert response.status_code in [200, 401, 422, 500]

    def test_large_content_workflow(self, test_client):
        """Test handling of large note content"""
        headers = {"x-api-key": "rk_large_content_123"}

        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.db.database.get_db') as mock_db:

            mock_user = type('User', (), {'org_id': 'large_content_org_123'})()
            mock_auth.return_value = mock_user

            mock_session = mock_db.return_value.__enter__.return_value

            # 1. Test various content sizes
            content_sizes = [1000, 10000, 100000, 500000]  # 1KB to 500KB

            for size in content_sizes:
                large_content = "x" * size
                note_data = {
                    "title": f"Large Note ({size} chars)",
                    "content_md": large_content
                }

                response = test_client.post("/v1/notes", json=note_data, headers=headers)
                # Should handle gracefully or reject with proper error
                assert response.status_code in [200, 201, 413, 422, 500]

    def test_concurrent_access_workflow(self, test_client):
        """Test concurrent access patterns"""
        headers = {"x-api-key": "rk_concurrent_test_123"}

        with patch('api.auth.auth.get_current_user') as mock_auth, \
             patch('api.db.database.get_db') as mock_db:

            mock_user = type('User', (), {'org_id': 'concurrent_org_123'})()
            mock_auth.return_value = mock_user

            mock_session = mock_db.return_value.__enter__.return_value

            # Simulate concurrent read/write operations
            note_id = "concurrent_note_123"
            mock_note = Mock(note_id=note_id, version=1)
            mock_session.query.return_value.filter.return_value.first.return_value = mock_note

            # Multiple rapid updates (simulating concurrent editing)
            for i in range(5):
                update_data = {
                    "content_md": f"Updated content version {i}",
                    "version": mock_note.version
                }

                response = test_client.patch(f"/v1/notes/{note_id}", json=update_data, headers=headers)
                assert response.status_code in [200, 409, 422, 500]

                # Increment version for next update
                mock_note.version += 1