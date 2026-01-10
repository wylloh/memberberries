"""
Backend abstraction for Memberberries storage.

Defines the protocol that all storage backends must implement.
"""

from typing import Protocol, List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Berry:
    """A single memory item."""
    id: str
    tags: List[str]
    summary: str
    created: str
    type: Optional[str] = None  # gotcha, preference, decision, pattern, rule, architecture
    archived: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d = {
            'id': self.id,
            'tags': self.tags,
            'summary': self.summary,
            'created': self.created,
        }
        if self.type:
            d['type'] = self.type
        if self.archived:
            d['archived'] = self.archived
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Berry':
        """Create Berry from dictionary."""
        return cls(
            id=d['id'],
            tags=d.get('tags', []),
            summary=d.get('summary', ''),
            created=d.get('created', ''),
            type=d.get('type'),
            archived=d.get('archived'),
        )


@dataclass
class Checkpoint:
    """An autoberry checkpoint."""
    content: str
    timestamp: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return {
            'content': self.content,
            'timestamp': self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> 'Checkpoint':
        """Create Checkpoint from dictionary."""
        return cls(
            content=d.get('content', ''),
            timestamp=d.get('timestamp', ''),
        )


@dataclass
class SearchResult:
    """A search result with relevance score."""
    berry: Berry
    score: float  # 0.0 to 1.0, higher is more relevant
    source: str = "active"  # "active" or "archive"


class MemoryBackend(Protocol):
    """Protocol for berry storage backends.

    All backends must implement these methods. The protocol allows for:
    - Simple JSON storage (current default)
    - Semantic search backends (sentence-transformers + numpy)
    - Future backends (SQLite, vector DBs, etc.)
    """

    def load_active(self) -> List[Berry]:
        """Load all active (non-archived) berries."""
        ...

    def save_berry(self, berry: Berry) -> str:
        """Store a new berry. Returns the berry ID.

        Implementations should deduplicate by summary text.
        """
        ...

    def archive(self, berry_id: str) -> bool:
        """Move a berry to archive by its primary tag.

        Returns True if archived, False if not found.
        """
        ...

    def load_archived(self, tag: str) -> List[Berry]:
        """Load all berries archived under a specific tag."""
        ...

    def get_archive_summary(self) -> Dict[str, int]:
        """Get count of archived berries by tag."""
        ...

    def search(self, query: str, k: int = 5) -> List[SearchResult]:
        """Search berries by query.

        For JSON backend: keyword search
        For semantic backend: embedding similarity search

        Returns up to k results, sorted by relevance.
        """
        ...

    def get_checkpoint(self) -> Optional[Checkpoint]:
        """Get current autoberry checkpoint."""
        ...

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save autoberry checkpoint (overwrites previous)."""
        ...

    def get_pending_retrieves(self) -> List[str]:
        """Get and clear pending [RETRIEVE] tag requests."""
        ...

    def save_pending_retrieves(self, tags: List[str]) -> None:
        """Save pending [RETRIEVE] tag requests."""
        ...
