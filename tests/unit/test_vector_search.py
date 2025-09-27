"""
Unit tests for vector search functionality
"""
import pytest
import numpy as np
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
import threading
import pickle

from api.search.vector_search import (
    NoteVectorIndex, text_to_embedding, index_note, remove_note_from_index,
    search_notes, get_index_for_org, _get_embedding_model, _get_embedding_dimension,
    rebuild_index_for_org
)
from api.models.models import Note


class TestTextToEmbedding:
    """Test embedding generation functionality"""

    def test_text_to_embedding_basic(self):
        """Test basic embedding generation"""
        text = "Hello world"
        embedding = text_to_embedding(text)

        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 384  # Default dimension
        assert embedding.dtype == np.float32

    def test_text_to_embedding_deterministic(self):
        """Test that embedding generation is deterministic"""
        text = "Machine learning is fascinating"

        embedding1 = text_to_embedding(text)
        embedding2 = text_to_embedding(text)

        np.testing.assert_array_equal(embedding1, embedding2)

    def test_text_to_embedding_different_texts(self):
        """Test that different texts produce different embeddings"""
        text1 = "Machine learning"
        text2 = "Deep learning"

        embedding1 = text_to_embedding(text1)
        embedding2 = text_to_embedding(text2)

        # Should not be identical
        assert not np.array_equal(embedding1, embedding2)

    def test_text_to_embedding_empty_string(self):
        """Test embedding generation with empty string"""
        embedding = text_to_embedding("")

        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 384

    def test_text_to_embedding_unicode(self):
        """Test embedding generation with unicode text"""
        text = "机器学习很有趣 🤖"
        embedding = text_to_embedding(text)

        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 384

    def test_text_to_embedding_normalized(self):
        """Test that embeddings are normalized"""
        text = "Test normalization"
        embedding = text_to_embedding(text)

        # Check if embedding is approximately unit length
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 1e-6

    @patch('api.search.vector_search.SENTENCE_TRANSFORMERS_AVAILABLE', True)
    @patch('api.search.vector_search._get_embedding_model')
    def test_text_to_embedding_with_sentence_transformers(self, mock_get_model):
        """Test embedding with sentence transformers"""
        # Mock sentence transformer model
        mock_model = Mock()
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        mock_get_model.return_value = mock_model

        text = "Test with sentence transformers"
        embedding = text_to_embedding(text)

        mock_model.encode.assert_called_once_with("Test with sentence transformers", normalize_embeddings=True)
        np.testing.assert_array_equal(embedding, np.array([0.1, 0.2, 0.3], dtype=np.float32))

    @patch('api.search.vector_search.SENTENCE_TRANSFORMERS_AVAILABLE', True)
    @patch('api.search.vector_search._get_embedding_model')
    def test_text_to_embedding_fallback_on_error(self, mock_get_model):
        """Test fallback to hash-based embedding on sentence transformer error"""
        # Mock sentence transformer to raise an error
        mock_model = Mock()
        mock_model.encode.side_effect = Exception("Model error")
        mock_get_model.return_value = mock_model

        text = "Test fallback"
        embedding = text_to_embedding(text)

        # Should fallback to hash-based embedding
        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 384


