"""
JSON file-based backend for Memberberries.

This is the default backend that stores berries as JSON files.
It's simple, human-readable, and requires no external dependencies.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict

from .base import Berry, Checkpoint, SearchResult, MemoryBackend


class JsonBackend(MemoryBackend):
    """JSON file-based storage backend.

    Storage structure:
        .memberberries/
        ├── active.json          # Current berries + checkpoint
        ├── pending_retrieves.json  # Transient retrieval requests
        └── archive/             # Archived berries by primary tag
            ├── gotcha/
            │   └── abc123.json
            └── architecture/
                └── def456.json
    """

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.storage_dir = self.project_path / ".memberberries"
        self.active_file = self.storage_dir / "active.json"
        self.archive_dir = self.storage_dir / "archive"
        self.retrieves_file = self.storage_dir / "pending_retrieves.json"

    def _ensure_dirs(self):
        """Ensure storage directories exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(exist_ok=True)

    def _load_storage(self) -> Dict:
        """Load the active.json storage file.

        Backward compatible: old format was just a list of berries.
        """
        if self.active_file.exists():
            try:
                with open(self.active_file, 'r') as f:
                    data = json.load(f)
                # Backward compat: old format was just a list
                if isinstance(data, list):
                    return {"berries": data, "autoberry": None}
                return data
            except Exception:
                return {"berries": [], "autoberry": None}
        return {"berries": [], "autoberry": None}

    def _save_storage(self, storage: Dict):
        """Save the full storage structure."""
        self._ensure_dirs()
        with open(self.active_file, 'w') as f:
            json.dump(storage, f, indent=2)

    def load_active(self) -> List[Berry]:
        """Load all active berries."""
        storage = self._load_storage()
        return [Berry.from_dict(b) for b in storage.get("berries", [])]

    def save_berry(self, berry: Berry) -> str:
        """Store a new berry. Deduplicates by summary."""
        storage = self._load_storage()
        berries = storage.get("berries", [])

        # Check for duplicate summary
        existing_summaries = {b.get('summary', '') for b in berries}
        if berry.summary in existing_summaries:
            return berry.id  # Already exists, skip

        berries.append(berry.to_dict())
        storage["berries"] = berries
        self._save_storage(storage)
        return berry.id

    def archive(self, berry_id: str) -> bool:
        """Move a berry to archive by primary tag."""
        storage = self._load_storage()
        berries = storage.get("berries", [])

        # Find the berry
        berry_dict = None
        for b in berries:
            if b.get('id') == berry_id:
                berry_dict = b
                break

        if not berry_dict:
            return False

        # Get primary tag for archive folder
        tags = berry_dict.get('tags', [])
        if not tags:
            return False

        primary_tag = tags[0]

        # Create archive directory
        tag_dir = self.archive_dir / primary_tag
        tag_dir.mkdir(parents=True, exist_ok=True)

        # Add archived timestamp
        berry_dict['archived'] = datetime.now().isoformat()

        # Write to archive
        archive_file = tag_dir / f"{berry_id}.json"
        with open(archive_file, 'w') as f:
            json.dump(berry_dict, f, indent=2)

        # Remove from active
        storage["berries"] = [b for b in berries if b.get('id') != berry_id]
        self._save_storage(storage)

        return True

    def load_archived(self, tag: str) -> List[Berry]:
        """Load all berries archived under a tag."""
        tag_dir = self.archive_dir / tag
        if not tag_dir.exists():
            return []

        berries = []
        for berry_file in tag_dir.glob("*.json"):
            try:
                with open(berry_file, 'r') as f:
                    berries.append(Berry.from_dict(json.load(f)))
            except Exception:
                continue
        return berries

    def get_archive_summary(self) -> Dict[str, int]:
        """Get count of archived berries by tag."""
        if not self.archive_dir.exists():
            return {}

        summary = {}
        for tag_dir in self.archive_dir.iterdir():
            if tag_dir.is_dir():
                count = len(list(tag_dir.glob("*.json")))
                if count > 0:
                    summary[tag_dir.name] = count
        return summary

    def search(self, query: str, k: int = 5) -> List[SearchResult]:
        """Simple keyword search across berries.

        For JSON backend, this does case-insensitive substring matching.
        """
        results = []
        query_lower = query.lower()
        query_words = set(re.findall(r'\w+', query_lower))

        # Search active berries
        for berry in self.load_active():
            score = self._keyword_score(berry, query_lower, query_words)
            if score > 0:
                results.append(SearchResult(berry=berry, score=score, source="active"))

        # Search archived berries
        for tag in self.get_archive_summary().keys():
            for berry in self.load_archived(tag):
                score = self._keyword_score(berry, query_lower, query_words)
                if score > 0:
                    results.append(SearchResult(berry=berry, score=score, source="archive"))

        # Sort by score descending, take top k
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:k]

    def _keyword_score(self, berry: Berry, query_lower: str, query_words: set) -> float:
        """Calculate keyword match score for a berry."""
        text = f"{berry.summary} {' '.join(berry.tags)}".lower()
        text_words = set(re.findall(r'\w+', text))

        # Exact substring match gets highest score
        if query_lower in text:
            return 1.0

        # Word overlap score
        overlap = len(query_words & text_words)
        if overlap == 0:
            return 0.0

        return overlap / len(query_words)

    def get_checkpoint(self) -> Optional[Checkpoint]:
        """Get current autoberry checkpoint."""
        storage = self._load_storage()
        autoberry = storage.get("autoberry")
        if autoberry:
            return Checkpoint.from_dict(autoberry)
        return None

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save autoberry checkpoint."""
        storage = self._load_storage()
        storage["autoberry"] = checkpoint.to_dict()
        self._save_storage(storage)

    def get_pending_retrieves(self) -> List[str]:
        """Get and clear pending retrieve requests."""
        if self.retrieves_file.exists():
            try:
                with open(self.retrieves_file, 'r') as f:
                    tags = json.load(f)
                # Clear after reading
                self.retrieves_file.unlink()
                return tags
            except Exception:
                return []
        return []

    def save_pending_retrieves(self, tags: List[str]) -> None:
        """Save pending retrieve requests."""
        self._ensure_dirs()
        with open(self.retrieves_file, 'w') as f:
            json.dump(tags, f)
