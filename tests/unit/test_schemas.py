"""
Unit tests for Pydantic schemas
"""
import pytest
from pydantic import ValidationError
from datetime import datetime

from api.models.schemas import (
    NoteCreate, NoteResponse, NotePatch,
    SearchRequest, SearchResponse, SearchResult,
    ApiKeyCreate, ApiKeyResponse,
    NoteDeleteResponse
)


class TestNoteSchemas:
    """Test note-related schemas"""

    def test_create_note_request_valid(self):
        """Test valid note creation request"""
        data = {
            "title": "Test Note",
            "content_md": "# Test\n\nThis is a test note."
        }
        request = NoteCreate(**data)

        assert request.title == "Test Note"
        assert request.content_md == "# Test\n\nThis is a test note."

    def test_create_note_request_minimal(self):
        """Test minimal note creation request"""
        data = {
            "title": "Minimal Note",
            "content_md": ""
        }
        request = NoteCreate(**data)

        assert request.title == "Minimal Note"
        assert request.content_md == ""

    def test_create_note_request_missing_title(self):
        """Test note creation request without title"""
        data = {
            "content_md": "Content without title"
        }
        with pytest.raises(ValidationError) as exc_info:
            NoteCreate(**data)

        assert "title" in str(exc_info.value)

    def test_create_note_request_missing_content(self):
        """Test note creation request without content"""
        data = {
            "title": "Title without content"
        }
        with pytest.raises(ValidationError) as exc_info:
            NoteCreate(**data)

        assert "content_md" in str(exc_info.value)

    def test_create_note_request_empty_title(self):
        """Test note creation request with empty title"""
        data = {
            "title": "",
            "content_md": "Some content"
        }
        with pytest.raises(ValidationError) as exc_info:
            NoteCreate(**data)

        assert "at least 1 character" in str(exc_info.value)

    def test_create_note_request_long_title(self):
        """Test note creation request with very long title"""
        data = {
            "title": "x" * 201,  # Assuming 200 is the limit
            "content_md": "Content"
        }
        with pytest.raises(ValidationError) as exc_info:
            NoteCreate(**data)

        assert "at most" in str(exc_info.value)

    def test_note_response_valid(self):
        """Test valid note response"""
        data = {
            "note_id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Test Note",
            "content_md": "# Test Content",
            "version": 1,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z"
        }
        response = NoteResponse(**data)

        assert response.note_id == "123e4567-e89b-12d3-a456-426614174000"
        assert response.title == "Test Note"
        assert response.content_md == "# Test Content"
        assert response.version == 1
        assert isinstance(response.created_at, datetime)
        assert isinstance(response.updated_at, datetime)

    def test_update_note_request_partial(self):
        """Test partial note update request"""
        data = {
            "title": "Updated Title"
        }
        request = NotePatch(**data)

        assert request.title == "Updated Title"
        assert request.content_md is None

    def test_update_note_request_full(self):
        """Test full note update request"""
        data = {
            "title": "Updated Title",
            "content_md": "Updated content"
        }
        request = NotePatch(**data)

        assert request.title == "Updated Title"
        assert request.content_md == "Updated content"

    def test_update_note_request_empty(self):
        """Test empty note update request"""
        data = {}
        request = NotePatch(**data)

        assert request.title is None
        assert request.content_md is None

    def test_note_delete_response(self):
        """Test note delete response"""
        data = {"deleted": True}
        response = NoteDeleteResponse(**data)

        assert response.deleted is True