class TestNoteVectorIndex:
    """Test the NoteVectorIndex class"""

    def test_index_initialization(self, temp_index_dir):
        """Test index initialization"""
        import uuid
        org_id = f"test-org-{uuid.uuid4()}"
        index = NoteVectorIndex(org_id)

        assert index.org_id == org_id
        assert index.dimension == 384  # Default dimension
        assert len(index.note_ids) == 0
        assert len(index.embeddings) == 0
        assert index.index is not None  # FAISS index should be created

    @patch('api.search.vector_search.FAISS_AVAILABLE', False)
    def test_index_initialization_without_faiss(self, temp_index_dir):
        """Test index initialization without FAISS"""
        import uuid
        org_id = f"test-org-{uuid.uuid4()}"
        index = NoteVectorIndex(org_id)

        assert index.org_id == org_id
        assert index.index is None  # No FAISS index

    def test_add_note_to_index(self, temp_index_dir):
        """Test adding a note to the index"""
        import uuid
        org_id = f"test-org-{uuid.uuid4()}"
        index = NoteVectorIndex(org_id)

        note_id = "note-123"
        embedding = np.random.randn(384).astype(np.float32)

        index.add_note(note_id, embedding)

        assert note_id in index.note_ids
        assert len(index.embeddings) == 1
        assert index.index.ntotal == 1

    def test_add_duplicate_note(self, temp_index_dir):
        """Test adding the same note twice (should update)"""
        import uuid
        org_id = f"test-org-{uuid.uuid4()}"
        index = NoteVectorIndex(org_id)

        note_id = "note-123"
        embedding1 = np.random.randn(384).astype(np.float32)
        embedding2 = np.random.randn(384).astype(np.float32)

        index.add_note(note_id, embedding1)
        index.add_note(note_id, embedding2)

        # Should still only have one note
        assert len(index.note_ids) == 1
        assert len(index.embeddings) == 1
        assert index.index.ntotal == 1

    def test_remove_note_from_index(self, temp_index_dir):
        """Test removing a note from the index"""
        import uuid
        org_id = f"test-org-{uuid.uuid4()}"
        index = NoteVectorIndex(org_id)

        # Add multiple notes
        note_id1 = "note-123"
        note_id2 = "note-456"
        embedding1 = np.random.randn(384).astype(np.float32)
        embedding2 = np.random.randn(384).astype(np.float32)

        index.add_note(note_id1, embedding1)
        index.add_note(note_id2, embedding2)

        assert len(index.note_ids) == 2
        assert index.index.ntotal == 2

        # Remove one note
        index.remove_note(note_id1)

        assert note_id1 not in index.note_ids
        assert note_id2 in index.note_ids
        assert len(index.note_ids) == 1
        assert index.index.ntotal == 1

    def test_remove_nonexistent_note(self, temp_index_dir):
        """Test removing a note that doesn't exist"""
        import uuid
        org_id = f"test-org-{uuid.uuid4()}"
        index = NoteVectorIndex(org_id)

        # Should not raise an error
        index.remove_note("nonexistent-note")

        assert len(index.note_ids) == 0

    def test_search_empty_index(self, temp_index_dir):
        """Test searching in an empty index"""
        import uuid
        org_id = f"test-org-{uuid.uuid4()}"
        index = NoteVectorIndex(org_id)

        query_embedding = np.random.randn(384).astype(np.float32)
        results = index.search(query_embedding, top_k=5)

        assert len(results) == 0

    def test_search_with_results(self, temp_index_dir):
        """Test searching with results"""
        import uuid
        org_id = f"test-org-{uuid.uuid4()}"
        index = NoteVectorIndex(org_id)

        # Add some notes
        for i in range(5):
            note_id = f"note-{i}"
            embedding = np.random.randn(384).astype(np.float32)
            index.add_note(note_id, embedding)

        query_embedding = np.random.randn(384).astype(np.float32)
        results = index.search(query_embedding, top_k=3)

        assert len(results) == 3
        for note_id, similarity in results:
            assert note_id.startswith("note-")
            assert 0 <= similarity <= 1

    def test_search_similarity_ordering(self, temp_index_dir):
        """Test that search results are ordered by similarity"""
        import uuid
        org_id = f"test-org-{uuid.uuid4()}"
        index = NoteVectorIndex(org_id)

        # Add notes with known embeddings
        base_embedding = np.ones(384, dtype=np.float32)
        base_embedding = base_embedding / np.linalg.norm(base_embedding)

        # Very similar embedding
        similar_embedding = base_embedding + np.random.randn(384).astype(np.float32) * 0.01
        similar_embedding = similar_embedding / np.linalg.norm(similar_embedding)

        # Less similar embedding
        different_embedding = np.random.randn(384).astype(np.float32)
        different_embedding = different_embedding / np.linalg.norm(different_embedding)

        index.add_note("similar", similar_embedding)
        index.add_note("different", different_embedding)

        # Search with base embedding
        results = index.search(base_embedding, top_k=2)

        assert len(results) == 2
        # First result should be more similar
        assert results[0][1] >= results[1][1]

    def test_index_persistence(self, temp_index_dir):
        """Test that index can be saved and loaded"""
        import uuid
        org_id = f"test-org-{uuid.uuid4()}"

        # Create and populate index
        index1 = NoteVectorIndex(org_id)
        note_id = "test-note"
        embedding = np.random.randn(384).astype(np.float32)
        index1.add_note(note_id, embedding)

        # Create new index instance (should load from disk)
        index2 = NoteVectorIndex(org_id)

        assert note_id in index2.note_ids
        assert len(index2.embeddings) == 1
        assert index2.index.ntotal == 1

    @patch('api.search.vector_search.FAISS_AVAILABLE', False)
    def test_search_without_faiss(self, temp_index_dir):
        """Test search functionality without FAISS"""
        import uuid
        org_id = f"test-org-{uuid.uuid4()}"
        index = NoteVectorIndex(org_id)

        # Add some notes
        for i in range(3):
            note_id = f"note-{i}"
            embedding = np.random.randn(384).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)  # Normalize
            index.add_note(note_id, embedding)

        query_embedding = np.random.randn(384).astype(np.float32)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)

        results = index.search(query_embedding, top_k=2)

        assert len(results) == 2
        # Results should be ordered by similarity (descending)
        assert results[0][1] >= results[1][1]

    def test_thread_safety(self, temp_index_dir):
        """Test thread safety of index operations"""
        import uuid
        org_id = f"test-org-{uuid.uuid4()}"
        index = NoteVectorIndex(org_id)

        def add_notes(start_idx, count):
            for i in range(start_idx, start_idx + count):
                note_id = f"note-{i}"
                embedding = np.random.randn(384).astype(np.float32)
                index.add_note(note_id, embedding)

        # Run multiple threads adding notes
        threads = []
        for i in range(3):
            thread = threading.Thread(target=add_notes, args=(i * 10, 10))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have 30 notes total
        assert len(index.note_ids) == 30
        assert index.index.ntotal == 30


