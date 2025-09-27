import numpy as np
import os
import pickle
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import threading
import re
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.models.models import Note

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Directory to store index files
INDEX_DIR = os.getenv("INDEX_DIR", "./indices")
os.makedirs(INDEX_DIR, exist_ok=True)

# Try to import FAISS, fall back to simple search if not available
try:
    import faiss

    FAISS_AVAILABLE = True
except ImportError:
    logger.warning(
        "FAISS not available. Using simple search instead. Install FAISS for better performance."
    )
    FAISS_AVAILABLE = False

# Try to import sentence transformers for advanced embeddings
try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
    # Global model instance for reuse
    _embedding_model: Optional[SentenceTransformer] = None
    _model_lock = threading.Lock()
except ImportError:
    logger.warning(
        "sentence-transformers not available. Using simple hash-based embeddings."
    )
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    # Use Any for type hints when SentenceTransformer is not available
    from typing import Any
    SentenceTransformer = Any
    _embedding_model = None
    _model_lock = threading.Lock()


class NoteVectorIndex:
    """Vector index for notes using FAISS if available, otherwise simple search"""

    def __init__(self, org_id: str, dimension: Optional[int] = None):
        self.org_id = org_id
        # Get dimension from embedding model or use default
        if dimension is None:
            dimension = _get_embedding_dimension()
        self.dimension = dimension
        self.note_ids: List[str] = []
        self.embeddings: List[np.ndarray] = []
        self.last_updated = datetime.now()
        self.lock = threading.RLock()

        # Create FAISS index if available
        if FAISS_AVAILABLE:
            self.index = faiss.IndexFlatL2(self.dimension)  # L2 distance
        else:
            self.index = None

        # Try to load existing index
        self._load_index()

    def _get_index_path(self) -> str:
        """Get the path to the index file"""
        return os.path.join(INDEX_DIR, f"index_{self.org_id}.pkl")

    def _load_index(self) -> None:
        """Load index from disk if it exists"""
        index_path = self._get_index_path()
        if os.path.exists(index_path):
            try:
                with open(index_path, "rb") as f:
                    data = pickle.load(f)
                    if FAISS_AVAILABLE:
                        saved_index = data.get("index")
                        if saved_index is not None:
                            self.index = saved_index
                        # If saved index is None but FAISS is now available,
                        # keep the new FAISS index we created in __init__
                    self.note_ids = data.get("note_ids", [])
                    self.embeddings = data.get("embeddings", [])
                    self.last_updated = data.get("last_updated", datetime.now())
                    logger.info(
                        f"Loaded index for org {self.org_id} with {len(self.note_ids)} notes"
                    )

                    # If FAISS is available but we loaded a None index, rebuild from embeddings
                    if FAISS_AVAILABLE and saved_index is None and len(self.embeddings) > 0:
                        logger.info(f"Rebuilding FAISS index from {len(self.embeddings)} stored embeddings")
                        for i, embedding in enumerate(self.embeddings):
                            if i < len(self.note_ids):
                                self.index.add(np.array([embedding]))
            except Exception as e:
                logger.error(f"Error loading index: {e}")

    def _save_index(self) -> None:
        """Save index to disk"""
        index_path = self._get_index_path()
        try:
            with open(index_path, "wb") as f:
                pickle.dump(
                    {
                        "index": self.index if FAISS_AVAILABLE else None,
                        "note_ids": self.note_ids,
                        "embeddings": self.embeddings,
                        "last_updated": self.last_updated,
                    },
                    f,
                )
            logger.info(
                f"Saved index for org {self.org_id} with {len(self.note_ids)} notes"
            )
        except Exception as e:
            logger.error(f"Error saving index: {e}")

    def add_note(self, note_id: str, embedding: np.ndarray) -> None:
        """Add a note to the index"""
        with self.lock:
            if note_id in self.note_ids:
                # Remove existing note
                idx = self.note_ids.index(note_id)
                self._remove_at_index(idx)

            # Add new embedding
            embedding_normalized = self._normalize_embedding(embedding)

            if FAISS_AVAILABLE:
                self.index.add(np.array([embedding_normalized]))

            self.note_ids.append(note_id)
            self.embeddings.append(embedding_normalized)
            self.last_updated = datetime.now()

            # Save index
            self._save_index()

    def remove_note(self, note_id: str) -> None:
        """Remove a note from the index"""
        with self.lock:
            if note_id in self.note_ids:
                idx = self.note_ids.index(note_id)
                self._remove_at_index(idx)
                self.last_updated = datetime.now()

                # Save index
                self._save_index()

    def _remove_at_index(self, idx: int) -> None:
        """Remove a note at the specified index"""
        if FAISS_AVAILABLE:
            # Create a new index without the removed note
            new_index = faiss.IndexFlatL2(self.dimension)

            # Get all vectors
            all_vectors = self.index.reconstruct_n(0, self.index.ntotal)

            # Add all vectors except the one to remove
            vectors_to_keep = np.delete(all_vectors, idx, axis=0)
            if len(vectors_to_keep) > 0:
                new_index.add(vectors_to_keep)

            # Replace index
            self.index = new_index

        # Remove from lists
        del self.note_ids[idx]
        if len(self.embeddings) > idx:
            del self.embeddings[idx]

    def search(
        self, query_embedding: np.ndarray, top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Search for similar notes"""
        with self.lock:
            if len(self.note_ids) == 0:
                return []

            # Normalize query embedding
            query_embedding = self._normalize_embedding(query_embedding)

            if FAISS_AVAILABLE:
                # Search with FAISS
                distances, indices = self.index.search(
                    np.array([query_embedding]), min(top_k, len(self.note_ids))
                )

                # Return results
                results = []
                for i, idx in enumerate(indices[0]):
                    if idx < len(self.note_ids) and idx >= 0:
                        note_id = self.note_ids[idx]
                        distance = distances[0][i]
                        # Convert distance to similarity score (1 - normalized distance)
                        similarity = 1.0 - min(
                            distance / 2.0, 1.0
                        )  # Normalize to [0, 1]
                        results.append((note_id, similarity))

                return results
            else:
                # Simple search using dot product similarity
                similarities = []
                for i, embedding in enumerate(self.embeddings):
                    if i < len(self.note_ids):
                        # Compute dot product similarity
                        similarity = np.dot(query_embedding, embedding)
                        similarities.append((self.note_ids[i], similarity))

                # Sort by similarity (descending)
                similarities.sort(key=lambda x: x[1], reverse=True)

                # Return top k
                return similarities[:top_k]

    def _normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """Normalize embedding vector"""
        norm = np.linalg.norm(embedding)
        if norm > 0:
            return embedding / norm
        return embedding


# Global index registry
index_registry: Dict[str, NoteVectorIndex] = {}
registry_lock = threading.RLock()


def get_index_for_org(org_id: str) -> NoteVectorIndex:
    """Get or create an index for an organization"""
    with registry_lock:
        if org_id not in index_registry:
            index_registry[org_id] = NoteVectorIndex(org_id)
        return index_registry[org_id]


def _get_embedding_model() -> Optional[SentenceTransformer]:
    """Get or initialize the embedding model (thread-safe)"""
    global _embedding_model

    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        return None

    if _embedding_model is None:
        with _model_lock:
            if _embedding_model is None:  # Double-check pattern
                try:
                    # Use a lightweight, fast model optimized for semantic search
                    model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
                    logger.info(f"Loading embedding model: {model_name}")
                    _embedding_model = SentenceTransformer(model_name)
                    logger.info(f"Embedding model loaded successfully. Dimension: {_embedding_model.get_sentence_embedding_dimension()}")
                except Exception as e:
                    logger.error(f"Failed to load embedding model: {e}")
                    return None

    return _embedding_model


def _get_embedding_dimension() -> int:
    """Get the dimension of embeddings from the model"""
    model = _get_embedding_model()
    if model is not None:
        return model.get_sentence_embedding_dimension()
    return 384  # Default dimension for hash-based embeddings


def text_to_embedding(text: str) -> np.ndarray:
    """
    Convert text to embedding vector using sentence transformers or hash-based fallback
    """
    if SENTENCE_TRANSFORMERS_AVAILABLE:
        model = _get_embedding_model()
        if model is not None:
            try:
                # Clean and prepare text
                cleaned_text = text.strip()
                if not cleaned_text:
                    cleaned_text = "empty"

                # Generate embedding using sentence transformer
                embedding = model.encode(cleaned_text, normalize_embeddings=True)
                return embedding.astype(np.float32)

            except Exception as e:
                logger.error(f"Error generating embedding with sentence transformer: {e}")
                # Fall through to hash-based approach

    # Fallback to hash-based embedding (original implementation)
    logger.debug("Using hash-based embedding fallback")
    hash_value = abs(hash(text)) % (2**32 - 1)  # Ensure positive value within range
    rng = np.random.RandomState(hash_value)
    embedding = rng.randn(384)  # 384-dimensional embedding
    return (embedding / np.linalg.norm(embedding)).astype(np.float32)  # Normalize


async def index_note(note: Note) -> None:
    """Index a note for search"""
    # Generate embedding from note content
    text = f"{note.title}\n\n{note.content_md}"
    embedding = text_to_embedding(text)

    # Add to index
    index = get_index_for_org(note.org_id)
    index.add_note(note.note_id, embedding)


async def remove_note_from_index(note: Note) -> None:
    """Remove a note from the search index"""
    index = get_index_for_org(note.org_id)
    index.remove_note(note.note_id)


async def search_notes(
    query: str, org_id: str, top_k: int = 10, db: AsyncSession = None
) -> List[Tuple[str, float]]:
    """Search for notes matching the query"""
    # Generate query embedding
    query_embedding = text_to_embedding(query)

    # Get index for organization
    index = get_index_for_org(org_id)

    # Search
    results = index.search(query_embedding, top_k)

    return results


async def rebuild_index_for_org(org_id: str, db: AsyncSession) -> int:
    """Rebuild the search index for an organization"""
    # Get all notes for the org
    result = await db.execute(
        select(Note).where(Note.org_id == org_id, Note.deleted == False)
    )
    notes = result.scalars().all()

    # Get or create index
    index = get_index_for_org(org_id)

    # Clear existing index
    index.note_ids = []
    index.embeddings = []
    if FAISS_AVAILABLE:
        index.index = faiss.IndexFlatL2(index.dimension)

    # Add notes to index
    count = 0
    for note in notes:
        try:
            # Generate embedding
            content = f"{note.title}\n\n{note.content_md}"
            embedding = text_to_embedding(content)

            # Add to index
            index.add_note(note.note_id, embedding)
            count += 1
        except Exception as e:
            logger.error(f"Error indexing note {note.note_id}: {e}")

    # Save index
    index._save_index()

    return count
