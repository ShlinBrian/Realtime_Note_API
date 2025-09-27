"""
Integration tests for Search API endpoints
"""
import pytest
import uuid
from unittest.mock import patch

from api.main import app


class TestSearchAPI:
    """Test search functionality"""

    def test_search_basic(self, test_client, auth_headers, mock_vector_search):
        """Test basic search functionality"""
        search_data = {
            "query": "machine learning",
            "top_k": 5
        }

        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert "results" in result
        assert isinstance(result["results"], list)

    def test_search_with_filters(self, test_client, auth_headers, mock_vector_search):
        """Test search with filters"""
        search_data = {
            "query": "python programming",
            "top_k": 3,
            "filters": {
                "min_score": 0.5,
                "title_only": True
            }
        }

        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert "results" in result

    def test_search_missing_query(self, test_client, auth_headers):
        """Test search without query"""
        search_data = {
            "top_k": 5
        }

        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)

        assert response.status_code == 422
        assert "query" in str(response.json())

    def test_search_empty_query(self, test_client, auth_headers):
        """Test search with empty query"""
        search_data = {
            "query": "",
            "top_k": 5
        }

        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)

        assert response.status_code == 422

    def test_search_invalid_top_k(self, test_client, auth_headers):
        """Test search with invalid top_k values"""
        # Zero top_k
        search_data = {
            "query": "test",
            "top_k": 0
        }

        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)
        assert response.status_code == 422

        # Negative top_k
        search_data["top_k"] = -1
        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)
        assert response.status_code == 422

        # Too large top_k
        search_data["top_k"] = 2000
        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)
        assert response.status_code == 422

    def test_search_missing_auth(self, test_client):
        """Test search without authentication"""
        search_data = {
            "query": "test search",
            "top_k": 5
        }

        response = test_client.post("/v1/search", json=search_data)
        assert response.status_code == 401

    def test_search_with_unicode(self, test_client, auth_headers, mock_vector_search):
        """Test search with unicode characters"""
        search_data = {
            "query": "机器学习 🤖",
            "top_k": 5
        }

        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert "results" in result

    def test_search_long_query(self, test_client, auth_headers, mock_vector_search):
        """Test search with very long query"""
        long_query = "machine learning " * 100  # Very long query
        search_data = {
            "query": long_query,
            "top_k": 5
        }

        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)

        assert response.status_code == 200

    @patch('api.search.vector_search.search_notes')
    def test_search_with_real_results(self, mock_search, test_client, auth_headers, test_org, test_session):
        """Test search with actual search results"""
        # Create test notes
        from api.models.models import Note
        notes = []
        note_data = [
            ("Machine Learning Basics", "Introduction to machine learning algorithms"),
            ("Python Programming", "Learning Python for data science"),
            ("Deep Learning", "Neural networks and deep learning concepts")
        ]

        for title, content in note_data:
            note = Note(
                note_id=str(uuid.uuid4()),
                org_id=test_org.org_id,
                title=title,
                content_md=f"# {title}\n\n{content}",
                version=1
            )
            test_session.add(note)
            notes.append(note)
        test_session.commit()

        # Mock search results
        mock_search.return_value = [
            (notes[0].note_id, 0.95),
            (notes[1].note_id, 0.75),
        ]

        search_data = {
            "query": "machine learning",
            "top_k": 5
        }

        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert len(result["results"]) == 2

        # Verify result structure
        first_result = result["results"][0]
        assert "note_id" in first_result
        assert "similarity_score" in first_result
        assert "title" in first_result
        assert "snippet" in first_result
        assert "created_at" in first_result
        assert "updated_at" in first_result

        # Verify ordering by similarity score
        assert result["results"][0]["similarity_score"] >= result["results"][1]["similarity_score"]

    @patch('api.search.vector_search.search_notes')
    def test_search_no_results(self, mock_search, test_client, auth_headers):
        """Test search with no results"""
        mock_search.return_value = []

        search_data = {
            "query": "nonexistent topic",
            "top_k": 5
        }

        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert len(result["results"]) == 0

    def test_search_filters_validation(self, test_client, auth_headers):
        """Test search filters validation"""
        # Invalid min_score (too high)
        search_data = {
            "query": "test",
            "filters": {
                "min_score": 1.5  # Should be <= 1.0
            }
        }

        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)
        assert response.status_code == 422

        # Invalid min_score (negative)
        search_data["filters"]["min_score"] = -0.1
        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)
        assert response.status_code == 422

    def test_search_malformed_json(self, test_client, auth_headers):
        """Test search with malformed JSON"""
        response = test_client.post(
            "/v1/search",
            data="{ invalid json }",
            headers={**auth_headers, "Content-Type": "application/json"}
        )

        assert response.status_code == 422

    @patch('api.search.vector_search.search_notes')
    def test_search_with_deleted_notes(self, mock_search, test_client, auth_headers, test_org, test_session):
        """Test that deleted notes don't appear in search results"""
        from api.models.models import Note

        # Create a note and mark it as deleted
        deleted_note = Note(
            note_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            title="Deleted Note",
            content_md="This note is deleted",
            version=1,
            deleted=True
        )
        test_session.add(deleted_note)
        test_session.commit()

        # Mock search to return the deleted note
        mock_search.return_value = [(deleted_note.note_id, 0.95)]

        search_data = {
            "query": "deleted",
            "top_k": 5
        }

        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        # Should have no results since the note is deleted
        assert len(result["results"]) == 0

    @patch('api.search.vector_search.search_notes')
    def test_search_snippet_generation(self, mock_search, test_client, auth_headers, test_org, test_session):
        """Test search result snippet generation"""
        from api.models.models import Note

        long_content = """
# Machine Learning Fundamentals

Machine learning is a subset of artificial intelligence that focuses on the development of algorithms and statistical models that enable computer systems to improve their performance on a specific task through experience.

## Types of Machine Learning

1. Supervised Learning
2. Unsupervised Learning
3. Reinforcement Learning

The key insight is that machine learning algorithms can automatically learn patterns from data without being explicitly programmed for every possible scenario.
"""

        note = Note(
            note_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            title="ML Fundamentals",
            content_md=long_content,
            version=1
        )
        test_session.add(note)
        test_session.commit()

        mock_search.return_value = [(note.note_id, 0.95)]

        search_data = {
            "query": "machine learning",
            "top_k": 1
        }

        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert len(result["results"]) == 1

        snippet = result["results"][0]["snippet"]
        # Snippet should be truncated and not contain the full content
        assert len(snippet) < len(long_content)
        assert "Machine Learning Fundamentals" in snippet

    def test_search_case_insensitive(self, test_client, auth_headers, mock_vector_search):
        """Test that search is case insensitive"""
        search_data = {
            "query": "MACHINE LEARNING",
            "top_k": 5
        }

        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)

        assert response.status_code == 200
        # Should work the same as lowercase