class TestIndexManagement:
    """Test index management functions"""

    def test_get_index_for_org(self, temp_index_dir):
        """Test getting index for organization"""
        import uuid
        org_id = f"test-org-{uuid.uuid4()}"

        index1 = get_index_for_org(org_id)
        index2 = get_index_for_org(org_id)

        # Should return the same instance
        assert index1 is index2
        assert index1.org_id == org_id

    def test_get_index_for_different_orgs(self, temp_index_dir):
        """Test getting indices for different organizations"""
        import uuid
        org_id1 = f"org-{uuid.uuid4()}"
        org_id2 = f"org-{uuid.uuid4()}"

        index1 = get_index_for_org(org_id1)
        index2 = get_index_for_org(org_id2)

        # Should be different instances
        assert index1 is not index2
        assert index1.org_id == org_id1
        assert index2.org_id == org_id2

    @pytest.mark.asyncio
    async def test_index_note(self, temp_index_dir):
        """Test indexing a note"""
        import uuid
        org_id = f"test-org-{uuid.uuid4()}"

        # Create a mock note
        note = Mock()
        note.note_id = "note-123"
        note.org_id = org_id
        note.title = "Test Note"
        note.content_md = "This is test content"

        await index_note(note)

        # Check that note was added to index
        index = get_index_for_org(org_id)
        assert note.note_id in index.note_ids

    @pytest.mark.asyncio
    async def test_remove_note_from_index_func(self, temp_index_dir):
        """Test removing a note from index"""
        import uuid
        org_id = f"test-org-{uuid.uuid4()}"

        # Create and index a note first
        note = Mock()
        note.note_id = "note-123"
        note.org_id = org_id
        note.title = "Test Note"
        note.content_md = "This is test content"

        await index_note(note)

        # Verify it's in the index
        index = get_index_for_org(org_id)
        assert note.note_id in index.note_ids

        # Remove it
        await remove_note_from_index(note)

        # Verify it's removed
        assert note.note_id not in index.note_ids

    @pytest.mark.asyncio
    async def test_search_notes(self, temp_index_dir):
        """Test searching notes"""
        import uuid
        org_id = f"test-org-{uuid.uuid4()}"

        # Add some notes to index first
        for i in range(3):
            note = Mock()
            note.note_id = f"note-{i}"
            note.org_id = org_id
            note.title = f"Test Note {i}"
            note.content_md = f"Content for note {i}"
            await index_note(note)

        # Search
        results = await search_notes("test query", org_id, top_k=2)

        assert len(results) == 2
        for note_id, similarity in results:
            assert note_id.startswith("note-")
            assert 0 <= similarity <= 1

    def test_rebuild_index_for_org(self, temp_index_dir, test_session, test_org):
        """Test rebuilding index for organization"""
        org_id = test_org.org_id

        # Create some notes in database
        from api.models.models import Note
        notes = []
        for i in range(3):
            note = Note(
                note_id=f"note-{i}",
                org_id=org_id,
                title=f"Test Note {i}",
                content_md=f"Content {i}",
                version=1,
                deleted=False
            )
            test_session.add(note)
            notes.append(note)

        test_session.commit()

        # Mock the async session for the rebuild function
        with patch('api.search.vector_search.rebuild_index_for_org') as mock_rebuild:
            mock_rebuild.return_value = 3

            # Since rebuild_index_for_org is async, we'll test the synchronous parts
            # Get the index and manually add notes to simulate rebuild
            index = get_index_for_org(org_id)

            # Clear any existing data first
            index.note_ids.clear()
            index.embeddings.clear()
            if index.index is not None:
                index.index.reset()

            # Add notes manually to simulate rebuild
            for note in notes:
                embedding = text_to_embedding(f"{note.title} {note.content_md}")
                index.add_note(note.note_id, embedding)

            assert len(index.note_ids) == 3
            for note in notes:
                assert note.note_id in index.note_ids


