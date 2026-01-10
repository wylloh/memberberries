"""
Semantic search backend for Memberberries.

Wraps the JSON backend and adds embedding-based similarity search.
Uses sentence-transformers for embeddings and numpy for similarity.

This backend is opt-in and requires:
    pip install sentence-transformers

At memberberries scale (hundreds of items), brute-force cosine similarity
is sub-millisecond. No need for approximate nearest neighbor indexes.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Optional, Dict

from .base import Berry, Checkpoint, SearchResult, MemoryBackend
from .json_backend import JsonBackend


# Check if sentence-transformers is available
try:
    from sentence_transformers import SentenceTransformer
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False


class SemanticBackend(MemoryBackend):
    """Semantic search backend using sentence-transformers.

    This backend wraps JsonBackend for storage and adds:
    - Embedding generation for berries
    - Cosine similarity search
    - Automatic embedding updates on save/archive

    Storage:
        .memberberries/
        ├── active.json          # Berries (via JsonBackend)
        ├── embeddings.json      # Cached embeddings
        └── archive/             # Archives (via JsonBackend)
    """

    # Default model: small, fast, good quality
    DEFAULT_MODEL = 'all-MiniLM-L6-v2'

    def __init__(self, project_path: Path, model_name: str = None):
        if not SEMANTIC_AVAILABLE:
            raise ImportError(
                "sentence-transformers is required for semantic search. "
                "Install with: pip install sentence-transformers"
            )

        self.project_path = Path(project_path)
        self.json_backend = JsonBackend(project_path)
        self.embeddings_file = self.project_path / ".memberberries" / "embeddings.json"

        # Lazy load model
        self._model = None
        self._model_name = model_name or self.DEFAULT_MODEL

        # Cache embeddings in memory
        self._embeddings_cache: Dict[str, List[float]] = {}
        self._load_embeddings_cache()

    @property
    def model(self) -> 'SentenceTransformer':
        """Lazy load the embedding model."""
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def _load_embeddings_cache(self):
        """Load cached embeddings from disk."""
        if self.embeddings_file.exists():
            try:
                with open(self.embeddings_file, 'r') as f:
                    self._embeddings_cache = json.load(f)
            except Exception:
                self._embeddings_cache = {}

    def _save_embeddings_cache(self):
        """Save embeddings cache to disk."""
        self.json_backend._ensure_dirs()
        with open(self.embeddings_file, 'w') as f:
            json.dump(self._embeddings_cache, f)

    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text, using cache if available."""
        # Use text hash as cache key
        import hashlib
        cache_key = hashlib.md5(text.encode()).hexdigest()

        if cache_key in self._embeddings_cache:
            return np.array(self._embeddings_cache[cache_key])

        # Generate embedding
        embedding = self.model.encode(text, convert_to_numpy=True)
        self._embeddings_cache[cache_key] = embedding.tolist()
        self._save_embeddings_cache()

        return embedding

    def _berry_text(self, berry: Berry) -> str:
        """Get searchable text for a berry."""
        parts = [berry.summary]
        if berry.tags:
            parts.extend(berry.tags)
        if berry.type:
            parts.append(berry.type)
        return ' '.join(parts)

    # Delegate most operations to JSON backend

    def load_active(self) -> List[Berry]:
        return self.json_backend.load_active()

    def save_berry(self, berry: Berry) -> str:
        result = self.json_backend.save_berry(berry)
        # Pre-compute embedding for new berry
        self._get_embedding(self._berry_text(berry))
        return result

    def archive(self, berry_id: str) -> bool:
        return self.json_backend.archive(berry_id)

    def load_archived(self, tag: str) -> List[Berry]:
        return self.json_backend.load_archived(tag)

    def get_archive_summary(self) -> Dict[str, int]:
        return self.json_backend.get_archive_summary()

    def get_checkpoint(self) -> Optional[Checkpoint]:
        return self.json_backend.get_checkpoint()

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        return self.json_backend.save_checkpoint(checkpoint)

    def get_pending_retrieves(self) -> List[str]:
        return self.json_backend.get_pending_retrieves()

    def save_pending_retrieves(self, tags: List[str]) -> None:
        return self.json_backend.save_pending_retrieves(tags)

    # Semantic search - the key differentiator

    def search(self, query: str, k: int = 5) -> List[SearchResult]:
        """Semantic similarity search across all berries.

        Uses cosine similarity between query embedding and berry embeddings.
        Falls back to keyword search if embeddings fail.
        """
        try:
            return self._semantic_search(query, k)
        except Exception:
            # Fall back to keyword search
            return self.json_backend.search(query, k)

    def _semantic_search(self, query: str, k: int) -> List[SearchResult]:
        """Perform semantic similarity search."""
        # Get query embedding
        query_embedding = self._get_embedding(query)

        results = []

        # Search active berries
        for berry in self.load_active():
            text = self._berry_text(berry)
            berry_embedding = self._get_embedding(text)
            score = self._cosine_similarity(query_embedding, berry_embedding)
            results.append(SearchResult(berry=berry, score=score, source="active"))

        # Search archived berries
        for tag in self.get_archive_summary().keys():
            for berry in self.load_archived(tag):
                text = self._berry_text(berry)
                berry_embedding = self._get_embedding(text)
                score = self._cosine_similarity(query_embedding, berry_embedding)
                results.append(SearchResult(berry=berry, score=score, source="archive"))

        # Sort by score descending, take top k
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:k]

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
