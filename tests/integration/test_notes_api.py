"""
Integration tests for Notes API endpoints
"""
import pytest
import uuid
import json
from fastapi.testclient import TestClient

from api.main import app


class TestNotesAPI:
    """Test Notes CRUD operations"""

    def test_create_note_success(self, test_client, auth_headers, mock_vector_search):
        """Test successful note creation"""
        note_data = {
            "title": "Test Note",
            "content_md": "# Test Note\n\nThis is a test note."
        }

        response = test_client.post("/v1/notes", json=note_data, headers=auth_headers)

        assert response.status_code == 201
        note_id = response.json()
        assert isinstance(note_id, str)

        # Verify UUID format
        uuid.UUID(note_id)

    def test_create_note_missing_auth(self, test_client):
        """Test note creation without authentication"""
        note_data = {
            "title": "Test Note",
            "content_md": "Content"
        }

        response = test_client.post("/v1/notes", json=note_data)

        assert response.status_code == 401

    def test_create_note_invalid_data(self, test_client, auth_headers):
        """Test note creation with invalid data"""
        # Missing title
        note_data = {
            "content_md": "Content without title"
        }

        response = test_client.post("/v1/notes", json=note_data, headers=auth_headers)

        assert response.status_code == 422
        assert "title" in response.json()["detail"][0]["loc"]

    def test_create_note_empty_title(self, test_client, auth_headers):
        """Test note creation with empty title"""
        note_data = {
            "title": "",
            "content_md": "Content"
        }

        response = test_client.post("/v1/notes", json=note_data, headers=auth_headers)

        assert response.status_code == 422

    def test_get_note_success(self, test_client, auth_headers, test_note):
        """Test successful note retrieval"""
        response = test_client.get(f"/v1/notes/{test_note.note_id}", headers=auth_headers)

        assert response.status_code == 200
        note_data = response.json()
        assert note_data["note_id"] == test_note.note_id
        assert note_data["title"] == test_note.title
        assert note_data["content_md"] == test_note.content_md
        assert note_data["version"] == test_note.version

    def test_get_note_not_found(self, test_client, auth_headers):
        """Test retrieving non-existent note"""
        fake_id = str(uuid.uuid4())
        response = test_client.get(f"/v1/notes/{fake_id}", headers=auth_headers)

        assert response.status_code == 404

    def test_get_note_invalid_uuid(self, test_client, auth_headers):
        """Test retrieving note with invalid UUID"""
        response = test_client.get("/v1/notes/invalid-uuid", headers=auth_headers)

        assert response.status_code == 422

    def test_get_note_missing_auth(self, test_client, test_note):
        """Test retrieving note without authentication"""
        response = test_client.get(f"/v1/notes/{test_note.note_id}")

        assert response.status_code == 401

    def test_update_note_success(self, test_client, auth_headers, test_note):
        """Test successful note update"""
        update_data = {
            "title": "Updated Title",
            "content_md": "# Updated Content\n\nThis note has been updated."
        }

        response = test_client.put(f"/v1/notes/{test_note.note_id}", json=update_data, headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert result["version"] == test_note.version + 1

        # Verify the note was actually updated
        get_response = test_client.get(f"/v1/notes/{test_note.note_id}", headers=auth_headers)
        updated_note = get_response.json()
        assert updated_note["title"] == "Updated Title"
        assert updated_note["content_md"] == "# Updated Content\n\nThis note has been updated."

    def test_update_note_partial(self, test_client, auth_headers, test_note):
        """Test partial note update"""
        update_data = {
            "title": "Only Title Updated"
        }

        response = test_client.put(f"/v1/notes/{test_note.note_id}", json=update_data, headers=auth_headers)

        assert response.status_code == 200

        # Verify only title was updated
        get_response = test_client.get(f"/v1/notes/{test_note.note_id}", headers=auth_headers)
        updated_note = get_response.json()
        assert updated_note["title"] == "Only Title Updated"
        assert updated_note["content_md"] == test_note.content_md  # Should remain unchanged

    def test_update_note_not_found(self, test_client, auth_headers):
        """Test updating non-existent note"""
        fake_id = str(uuid.uuid4())
        update_data = {"title": "New Title"}

        response = test_client.put(f"/v1/notes/{fake_id}", json=update_data, headers=auth_headers)

        assert response.status_code == 404

    def test_update_note_empty_data(self, test_client, auth_headers, test_note):
        """Test updating note with empty data"""
        update_data = {}

        response = test_client.put(f"/v1/notes/{test_note.note_id}", json=update_data, headers=auth_headers)

        # Should succeed even with empty data (no changes)
        assert response.status_code == 200

    def test_delete_note_success(self, test_client, auth_headers, test_note, mock_vector_search):
        """Test successful note deletion"""
        response = test_client.delete(f"/v1/notes/{test_note.note_id}", headers=auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert result["deleted"] is True

        # Verify note is no longer accessible
        get_response = test_client.get(f"/v1/notes/{test_note.note_id}", headers=auth_headers)
        assert get_response.status_code == 404

    def test_delete_note_not_found(self, test_client, auth_headers):
        """Test deleting non-existent note"""
        fake_id = str(uuid.uuid4())
        response = test_client.delete(f"/v1/notes/{fake_id}", headers=auth_headers)

        assert response.status_code == 404

    def test_delete_note_missing_auth(self, test_client, test_note):
        """Test deleting note without authentication"""
        response = test_client.delete(f"/v1/notes/{test_note.note_id}")

        assert response.status_code == 401

    def test_list_notes_success(self, test_client, auth_headers, test_org, test_session):
        """Test successful notes listing"""
        # Create multiple notes
        from api.models.models import Note
        notes = []
        for i in range(3):
            note = Note(
                note_id=str(uuid.uuid4()),
                org_id=test_org.org_id,
                title=f"Note {i}",
                content_md=f"Content {i}",
                version=1
            )
            test_session.add(note)
            notes.append(note)
        test_session.commit()

        response = test_client.get("/v1/notes", headers=auth_headers)

        assert response.status_code == 200
        response_notes = response.json()

        # Should include the test_note fixture plus the 3 new notes
        assert len(response_notes) >= 3

        # Verify note structure
        for note_data in response_notes:
            assert "note_id" in note_data
            assert "title" in note_data
            assert "content_md" in note_data
            assert "version" in note_data
            assert "created_at" in note_data
            assert "updated_at" in note_data

    def test_list_notes_pagination(self, test_client, auth_headers, test_org, test_session):
        """Test notes listing with pagination"""
        # Create multiple notes
        from api.models.models import Note
        for i in range(10):
            note = Note(
                note_id=str(uuid.uuid4()),
                org_id=test_org.org_id,
                title=f"Note {i}",
                content_md=f"Content {i}",
                version=1
            )
            test_session.add(note)
        test_session.commit()

        # Test first page
        response = test_client.get("/v1/notes?skip=0&limit=5", headers=auth_headers)
        assert response.status_code == 200
        page1_notes = response.json()
        assert len(page1_notes) <= 5

        # Test second page
        response = test_client.get("/v1/notes?skip=5&limit=5", headers=auth_headers)
        assert response.status_code == 200
        page2_notes = response.json()

        # Should have different notes
        page1_ids = {note["note_id"] for note in page1_notes}
        page2_ids = {note["note_id"] for note in page2_notes}
        assert page1_ids.isdisjoint(page2_ids)

    def test_list_notes_invalid_pagination(self, test_client, auth_headers):
        """Test notes listing with invalid pagination parameters"""
        # Negative skip
        response = test_client.get("/v1/notes?skip=-1", headers=auth_headers)
        assert response.status_code == 422

        # Invalid limit
        response = test_client.get("/v1/notes?limit=0", headers=auth_headers)
        assert response.status_code == 422

        # Limit too high
        response = test_client.get("/v1/notes?limit=2000", headers=auth_headers)
        assert response.status_code == 422

    def test_list_notes_missing_auth(self, test_client):
        """Test listing notes without authentication"""
        response = test_client.get("/v1/notes")
        assert response.status_code == 401

    def test_list_notes_ordered_by_updated_at(self, test_client, auth_headers, test_org, test_session):
        """Test that notes are ordered by updated_at descending"""
        from api.models.models import Note
        import time

        # Create notes with slight time differences
        notes = []
        for i in range(3):
            note = Note(
                note_id=str(uuid.uuid4()),
                org_id=test_org.org_id,
                title=f"Note {i}",
                content_md=f"Content {i}",
                version=1
            )
            test_session.add(note)
            test_session.commit()
            test_session.refresh(note)
            notes.append(note)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        response = test_client.get("/v1/notes", headers=auth_headers)
        assert response.status_code == 200

        response_notes = response.json()
        if len(response_notes) >= 2:
            # Should be ordered by updated_at descending (newest first)
            for i in range(len(response_notes) - 1):
                current_time = response_notes[i]["updated_at"]
                next_time = response_notes[i + 1]["updated_at"]
                assert current_time >= next_time


class TestNotesAPIEdgeCases:
    """Test edge cases and error conditions"""

    def test_create_note_with_unicode(self, test_client, auth_headers, mock_vector_search):
        """Test creating note with unicode characters"""
        note_data = {
            "title": "测试笔记 🚀",
            "content_md": "# 测试内容\n\n这是一个包含表情符号的测试 😊"
        }

        response = test_client.post("/v1/notes", json=note_data, headers=auth_headers)

        assert response.status_code == 201
        note_id = response.json()

        # Verify the note was created correctly
        get_response = test_client.get(f"/v1/notes/{note_id}", headers=auth_headers)
        assert get_response.status_code == 200
        note = get_response.json()
        assert note["title"] == "测试笔记 🚀"
        assert "😊" in note["content_md"]

    def test_create_note_with_very_long_content(self, test_client, auth_headers, mock_vector_search):
        """Test creating note with very long content"""
        long_content = "x" * 100000  # 100KB content
        note_data = {
            "title": "Long Content Note",
            "content_md": long_content
        }

        response = test_client.post("/v1/notes", json=note_data, headers=auth_headers)

        assert response.status_code == 201

    def test_create_note_with_markdown_content(self, test_client, auth_headers, mock_vector_search):
        """Test creating note with complex markdown"""
        markdown_content = """
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
        note_data = {
            "title": "Markdown Test",
            "content_md": markdown_content
        }

        response = test_client.post("/v1/notes", json=note_data, headers=auth_headers)

        assert response.status_code == 201
        note_id = response.json()

        # Verify content is preserved
        get_response = test_client.get(f"/v1/notes/{note_id}", headers=auth_headers)
        note = get_response.json()
        assert "```python" in note["content_md"]
        assert "| Column 1" in note["content_md"]

    def test_concurrent_note_updates(self, test_client, auth_headers, test_note):
        """Test concurrent updates to the same note"""
        # Simulate concurrent updates
        update_data1 = {"title": "Update 1"}
        update_data2 = {"title": "Update 2"}

        # Both should succeed (last one wins)
        response1 = test_client.put(f"/v1/notes/{test_note.note_id}", json=update_data1, headers=auth_headers)
        response2 = test_client.put(f"/v1/notes/{test_note.note_id}", json=update_data2, headers=auth_headers)

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Final state should be from the last update
        get_response = test_client.get(f"/v1/notes/{test_note.note_id}", headers=auth_headers)
        final_note = get_response.json()
        assert final_note["title"] == "Update 2"

    def test_malformed_json(self, test_client, auth_headers):
        """Test handling of malformed JSON"""
        response = test_client.post(
            "/v1/notes",
            data="{ invalid json }",
            headers={**auth_headers, "Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_sql_injection_attempt(self, test_client, auth_headers, mock_vector_search):
        """Test protection against SQL injection"""
        malicious_data = {
            "title": "'; DROP TABLE notes; --",
            "content_md": "SQL injection attempt"
        }

        response = test_client.post("/v1/notes", json=malicious_data, headers=auth_headers)

        # Should succeed (content is treated as literal string)
        assert response.status_code == 201

        # Verify the malicious content is stored literally
        note_id = response.json()
        get_response = test_client.get(f"/v1/notes/{note_id}", headers=auth_headers)
        note = get_response.json()
        assert note["title"] == "'; DROP TABLE notes; --"

    def test_xss_attempt(self, test_client, auth_headers, mock_vector_search):
        """Test handling of XSS attempts"""
        xss_data = {
            "title": "<script>alert('XSS')</script>",
            "content_md": "<img src=x onerror=alert('XSS')>"
        }

        response = test_client.post("/v1/notes", json=xss_data, headers=auth_headers)

        # Should succeed (content is stored as-is, sanitization happens on frontend)
        assert response.status_code == 201

        note_id = response.json()
        get_response = test_client.get(f"/v1/notes/{note_id}", headers=auth_headers)
        note = get_response.json()
        assert "<script>" in note["title"]
        assert "<img src=" in note["content_md"]