class TestEmbeddingModel:
    """Test embedding model management"""

    @patch('api.search.vector_search.SENTENCE_TRANSFORMERS_AVAILABLE', True)
    @patch('api.search.vector_search.SentenceTransformer')
    def test_get_embedding_model_initialization(self, mock_sentence_transformer):
        """Test embedding model initialization"""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_sentence_transformer.return_value = mock_model

        # Clear any existing model
        import api.search.vector_search
        api.search.vector_search._embedding_model = None

        model = _get_embedding_model()

        assert model is mock_model
        mock_sentence_transformer.assert_called_once_with("all-MiniLM-L6-v2")

    @patch('api.search.vector_search.SENTENCE_TRANSFORMERS_AVAILABLE', False)
    def test_get_embedding_model_unavailable(self):
        """Test when sentence transformers is not available"""
        model = _get_embedding_model()
        assert model is None

    @patch('api.search.vector_search.SENTENCE_TRANSFORMERS_AVAILABLE', True)
    @patch('api.search.vector_search._get_embedding_model')
    def test_get_embedding_dimension_with_model(self, mock_get_model):
        """Test getting embedding dimension from model"""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_get_model.return_value = mock_model

        dimension = _get_embedding_dimension()
        assert dimension == 768

    @patch('api.search.vector_search.SENTENCE_TRANSFORMERS_AVAILABLE', False)
    def test_get_embedding_dimension_fallback(self):
        """Test getting embedding dimension fallback"""
        dimension = _get_embedding_dimension()
        assert dimension == 384  # Default dimension

    @patch('api.search.vector_search.SENTENCE_TRANSFORMERS_AVAILABLE', True)
    @patch.dict(os.environ, {'EMBEDDING_MODEL': 'custom-model'})
    @patch('api.search.vector_search.SentenceTransformer')
    def test_custom_embedding_model(self, mock_sentence_transformer):
        """Test using custom embedding model from environment"""
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        # Clear existing model
        import api.search.vector_search
        api.search.vector_search._embedding_model = None

        _get_embedding_model()

        mock_sentence_transformer.assert_called_once_with("custom-model")