class TestSearchSchemas:
    """Test search-related schemas"""

    def test_search_request_minimal(self):
        """Test minimal search request"""
        data = {"query": "test search"}
        request = SearchRequest(**data)

        assert request.query == "test search"
        assert request.top_k == 10  # Default value
        # SearchRequest doesn't have filters field

    def test_search_request_full(self):
        """Test full search request"""
        data = {
            "query": "machine learning",
            "top_k": 5
        }
        request = SearchRequest(**data)

        assert request.query == "machine learning"
        assert request.top_k == 5

    def test_search_request_empty_query(self):
        """Test search request with empty query"""
        data = {"query": ""}
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(**data)

        assert "at least 1 character" in str(exc_info.value)

    def test_search_request_invalid_top_k(self):
        """Test search request with invalid top_k"""
        data = {"query": "test", "top_k": 0}
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(**data)

        assert "greater than or equal to 1" in str(exc_info.value)

    def test_search_request_large_top_k(self):
        """Test search request with very large top_k"""
        data = {"query": "test", "top_k": 1001}
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(**data)

        assert "less than or equal to 100" in str(exc_info.value)

    def test_search_result_valid(self):
        """Test valid search result"""
        data = {
            "note_id": "123e4567-e89b-12d3-a456-426614174000",
            "similarity_score": 0.85,
            "title": "Found Note",
            "snippet": "This is a snippet...",
            "highlighted_content": None,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z"
        }
        result = SearchResult(**data)

        assert result.note_id == "123e4567-e89b-12d3-a456-426614174000"
        assert result.similarity_score == 0.85
        assert result.title == "Found Note"
        assert result.snippet == "This is a snippet..."
        assert result.highlighted_content is None

    def test_search_result_invalid_score(self):
        """Test search result with invalid similarity score"""
        data = {
            "note_id": "123e4567-e89b-12d3-a456-426614174000",
            "similarity_score": 1.5,  # Should be between 0 and 1
            "title": "Found Note",
            "snippet": "Snippet",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z"
        }
        with pytest.raises(ValidationError) as exc_info:
            SearchResult(**data)

        assert "less than or equal to 1" in str(exc_info.value)

    def test_search_response_valid(self):
        """Test valid search response"""
        result_data = {
            "note_id": "123e4567-e89b-12d3-a456-426614174000",
            "similarity_score": 0.85,
            "title": "Found Note",
            "snippet": "Snippet",
            "highlighted_content": None,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T12:00:00Z"
        }
        data = {
            "results": [result_data]
        }
        response = SearchResponse(**data)

        assert len(response.results) == 1
        assert response.results[0].note_id == "123e4567-e89b-12d3-a456-426614174000"

    def test_search_response_empty(self):
        """Test empty search response"""
        data = {"results": []}
        response = SearchResponse(**data)

        assert len(response.results) == 0


class TestApiKeySchemas:
    """Test API key schemas"""

    def test_api_key_create_request_valid(self):
        """Test valid API key creation request"""
        data = {"name": "Test API Key"}
        request = ApiKeyCreate(**data)

        assert request.name == "Test API Key"

    def test_api_key_create_request_empty_name(self):
        """Test API key creation with empty name"""
        data = {"name": ""}
        with pytest.raises(ValidationError) as exc_info:
            ApiKeyCreate(**data)

        assert "at least 1 character" in str(exc_info.value)

    def test_api_key_create_request_long_name(self):
        """Test API key creation with very long name"""
        data = {"name": "x" * 101}  # Assuming 100 is the limit
        with pytest.raises(ValidationError) as exc_info:
            ApiKeyCreate(**data)

        assert "at most" in str(exc_info.value)

    def test_api_key_response_valid(self):
        """Test valid API key response"""
        data = {
            "key_id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Test Key",
            "key": "rk_1234567890abcdef",
            "created_at": datetime.now(),
            "expires_at": None
        }
        response = ApiKeyResponse(**data)

        assert response.key_id == "123e4567-e89b-12d3-a456-426614174000"
        assert response.name == "Test Key"
        assert response.key == "rk_1234567890abcdef"
        assert response.expires_at is None
        assert isinstance(response.created_at, datetime)


class TestSchemaValidation:
    """Test schema validation edge cases"""

    def test_unicode_content(self):
        """Test schemas with unicode content"""
        data = {
            "title": "测试笔记 🚀",
            "content_md": "# 测试内容\n\n这是一个包含表情符号的测试 😊"
        }
        request = NoteCreate(**data)

        assert request.title == "测试笔记 🚀"
        assert "😊" in request.content_md

    def test_markdown_content(self):
        """Test schemas with complex markdown content"""
        content = """
# Main Title

## Subsection

- List item 1
- List item 2
  - Nested item

```python
def hello():
    print("Hello, World!")
```

[Link](https://example.com)

> Blockquote text

| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |
"""
        data = {
            "title": "Markdown Test",
            "content_md": content
        }
        request = NoteCreate(**data)

        assert request.title == "Markdown Test"
        assert "```python" in request.content_md
        assert "| Column 1" in request.content_md

    def test_very_long_content(self):
        """Test schemas with very long content"""
        long_content = "x" * 100000  # 100KB content
        data = {
            "title": "Long Content Note",
            "content_md": long_content
        }
        request = NoteCreate(**data)

        assert request.title == "Long Content Note"
        assert len(request.content_md) == 100000

    def test_special_characters(self):
        """Test schemas with special characters"""
        data = {
            "title": "Special chars: !@#$%^&*(){}[]|\\:;\"'<>?,./-+=",
            "content_md": "Content with special chars: \n\t\r\\'\"&<>"
        }
        request = NoteCreate(**data)

        assert "!@#$%^&*()" in request.title
        assert "\\'" in request.content_md and "&<>" in request.content_md