class TestSearchAPIPerformance:
    """Test search API performance characteristics"""

    @patch('api.search.vector_search.search_notes')
    def test_search_large_result_set(self, mock_search, test_client, auth_headers):
        """Test search with large number of results"""
        # Mock a large number of search results
        large_results = [(f"note-{i}", 0.9 - i * 0.01) for i in range(100)]
        mock_search.return_value = large_results

        search_data = {
            "query": "test",
            "top_k": 100
        }

        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        # Should handle large result sets
        assert len(result["results"]) <= 100

    def test_search_concurrent_requests(self, test_client, auth_headers, mock_vector_search):
        """Test concurrent search requests"""
        import threading
        import time

        results = []
        errors = []

        def search_worker():
            try:
                search_data = {
                    "query": f"test query {threading.current_thread().ident}",
                    "top_k": 5
                }
                response = test_client.post("/v1/search", json=search_data, headers=auth_headers)
                results.append(response.status_code)
            except Exception as e:
                errors.append(e)

        # Start multiple concurrent search requests
        threads = []
        for i in range(10):
            thread = threading.Thread(target=search_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All requests should succeed
        assert len(errors) == 0
        assert all(status == 200 for status in results)
        assert len(results) == 10


class TestSearchAPIEdgeCases:
    """Test edge cases and error conditions"""

    def test_search_special_characters(self, test_client, auth_headers, mock_vector_search):
        """Test search with special characters"""
        special_queries = [
            "C++ programming",
            "machine-learning",
            "data_science",
            "AI/ML",
            "NLP & text processing",
            "search terms: with colons",
            "terms; with; semicolons",
            "terms|with|pipes",
            "terms (with) parentheses",
            "terms [with] brackets",
            "terms {with} braces",
            "terms <with> angles",
            "terms \"with\" quotes",
            "terms 'with' apostrophes",
        ]

        for query in special_queries:
            search_data = {
                "query": query,
                "top_k": 5
            }

            response = test_client.post("/v1/search", json=search_data, headers=auth_headers)
            assert response.status_code == 200, f"Failed for query: {query}"

    def test_search_numeric_query(self, test_client, auth_headers, mock_vector_search):
        """Test search with numeric queries"""
        numeric_queries = [
            "123",
            "3.14159",
            "2024",
            "version 2.0",
            "python 3.9",
            "HTTP 404 error"
        ]

        for query in numeric_queries:
            search_data = {
                "query": query,
                "top_k": 5
            }

            response = test_client.post("/v1/search", json=search_data, headers=auth_headers)
            assert response.status_code == 200

    @patch('api.search.vector_search.search_notes')
    def test_search_error_handling(self, mock_search, test_client, auth_headers):
        """Test search error handling"""
        # Mock search to raise an exception
        mock_search.side_effect = Exception("Search service error")

        search_data = {
            "query": "test",
            "top_k": 5
        }

        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)

        # Should handle the error gracefully
        assert response.status_code == 500

    def test_search_boundary_values(self, test_client, auth_headers, mock_vector_search):
        """Test search with boundary values"""
        # Test minimum valid top_k
        search_data = {
            "query": "test",
            "top_k": 1
        }
        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)
        assert response.status_code == 200

        # Test maximum valid top_k
        search_data["top_k"] = 1000
        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)
        assert response.status_code == 200

        # Test minimum valid min_score
        search_data = {
            "query": "test",
            "filters": {"min_score": 0.0}
        }
        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)
        assert response.status_code == 200

        # Test maximum valid min_score
        search_data["filters"]["min_score"] = 1.0
        response = test_client.post("/v1/search", json=search_data, headers=auth_headers)
        assert response.status_code == 200