#!/usr/bin/env python3
"""
🫐 Memberberries Berry Manager

Member when Claude Code had no memory? We memberberry!
A lightweight berry storage system for persisting and juicing context across sessions.
"""

import os
import re
import json
import hashlib
import stat
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np


# Patterns that might indicate sensitive data
SENSITIVE_PATTERNS = [
    # API keys and tokens
    (r'api[_-]?key', 'API key'),
    (r'api[_-]?secret', 'API secret'),
    (r'auth[_-]?token', 'Auth token'),
    (r'access[_-]?token', 'Access token'),
    (r'bearer\s+\S+', 'Bearer token'),
    # Secrets and passwords
    (r'password', 'Password'),
    (r'passwd', 'Password'),
    (r'secret', 'Secret'),
    (r'private[_-]?key', 'Private key'),
    # Common token patterns
    (r'sk-[a-zA-Z0-9]{20,}', 'OpenAI API key'),
    (r'ghp_[a-zA-Z0-9]{36}', 'GitHub token'),
    (r'gho_[a-zA-Z0-9]{36}', 'GitHub OAuth token'),
    (r'xox[baprs]-[a-zA-Z0-9-]+', 'Slack token'),
    (r'AKIA[A-Z0-9]{16}', 'AWS access key'),
    # Credentials
    (r'credential', 'Credential'),
    (r'auth[_-]?key', 'Auth key'),
]


class BerryManager:
    """Manages memberberries for Claude Code sessions."""

    def __init__(self, base_path: str = None, storage_mode: str = 'auto',
                 project_path: str = None):
        """Initialize the berry manager.

        Args:
            base_path: Base directory for berry storage. Defaults to ~/.memberberries
            storage_mode: 'auto' (check for local first), 'global', or 'local'
            project_path: Project path for local storage mode
        """
        self.storage_mode = storage_mode
        self.project_path = project_path
        self.base_path = self._resolve_storage_path(base_path, storage_mode, project_path)

        # Original memory types
        self.preferences_path = self.base_path / "preferences"
        self.projects_path = self.base_path / "projects"
        self.solutions_path = self.base_path / "solutions"
        self.sessions_path = self.base_path / "sessions"

        # New memory types
        self.errors_path = self.base_path / "errors"
        self.antipatterns_path = self.base_path / "antipatterns"
        self.git_conventions_path = self.base_path / "git_conventions"
        self.dependencies_path = self.base_path / "dependencies"
        self.testing_path = self.base_path / "testing"
        self.environment_path = self.base_path / "environment"
        self.api_notes_path = self.base_path / "api_notes"
        self.pinned_path = self.base_path / "pinned"  # Protected memories

        # Create directories if they don't exist
        all_paths = [
            self.preferences_path, self.projects_path,
            self.solutions_path, self.sessions_path,
            self.errors_path, self.antipatterns_path,
            self.git_conventions_path, self.dependencies_path,
            self.testing_path, self.environment_path, self.api_notes_path,
            self.pinned_path
        ]
        for path in all_paths:
            path.mkdir(parents=True, exist_ok=True)

        # Load or create berry index
        self.index_path = self.base_path / "berry_index.json"
        self.index = self._load_index()

    def _resolve_storage_path(self, base_path: str, storage_mode: str,
                              project_path: str) -> Path:
        """Resolve the storage path based on storage mode.

        Args:
            base_path: Explicit base path if provided
            storage_mode: 'auto', 'global', or 'local'
            project_path: Project path for local storage

        Returns:
            Resolved Path for storage
        """
        # If explicit base_path provided, use it
        if base_path is not None:
            return Path(base_path)

        global_path = Path(os.path.expanduser("~/.memberberries"))

        if storage_mode == 'global':
            return global_path

        if storage_mode == 'local':
            if project_path:
                return Path(project_path) / ".memberberries"
            else:
                # Use current working directory
                return Path.cwd() / ".memberberries"

        # Auto mode: check for local .memberberries first
        if storage_mode == 'auto':
            if project_path:
                local_path = Path(project_path) / ".memberberries"
                if local_path.exists():
                    return local_path
            # Check current directory
            cwd_local = Path.cwd() / ".memberberries"
            if cwd_local.exists():
                return cwd_local
            # Fall back to global
            return global_path

        return global_path
    
    def _load_index(self) -> Dict:
        """Load the memory index or create a new one."""
        default_index = {
            "preferences": [],
            "projects": {},
            "solutions": [],
            "sessions": [],
            # New memory types
            "errors": [],
            "antipatterns": [],
            "git_conventions": [],
            "dependencies": {},  # Keyed by package name
            "testing": [],
            "environment": {},  # Keyed by env_type
            "api_notes": [],
            # Protected memories that are never auto-deleted
            "pinned": [],  # List of {id, name, content, category, tags, timestamp}
            # Adaptive learning - tracks user-specific signal words
            "learned_signals": {
                "emphasis": {},     # word -> count (words used with emphasis)
                "repeated": {},     # word -> count (words that appear often)
                "effective": []     # signals that led to successful captures
            },
            # Gravitational task clustering - memories orbit around task centers
            "task_clusters": {},  # task_id -> {name, mass, memories: [memory_ids]}
            "memory_gravity": {}  # memory_id -> {mass, references, last_accessed}
        }

        if self.index_path.exists():
            try:
                with open(self.index_path, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults to handle upgrades
                    for key in default_index:
                        if key not in loaded:
                            loaded[key] = default_index[key]
                    return loaded
            except json.JSONDecodeError as e:
                # Index is corrupted - try to recover from backup
                print(f"⚠️  Memory index corrupted at line {e.lineno}. Attempting recovery...")
                return self._recover_from_backup(default_index)
        return default_index

    def _recover_from_backup(self, default_index: Dict) -> Dict:
        """Attempt to recover index from backup files."""
        backup_files = [
            self.index_path.with_suffix('.json.bak'),
            self.index_path.with_suffix('.json.bak2'),
        ]

        for backup_path in backup_files:
            if backup_path.exists():
                try:
                    with open(backup_path, 'r') as f:
                        loaded = json.load(f)
                    print(f"✅ Recovered from backup: {backup_path.name}")

                    # Move corrupted file aside
                    corrupted_path = self.index_path.with_suffix('.json.corrupted')
                    try:
                        self.index_path.rename(corrupted_path)
                    except:
                        pass

                    # Merge with defaults
                    for key in default_index:
                        if key not in loaded:
                            loaded[key] = default_index[key]
                    return loaded
                except json.JSONDecodeError:
                    continue  # Try next backup

        # No valid backup found - start fresh
        print("❌ No valid backup found. Starting with fresh memory index.")
        print("   Run 'member report' to help diagnose the issue.")

        # Move corrupted file aside
        try:
            corrupted_path = self.index_path.with_suffix('.json.corrupted')
            self.index_path.rename(corrupted_path)
            print(f"   Corrupted file saved as: {corrupted_path.name}")
        except:
            pass

        return default_index
    
    def _save_index(self):
        """Save the memory index with atomic write and validation.

        Uses atomic write pattern to prevent corruption:
        1. Create backup of existing file
        2. Write to temporary file
        3. Validate the JSON is readable
        4. Atomically rename temp to target
        """
        import tempfile
        import fcntl

        # Sanitize all string content before saving
        self._sanitize_index()

        # Create backup before write (keep last 2 backups)
        if self.index_path.exists():
            backup_path = self.index_path.with_suffix('.json.bak')
            backup_path2 = self.index_path.with_suffix('.json.bak2')
            if backup_path.exists():
                try:
                    if backup_path2.exists():
                        backup_path2.unlink()
                    backup_path.rename(backup_path2)
                except:
                    pass
            try:
                import shutil
                shutil.copy2(self.index_path, backup_path)
            except:
                pass

        # Write to temporary file first
        temp_fd, temp_path = tempfile.mkstemp(
            suffix='.json',
            prefix='berry_index_',
            dir=self.base_path
        )
        temp_path = Path(temp_path)

        try:
            # Write with file locking to prevent concurrent writes
            with os.fdopen(temp_fd, 'w') as f:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except (IOError, OSError):
                    # Could not acquire lock - another process is writing
                    # Wait briefly and retry
                    import time
                    time.sleep(0.1)
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)

                json.dump(self.index, f, indent=2, ensure_ascii=True)
                f.flush()
                os.fsync(f.fileno())

            # Validate the written JSON is readable
            with open(temp_path, 'r') as f:
                json.load(f)  # Will raise if invalid

            # Atomic rename (on POSIX systems)
            temp_path.rename(self.index_path)
            self._set_file_permissions(self.index_path)

        except Exception as e:
            # Clean up temp file on failure
            try:
                temp_path.unlink()
            except:
                pass
            raise RuntimeError(f"Failed to save index: {e}")

    def _sanitize_index(self):
        """Sanitize all string content in the index to prevent JSON corruption."""
        def sanitize_string(s):
            if not isinstance(s, str):
                return s
            # Remove control characters except newlines and tabs
            import re
            s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', s)
            # Limit string length to prevent massive entries
            if len(s) > 10000:
                s = s[:10000] + '...[truncated]'
            return s

        def sanitize_dict(d):
            if isinstance(d, dict):
                return {k: sanitize_dict(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [sanitize_dict(item) for item in d]
            elif isinstance(d, str):
                return sanitize_string(d)
            else:
                return d

        # Sanitize the entire index
        for key in self.index:
            self.index[key] = sanitize_dict(self.index[key])
    
    def _get_project_hash(self, project_path: str) -> str:
        """Generate a hash for a project path."""
        return hashlib.md5(project_path.encode()).hexdigest()[:12]
    
    def _simple_embedding(self, text: str) -> np.ndarray:
        """Create a simple embedding using character n-grams.
        
        This is a lightweight alternative to heavy ML models.
        For production, consider using sentence-transformers or OpenAI embeddings.
        """
        # Normalize text
        text = text.lower()
        words = text.split()
        
        # Create a simple bag-of-words vector (top 1000 common programming terms)
        # This is very basic - in practice you'd want proper embeddings
        vocab = set(words)
        
        # Use a simple hash-based embedding for demo purposes
        embedding = np.zeros(128)
        for word in vocab:
            hash_val = hash(word) % 128
            embedding[hash_val] += 1
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    # SECURITY HELPERS

    def _check_sensitive_data(self, text: str) -> List[str]:
        """Check if text contains potentially sensitive data.

        Args:
            text: Text to check for sensitive patterns

        Returns:
            List of detected sensitive data types (empty if none found)
        """
        detected = []
        text_lower = text.lower()

        for pattern, description in SENSITIVE_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if description not in detected:
                    detected.append(description)

        return detected

    def _set_file_permissions(self, file_path: Path):
        """Set restrictive file permissions (owner read/write only).

        Args:
            file_path: Path to the file to secure
        """
        try:
            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        except OSError:
            pass  # Silently fail on systems that don't support chmod

    def _secure_write_json(self, file_path: Path, data: Dict):
        """Write JSON data to file with secure permissions.

        Args:
            file_path: Path to write to
            data: Dictionary to serialize as JSON
        """
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        self._set_file_permissions(file_path)

    def _warn_sensitive_data(self, text: str, context: str = "content") -> bool:
        """Check for sensitive data and print warning if found.

        Args:
            text: Text to check
            context: Description of what's being stored (for warning message)

        Returns:
            True if sensitive data was detected, False otherwise
        """
        detected = self._check_sensitive_data(text)
        if detected:
            print(f"⚠️  Warning: Potentially sensitive data detected in {context}:")
            for item in detected:
                print(f"   - {item}")
            print("   Data will still be stored. Use --force to suppress this warning.")
            return True
        return False

    # PREFERENCE MANAGEMENT
    
    def add_preference(self, category: str, content: str, tags: List[str] = None):
        """Add a user preference.
        
        Args:
            category: Category of preference (e.g., 'coding_style', 'tools')
            content: The actual preference content
            tags: Optional tags for better retrieval
        """
        pref_file = self.preferences_path / f"{category}.md"
        timestamp = datetime.now().isoformat()
        
        entry = {
            "category": category,
            "content": content,
            "tags": tags or [],
            "timestamp": timestamp,
            "embedding": self._simple_embedding(content).tolist()
        }
        
        # Append to category file
        with open(pref_file, 'a') as f:
            f.write(f"\n## {timestamp}\n")
            f.write(f"Tags: {', '.join(tags or [])}\n\n")
            f.write(f"{content}\n")
        
        # Update index
        self.index["preferences"].append(entry)
        self._save_index()
        
        return entry
    
    def get_preferences(self, query: str = None, top_k: int = 5) -> List[Dict]:
        """Retrieve preferences, optionally filtered by semantic similarity.
        
        Args:
            query: Optional query to find relevant preferences
            top_k: Number of top results to return
        """
        if not query:
            return self.index["preferences"][-top_k:]
        
        query_embedding = self._simple_embedding(query)
        scored_prefs = []
        
        for pref in self.index["preferences"]:
            pref_embedding = np.array(pref["embedding"])
            similarity = self._cosine_similarity(query_embedding, pref_embedding)
            scored_prefs.append((similarity, pref))
        
        # Sort by similarity and return top_k
        scored_prefs.sort(reverse=True, key=lambda x: x[0])
        return [pref for _, pref in scored_prefs[:top_k]]
    
    # PROJECT CONTEXT MANAGEMENT
    
    def add_project_context(self, project_path: str, context: Dict):
        """Add or update context for a specific project.
        
        Args:
            project_path: Path to the project
            context: Dictionary containing project context (architecture, conventions, etc.)
        """
        project_hash = self._get_project_hash(project_path)
        project_dir = self.projects_path / project_hash
        project_dir.mkdir(exist_ok=True)
        
        context_file = project_dir / "context.json"
        
        # Add metadata
        context["project_path"] = project_path
        context["last_updated"] = datetime.now().isoformat()
        
        # Save context
        with open(context_file, 'w') as f:
            json.dump(context, f, indent=2)
        
        # Update index
        self.index["projects"][project_hash] = {
            "path": project_path,
            "last_updated": context["last_updated"]
        }
        self._save_index()
        
        return project_hash
    
    def get_project_context(self, project_path: str) -> Optional[Dict]:
        """Retrieve context for a specific project."""
        project_hash = self._get_project_hash(project_path)
        context_file = self.projects_path / project_hash / "context.json"
        
        if not context_file.exists():
            return None
        
        with open(context_file, 'r') as f:
            return json.load(f)
    
    # SOLUTION MANAGEMENT
    
    def add_solution(self, problem: str, solution: str, tags: List[str] = None, 
                    code_snippet: str = None):
        """Store a solution to a recurring problem.
        
        Args:
            problem: Description of the problem
            solution: The solution or approach
            tags: Tags for categorization
            code_snippet: Optional code example
        """
        timestamp = datetime.now().isoformat()
        solution_id = hashlib.md5(f"{problem}{timestamp}".encode()).hexdigest()[:12]
        
        solution_data = {
            "id": solution_id,
            "problem": problem,
            "solution": solution,
            "tags": tags or [],
            "code_snippet": code_snippet,
            "timestamp": timestamp,
            "embedding": self._simple_embedding(f"{problem} {solution}").tolist()
        }
        
        # Save to file
        solution_file = self.solutions_path / f"{solution_id}.json"
        with open(solution_file, 'w') as f:
            json.dump(solution_data, f, indent=2)
        
        # Update index
        self.index["solutions"].append(solution_data)
        self._save_index()
        
        return solution_data
    
    def search_solutions(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search for relevant solutions using semantic similarity.

        Args:
            query: The problem or query to search for
            top_k: Number of top results to return
        """
        query_embedding = self._simple_embedding(query)
        scored_solutions = []

        for solution in self.index["solutions"]:
            # Skip archived memories
            if solution.get('archived'):
                continue
            solution_embedding = np.array(solution["embedding"])
            similarity = self._cosine_similarity(query_embedding, solution_embedding)
            scored_solutions.append((similarity, solution))

        # Sort by similarity
        scored_solutions.sort(reverse=True, key=lambda x: x[0])
        return [sol for _, sol in scored_solutions[:top_k]]

    def refine_memory(self, memory_id: str, new_content: str) -> bool:
        """Update a memory with refined content.

        This is used when Claude suggests improvements to low-quality memories
        via the self-reflection mechanism.

        Args:
            memory_id: The ID (or prefix) of the memory to refine
            new_content: The improved/refined content

        Returns:
            True if memory was found and updated, False otherwise
        """
        # Search all memory types for the ID
        memory_types = [
            ('solutions', 'problem'),
            ('solutions', 'solution'),
            ('errors', 'error_message'),
            ('errors', 'resolution'),
            ('antipatterns', 'pattern'),
        ]

        for mem_type, content_field in memory_types:
            memories = self.index.get(mem_type, [])
            for mem in memories:
                if mem.get('id', '').startswith(memory_id):
                    # Update the content field
                    if content_field in mem:
                        mem[content_field] = new_content

                    # Mark as refined
                    mem['refined'] = True
                    mem['refined_at'] = datetime.now().isoformat()

                    # Update embedding for the new content
                    full_content = mem.get('problem', '') + mem.get('solution', '') + mem.get('error_message', '') + mem.get('resolution', '')
                    mem['embedding'] = self._simple_embedding(full_content).tolist()

                    self._save_index()
                    return True

        return False

    def get_memories_needing_refinement(self) -> List[Dict]:
        """Get all memories that may need refinement (low quality).

        Returns:
            List of memory dicts with quality issues
        """
        low_quality = []

        for mem_type in ['solutions', 'errors', 'antipatterns']:
            for mem in self.index.get(mem_type, []):
                # Skip already refined memories
                if mem.get('refined'):
                    continue

                # Check for quality issues
                content = mem.get('problem', '') + mem.get('solution', '') + mem.get('error_message', '') + mem.get('resolution', '')

                issues = 0
                if len(content) < 20:
                    issues += 1
                if '→' in content:
                    issues += 1
                if content.count('{') > 2:
                    issues += 1
                if 'stop_reason' in content or 'input_tokens' in content:
                    issues += 2

                if issues >= 2:
                    low_quality.append({
                        'id': mem.get('id', '')[:8],
                        'type': mem_type,
                        'content': content[:100] + '...' if len(content) > 100 else content,
                        'issues': issues
                    })

        return low_quality

    def archive_memory(self, memory_id: str) -> bool:
        """Archive a memory, moving it from active to archived state.

        This is used when Claude decides a memory is no longer relevant
        for the current session. Archived memories are still stored but
        not included in active memory lists.

        Args:
            memory_id: The ID (or 8-char prefix) of the memory to archive

        Returns:
            True if memory was found and archived, False otherwise
        """
        # Search all memory types for the ID
        memory_types = ['solutions', 'errors', 'antipatterns', 'preferences',
                        'git_conventions', 'dependencies', 'testing', 'env_configs', 'api_notes']

        for mem_type in memory_types:
            memories = self.index.get(mem_type, [])
            for mem in memories:
                if mem.get('id', '').startswith(memory_id):
                    # Mark as archived
                    mem['archived'] = True
                    mem['archived_at'] = datetime.now().isoformat()

                    # Reduce gravitational mass (less likely to resurface)
                    current_mass = mem.get('gravitational_mass', 1.0)
                    mem['gravitational_mass'] = max(0.1, current_mass * 0.5)

                    self._save_index()
                    return True

        return False

    def get_archived_memories(self, limit: int = 20) -> List[Dict]:
        """Get recently archived memories.

        Args:
            limit: Maximum number of memories to return

        Returns:
            List of archived memory dicts, sorted by archive time
        """
        archived = []

        for mem_type in ['solutions', 'errors', 'antipatterns']:
            for mem in self.index.get(mem_type, []):
                if mem.get('archived'):
                    archived.append({
                        **mem,
                        'memory_type': mem_type
                    })

        # Sort by archive time, most recent first
        archived.sort(key=lambda x: x.get('archived_at', ''), reverse=True)

        return archived[:limit]

    def unarchive_memory(self, memory_id: str) -> bool:
        """Restore an archived memory to active status.

        Args:
            memory_id: The ID (or 8-char prefix) of the memory to unarchive

        Returns:
            True if memory was found and unarchived, False otherwise
        """
        memory_types = ['solutions', 'errors', 'antipatterns', 'preferences',
                        'git_conventions', 'dependencies', 'testing', 'env_configs', 'api_notes']

        for mem_type in memory_types:
            memories = self.index.get(mem_type, [])
            for mem in memories:
                if mem.get('id', '').startswith(memory_id) and mem.get('archived'):
                    mem['archived'] = False
                    mem.pop('archived_at', None)
                    # Restore some gravitational mass
                    mem['gravitational_mass'] = mem.get('gravitational_mass', 0.5) * 2

                    self._save_index()
                    return True

        return False

    # SESSION MANAGEMENT
    
    def save_session_summary(self, summary: str, key_learnings: List[str] = None,
                           project_path: str = None):
        """Save a summary of a coding session.
        
        Args:
            summary: Brief summary of what was accomplished
            key_learnings: List of important insights or decisions
            project_path: Optional project this session was related to
        """
        timestamp = datetime.now().isoformat()
        session_id = hashlib.md5(f"{summary}{timestamp}".encode()).hexdigest()[:12]
        
        session_data = {
            "id": session_id,
            "timestamp": timestamp,
            "summary": summary,
            "key_learnings": key_learnings or [],
            "project_path": project_path
        }
        
        session_file = self.sessions_path / f"{session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        # Update index
        self.index["sessions"].append(session_data)
        self._save_index()

        return session_data

    # ERROR/DEBUGGING PATTERN MANAGEMENT

    def add_error(self, error_message: str, resolution: str, context: str = None,
                  tags: List[str] = None):
        """Store an error pattern and its resolution.

        Args:
            error_message: The error message or stack trace
            resolution: How the error was resolved
            context: Optional context about what was happening
            tags: Tags for categorization
        """
        timestamp = datetime.now().isoformat()
        error_id = hashlib.md5(f"{error_message}{timestamp}".encode()).hexdigest()[:12]

        error_data = {
            "id": error_id,
            "error_message": error_message,
            "resolution": resolution,
            "context": context or "",
            "tags": tags or [],
            "timestamp": timestamp,
            "embedding": self._simple_embedding(f"{error_message} {resolution}").tolist()
        }

        # Save to file
        error_file = self.errors_path / f"{error_id}.json"
        with open(error_file, 'w') as f:
            json.dump(error_data, f, indent=2)

        # Update index
        self.index["errors"].append(error_data)
        self._save_index()

        return error_data

    def search_errors(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search for relevant error patterns using semantic similarity."""
        query_embedding = self._simple_embedding(query)
        scored_errors = []

        for error in self.index["errors"]:
            error_embedding = np.array(error["embedding"])
            similarity = self._cosine_similarity(query_embedding, error_embedding)
            scored_errors.append((similarity, error))

        scored_errors.sort(reverse=True, key=lambda x: x[0])
        return [err for _, err in scored_errors[:top_k]]

    # ANTIPATTERN MANAGEMENT

    def add_antipattern(self, pattern: str, reason: str, alternative: str,
                        tags: List[str] = None):
        """Store an antipattern (what NOT to do).

        Args:
            pattern: What NOT to do
            reason: Why it's bad
            alternative: What to do instead
            tags: Tags for categorization
        """
        timestamp = datetime.now().isoformat()
        antipattern_id = hashlib.md5(f"{pattern}{timestamp}".encode()).hexdigest()[:12]

        antipattern_data = {
            "id": antipattern_id,
            "pattern": pattern,
            "reason": reason,
            "alternative": alternative,
            "tags": tags or [],
            "timestamp": timestamp,
            "embedding": self._simple_embedding(f"{pattern} {reason} {alternative}").tolist()
        }

        # Save to file
        antipattern_file = self.antipatterns_path / f"{antipattern_id}.json"
        with open(antipattern_file, 'w') as f:
            json.dump(antipattern_data, f, indent=2)

        # Update index
        self.index["antipatterns"].append(antipattern_data)
        self._save_index()

        return antipattern_data

    def search_antipatterns(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search for relevant antipatterns using semantic similarity."""
        query_embedding = self._simple_embedding(query)
        scored_antipatterns = []

        for ap in self.index["antipatterns"]:
            ap_embedding = np.array(ap["embedding"])
            similarity = self._cosine_similarity(query_embedding, ap_embedding)
            scored_antipatterns.append((similarity, ap))

        scored_antipatterns.sort(reverse=True, key=lambda x: x[0])
        return [ap for _, ap in scored_antipatterns[:top_k]]

    # GIT CONVENTIONS MANAGEMENT

    def add_git_convention(self, convention_type: str, pattern: str, example: str,
                           tags: List[str] = None):
        """Store a git convention (commit style, branch naming, etc.).

        Args:
            convention_type: Type of convention (commit_message, branch_naming, pr_template)
            pattern: The pattern or rule
            example: An example demonstrating the convention
            tags: Tags for categorization
        """
        timestamp = datetime.now().isoformat()
        convention_id = hashlib.md5(f"{convention_type}{pattern}{timestamp}".encode()).hexdigest()[:12]

        convention_data = {
            "id": convention_id,
            "convention_type": convention_type,
            "pattern": pattern,
            "example": example,
            "tags": tags or [],
            "timestamp": timestamp,
            "embedding": self._simple_embedding(f"{convention_type} {pattern} {example}").tolist()
        }

        # Save to file
        convention_file = self.git_conventions_path / f"{convention_id}.json"
        with open(convention_file, 'w') as f:
            json.dump(convention_data, f, indent=2)

        # Update index
        self.index["git_conventions"].append(convention_data)
        self._save_index()

        return convention_data

    def search_git_conventions(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search for relevant git conventions using semantic similarity."""
        query_embedding = self._simple_embedding(query)
        scored_conventions = []

        for conv in self.index["git_conventions"]:
            conv_embedding = np.array(conv["embedding"])
            similarity = self._cosine_similarity(query_embedding, conv_embedding)
            scored_conventions.append((similarity, conv))

        scored_conventions.sort(reverse=True, key=lambda x: x[0])
        return [conv for _, conv in scored_conventions[:top_k]]

    # DEPENDENCY MANAGEMENT

    def add_dependency(self, name: str, version_constraint: str = None, notes: str = None,
                       tags: List[str] = None):
        """Store dependency/library information (keyed by name).

        Args:
            name: Package/library name
            version_constraint: Version constraint (e.g., ">=2.0,<3.0")
            notes: Notes about the dependency (gotchas, alternatives, etc.)
            tags: Tags for categorization
        """
        timestamp = datetime.now().isoformat()

        dependency_data = {
            "name": name,
            "version_constraint": version_constraint or "",
            "notes": notes or "",
            "tags": tags or [],
            "timestamp": timestamp
        }

        # Save to file
        dep_file = self.dependencies_path / f"{name}.json"
        with open(dep_file, 'w') as f:
            json.dump(dependency_data, f, indent=2)

        # Update index (keyed by name for direct lookup)
        self.index["dependencies"][name] = dependency_data
        self._save_index()

        return dependency_data

    def get_dependency(self, name: str) -> Optional[Dict]:
        """Retrieve dependency information by name."""
        return self.index["dependencies"].get(name)

    def get_all_dependencies(self) -> Dict:
        """Retrieve all stored dependencies."""
        return self.index["dependencies"]

    # TESTING PATTERN MANAGEMENT

    def add_testing_pattern(self, strategy: str, framework: str, pattern: str,
                            example: str = None, tags: List[str] = None):
        """Store a testing pattern.

        Args:
            strategy: Testing strategy (unit, integration, e2e)
            framework: Testing framework (pytest, jest, etc.)
            pattern: The testing pattern or approach
            example: Optional code example
            tags: Tags for categorization
        """
        timestamp = datetime.now().isoformat()
        testing_id = hashlib.md5(f"{strategy}{pattern}{timestamp}".encode()).hexdigest()[:12]

        testing_data = {
            "id": testing_id,
            "strategy": strategy,
            "framework": framework,
            "pattern": pattern,
            "example": example or "",
            "tags": tags or [],
            "timestamp": timestamp,
            "embedding": self._simple_embedding(f"{strategy} {framework} {pattern}").tolist()
        }

        # Save to file
        testing_file = self.testing_path / f"{testing_id}.json"
        with open(testing_file, 'w') as f:
            json.dump(testing_data, f, indent=2)

        # Update index
        self.index["testing"].append(testing_data)
        self._save_index()

        return testing_data

    def search_testing_patterns(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search for relevant testing patterns using semantic similarity."""
        query_embedding = self._simple_embedding(query)
        scored_patterns = []

        for tp in self.index["testing"]:
            tp_embedding = np.array(tp["embedding"])
            similarity = self._cosine_similarity(query_embedding, tp_embedding)
            scored_patterns.append((similarity, tp))

        scored_patterns.sort(reverse=True, key=lambda x: x[0])
        return [tp for _, tp in scored_patterns[:top_k]]

    # ENVIRONMENT CONFIGURATION MANAGEMENT

    def add_environment(self, env_type: str, config: str, notes: str = None,
                        tags: List[str] = None):
        """Store environment configuration (keyed by env_type).

        Args:
            env_type: Type of environment (local, docker, ci, staging, production)
            config: Configuration details
            notes: Additional notes
            tags: Tags for categorization
        """
        timestamp = datetime.now().isoformat()

        environment_data = {
            "env_type": env_type,
            "config": config,
            "notes": notes or "",
            "tags": tags or [],
            "timestamp": timestamp
        }

        # Save to file
        env_file = self.environment_path / f"{env_type}.json"
        with open(env_file, 'w') as f:
            json.dump(environment_data, f, indent=2)

        # Update index (keyed by env_type for direct lookup)
        self.index["environment"][env_type] = environment_data
        self._save_index()

        return environment_data

    def get_environment(self, env_type: str) -> Optional[Dict]:
        """Retrieve environment configuration by type."""
        return self.index["environment"].get(env_type)

    def get_all_environments(self) -> Dict:
        """Retrieve all stored environment configurations."""
        return self.index["environment"]

    # API NOTES MANAGEMENT

    def add_api_note(self, service_name: str, notes: str, endpoint: str = None,
                     tags: List[str] = None):
        """Store notes about an API or external service.

        Args:
            service_name: Name of the service/API
            notes: Notes (rate limits, auth patterns, quirks, etc.)
            endpoint: Optional specific endpoint
            tags: Tags for categorization
        """
        timestamp = datetime.now().isoformat()
        api_id = hashlib.md5(f"{service_name}{endpoint or ''}{timestamp}".encode()).hexdigest()[:12]

        api_data = {
            "id": api_id,
            "service_name": service_name,
            "endpoint": endpoint or "",
            "notes": notes,
            "tags": tags or [],
            "timestamp": timestamp,
            "embedding": self._simple_embedding(f"{service_name} {endpoint or ''} {notes}").tolist()
        }

        # Save to file
        api_file = self.api_notes_path / f"{api_id}.json"
        with open(api_file, 'w') as f:
            json.dump(api_data, f, indent=2)

        # Update index
        self.index["api_notes"].append(api_data)
        self._save_index()

        return api_data

    def search_api_notes(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search for relevant API notes using semantic similarity."""
        query_embedding = self._simple_embedding(query)
        scored_notes = []

        for note in self.index["api_notes"]:
            note_embedding = np.array(note["embedding"])
            similarity = self._cosine_similarity(query_embedding, note_embedding)
            scored_notes.append((similarity, note))

        scored_notes.sort(reverse=True, key=lambda x: x[0])
        return [note for _, note in scored_notes[:top_k]]

    # PINNED MEMORY MANAGEMENT (Protected memories that never get overwritten)

    def add_pinned_memory(self, name: str, content: str, category: str = "general",
                          tags: List[str] = None, sensitive: bool = False) -> Dict:
        """Add a pinned/protected memory that will never be auto-deleted.

        Use this for critical information like:
        - SSH credentials for test environments
        - API keys reference (not the actual keys!)
        - Important server configurations
        - Project-specific secrets management notes

        Args:
            name: Short, memorable name for this memory (e.g., "VPS SSH")
            content: The content to remember (can include secrets)
            category: Category (e.g., "credentials", "config", "server", "api")
            tags: Tags for organization
            sensitive: If True, marks as containing sensitive data

        Returns:
            The created pinned memory entry
        """
        timestamp = datetime.now().isoformat()
        pin_id = hashlib.md5(f"{name}{timestamp}".encode()).hexdigest()[:12]

        # Warn about sensitive data but allow storage
        if sensitive:
            print(f"⚠️  Storing sensitive data in pinned memory: {name}")
            print("   This data is stored locally and never synced to cloud.")

        pinned_data = {
            "id": pin_id,
            "name": name,
            "content": content,
            "category": category,
            "tags": tags or [],
            "sensitive": sensitive,
            "timestamp": timestamp,
            "pinned": True  # Always true for pinned memories
        }

        # Save to file with secure permissions
        pin_file = self.pinned_path / f"{pin_id}.json"
        self._secure_write_json(pin_file, pinned_data)

        # Update index
        self.index["pinned"].append(pinned_data)
        self._save_index()

        return pinned_data

    def get_pinned_memories(self, category: str = None) -> List[Dict]:
        """Get all pinned memories, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of pinned memory entries
        """
        pinned = self.index.get("pinned", [])
        if category:
            return [p for p in pinned if p.get("category") == category]
        return pinned

    def get_pinned_memory_by_name(self, name: str) -> Optional[Dict]:
        """Get a pinned memory by its name.

        Args:
            name: The name of the pinned memory

        Returns:
            The pinned memory or None
        """
        for p in self.index.get("pinned", []):
            if p.get("name", "").lower() == name.lower():
                return p
        return None

    def unpin_memory(self, pin_id: str) -> bool:
        """Remove a pinned memory (requires explicit ID).

        Args:
            pin_id: The ID of the pinned memory to remove

        Returns:
            True if successfully removed
        """
        pinned = self.index.get("pinned", [])
        original_len = len(pinned)

        self.index["pinned"] = [p for p in pinned if p.get("id") != pin_id]

        if len(self.index["pinned"]) < original_len:
            # Delete the file
            pin_file = self.pinned_path / f"{pin_id}.json"
            if pin_file.exists():
                pin_file.unlink()
            self._save_index()
            return True
        return False

    def search_pinned(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search pinned memories by name, content, or tags.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            Matching pinned memories
        """
        query_lower = query.lower()
        scored = []

        for p in self.index.get("pinned", []):
            score = 0
            # Name match is highest priority
            if query_lower in p.get("name", "").lower():
                score += 10
            # Category match
            if query_lower in p.get("category", "").lower():
                score += 5
            # Tag match
            if any(query_lower in t.lower() for t in p.get("tags", [])):
                score += 3
            # Content match
            if query_lower in p.get("content", "").lower():
                score += 1

            if score > 0:
                scored.append((score, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:top_k]]

    # ADAPTIVE SIGNAL LEARNING

    def learn_signal(self, word: str, signal_type: str = "emphasis", weight: int = 1):
        """Learn a user-specific signal word from their communication patterns.

        Args:
            word: The word or phrase to learn
            signal_type: "emphasis" (caps, exclamation) or "repeated" (frequent use)
            weight: How much to boost this signal's score
        """
        word = word.lower().strip()
        if not word or len(word) < 3:
            return

        learned = self.index.get("learned_signals", {})
        if signal_type not in learned:
            learned[signal_type] = {}

        if signal_type in ["emphasis", "repeated"]:
            current = learned[signal_type].get(word, 0)
            learned[signal_type][word] = current + weight
            self.index["learned_signals"] = learned
            self._save_index()

    def record_effective_signal(self, signal: str):
        """Record a signal that led to a successful memory capture.

        This helps identify which signals work best for this user.
        """
        signal = signal.lower().strip()
        learned = self.index.get("learned_signals", {})
        if "effective" not in learned:
            learned["effective"] = []

        if signal not in learned["effective"]:
            learned["effective"].append(signal)
            self.index["learned_signals"] = learned
            self._save_index()

    def get_learned_signals(self, signal_type: str = None, min_count: int = 2) -> List[str]:
        """Get learned signal words that have been used frequently.

        Args:
            signal_type: Optional filter by type ("emphasis", "repeated", "effective")
            min_count: Minimum usage count to include (for emphasis/repeated)

        Returns:
            List of learned signal words
        """
        learned = self.index.get("learned_signals", {})
        signals = []

        if signal_type == "effective":
            return learned.get("effective", [])

        for stype in ["emphasis", "repeated"]:
            if signal_type and stype != signal_type:
                continue
            type_signals = learned.get(stype, {})
            for word, count in type_signals.items():
                if count >= min_count:
                    signals.append(word)

        return list(set(signals))

    def get_signal_score(self, word: str) -> int:
        """Get the learned importance score for a word.

        Higher scores mean the user tends to emphasize this word.
        """
        word = word.lower().strip()
        learned = self.index.get("learned_signals", {})

        score = 0
        # Check emphasis
        score += learned.get("emphasis", {}).get(word, 0)
        # Check repeated
        score += learned.get("repeated", {}).get(word, 0) // 2
        # Bonus if it's proven effective
        if word in learned.get("effective", []):
            score += 5

        return score

    # AUTO-PIN DETECTION

    # Patterns that indicate content should be auto-pinned
    AUTO_PIN_PATTERNS = [
        (r'ssh\s+[\w.-]+@[\w.-]+', 'credentials', 'SSH connection'),
        (r'[\w.-]+@[\w.-]+:\d+', 'server', 'Server address'),
        (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?', 'server', 'IP address'),
        (r'sk-[a-zA-Z0-9]{20,}', 'credentials', 'API key'),
        (r'ghp_[a-zA-Z0-9]{30,}', 'credentials', 'GitHub token'),
        (r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY', 'credentials', 'Private key'),
        (r'Bearer\s+[A-Za-z0-9._-]{20,}', 'credentials', 'Bearer token'),
        (r'mongodb(?:\+srv)?://[^\s]+', 'database', 'MongoDB URI'),
        (r'postgres(?:ql)?://[^\s]+', 'database', 'PostgreSQL URI'),
        (r'mysql://[^\s]+', 'database', 'MySQL URI'),
        (r'redis://[^\s]+', 'database', 'Redis URI'),
        (r'https?://[\w.-]+(?::\d+)?/api/v\d+', 'api', 'API endpoint'),
    ]

    def detect_auto_pin(self, text: str) -> Optional[Dict]:
        """Detect if text contains patterns that should be auto-pinned.

        Returns pin metadata if pattern detected, None otherwise.
        """
        for pattern, category, description in self.AUTO_PIN_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {
                    'category': category,
                    'description': description,
                    'matched': match.group(0),
                    'sensitive': category == 'credentials'
                }
        return None

    def auto_pin_if_needed(self, text: str, name_hint: str = None) -> Optional[Dict]:
        """Auto-pin content if it matches credential/config patterns.

        Args:
            text: Content to check and potentially pin
            name_hint: Optional name hint for the pinned memory

        Returns:
            Created pin if auto-pinned, None otherwise
        """
        detected = self.detect_auto_pin(text)
        if not detected:
            return None

        # Generate name from hint or description
        name = name_hint or f"Auto: {detected['description']}"

        # Check if already pinned (avoid duplicates)
        existing = self.get_pinned_memories(category=detected['category'])
        for p in existing:
            if detected['matched'] in p.get('content', ''):
                return None  # Already pinned

        # Create the pin
        return self.add_pinned_memory(
            name=name,
            content=text,
            category=detected['category'],
            tags=['auto-pinned', detected['description'].lower().replace(' ', '-')],
            sensitive=detected['sensitive']
        )

    # GRAVITATIONAL TASK CLUSTERING
    # Memories cluster around task centers based on frequency and amplitude

    def create_task_cluster(self, name: str, description: str = "",
                           parent_task: str = None) -> str:
        """Create a task cluster that memories can orbit around.

        Args:
            name: Task name (e.g., "implement-auth", "fix-memory-bug")
            description: Optional task description
            parent_task: Optional parent task ID for subtask hierarchy

        Returns:
            task_id for the created cluster
        """
        task_id = hashlib.md5(f"{name}{datetime.now().isoformat()}".encode()).hexdigest()[:12]

        clusters = self.index.get("task_clusters", {})
        clusters[task_id] = {
            "name": name,
            "description": description,
            "parent": parent_task,
            "mass": 1,  # Initial gravitational mass
            "memories": [],  # Memory IDs that orbit this task
            "created": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat()
        }

        self.index["task_clusters"] = clusters
        self._save_index()
        return task_id

    def attach_memory_to_task(self, memory_id: str, task_id: str,
                              memory_type: str = "solution"):
        """Attach a memory to a task cluster, increasing both masses.

        Args:
            memory_id: ID of the memory to attach
            task_id: ID of the task cluster
            memory_type: Type of memory (for context)
        """
        clusters = self.index.get("task_clusters", {})
        gravity = self.index.get("memory_gravity", {})

        if task_id not in clusters:
            return

        # Add memory to task's orbit
        if memory_id not in clusters[task_id]["memories"]:
            clusters[task_id]["memories"].append(memory_id)
            clusters[task_id]["mass"] += 1  # Task gains mass
            clusters[task_id]["last_active"] = datetime.now().isoformat()

        # Initialize or update memory gravity
        if memory_id not in gravity:
            gravity[memory_id] = {
                "mass": 1,
                "references": 0,
                "tasks": [],
                "last_accessed": datetime.now().isoformat()
            }

        if task_id not in gravity[memory_id]["tasks"]:
            gravity[memory_id]["tasks"].append(task_id)
            gravity[memory_id]["mass"] += 1

        self.index["task_clusters"] = clusters
        self.index["memory_gravity"] = gravity
        self._save_index()

    def reference_memory(self, memory_id: str):
        """Record that a memory was referenced, increasing its gravitational mass."""
        gravity = self.index.get("memory_gravity", {})

        if memory_id not in gravity:
            gravity[memory_id] = {
                "mass": 1,
                "references": 0,
                "tasks": [],
                "last_accessed": datetime.now().isoformat()
            }

        gravity[memory_id]["references"] += 1
        gravity[memory_id]["mass"] += 0.5  # Gradual mass increase
        gravity[memory_id]["last_accessed"] = datetime.now().isoformat()

        self.index["memory_gravity"] = gravity
        self._save_index()

    def get_task_memories(self, task_id: str, include_subtasks: bool = True) -> List[Dict]:
        """Get all memories orbiting a task cluster.

        Args:
            task_id: Task cluster ID
            include_subtasks: Whether to include memories from subtasks

        Returns:
            List of memories sorted by gravitational mass (highest first)
        """
        clusters = self.index.get("task_clusters", {})
        gravity = self.index.get("memory_gravity", {})

        if task_id not in clusters:
            return []

        memory_ids = set(clusters[task_id]["memories"])

        # Include subtask memories if requested
        if include_subtasks:
            for tid, cluster in clusters.items():
                if cluster.get("parent") == task_id:
                    memory_ids.update(cluster["memories"])

        # Gather memories with their gravity scores
        memories_with_mass = []
        for mid in memory_ids:
            mass = gravity.get(mid, {}).get("mass", 1)
            # Find the actual memory data
            memory = self._find_memory_by_id(mid)
            if memory:
                memory["_gravity_mass"] = mass
                memories_with_mass.append(memory)

        # Sort by mass (highest gravity first)
        memories_with_mass.sort(key=lambda m: m.get("_gravity_mass", 0), reverse=True)
        return memories_with_mass

    def _find_memory_by_id(self, memory_id: str) -> Optional[Dict]:
        """Find a memory by its ID across all memory types."""
        for mem_type in ["solutions", "errors", "antipatterns", "pinned"]:
            for mem in self.index.get(mem_type, []):
                if mem.get("id") == memory_id:
                    return mem
        return None

    def apply_staleness_decay(self, decay_days: int = 7, decay_factor: float = 0.9):
        """Apply gravitational decay to memories that haven't been accessed recently.

        Memories lose mass over time if not referenced, keeping context fresh.

        Args:
            decay_days: Days of inactivity before decay applies
            decay_factor: Multiplier applied to mass (0.9 = 10% decay)
        """
        gravity = self.index.get("memory_gravity", {})
        now = datetime.now()
        updated = False

        for mid, gdata in gravity.items():
            last_accessed = gdata.get("last_accessed")
            if last_accessed:
                try:
                    last_dt = datetime.fromisoformat(last_accessed)
                    days_inactive = (now - last_dt).days
                    if days_inactive >= decay_days:
                        # Apply decay
                        old_mass = gdata.get("mass", 1)
                        new_mass = max(0.1, old_mass * decay_factor)
                        gdata["mass"] = new_mass
                        updated = True
                except (ValueError, TypeError):
                    pass

        if updated:
            self.index["memory_gravity"] = gravity
            self._save_index()

    def get_high_gravity_memories(self, top_k: int = 10) -> List[Dict]:
        """Get memories with highest gravitational mass (most referenced/important).

        These are the "center of mass" memories that should be prioritized.
        Applies staleness decay before retrieval.
        """
        # Apply decay to stale memories
        self.apply_staleness_decay()

        gravity = self.index.get("memory_gravity", {})

        # Sort by mass
        sorted_gravity = sorted(
            gravity.items(),
            key=lambda x: x[1].get("mass", 0),
            reverse=True
        )

        memories = []
        for mid, gdata in sorted_gravity:
            mem = self._find_memory_by_id(mid)
            # Skip archived memories
            if mem and not mem.get('archived'):
                mem["_gravity_mass"] = gdata.get("mass", 1)
                mem["_references"] = gdata.get("references", 0)
                memories.append(mem)
            if len(memories) >= top_k:
                break

        return memories

    def get_task_hierarchy(self, task_id: str = None) -> List[Dict]:
        """Get task clusters in hierarchical structure.

        Args:
            task_id: Optional root task ID (None for all top-level)

        Returns:
            List of tasks with their subtasks nested
        """
        clusters = self.index.get("task_clusters", {})

        def build_tree(parent_id):
            children = []
            for tid, cluster in clusters.items():
                if cluster.get("parent") == parent_id:
                    task = {
                        "id": tid,
                        "name": cluster["name"],
                        "description": cluster.get("description", ""),
                        "mass": cluster.get("mass", 1),
                        "memory_count": len(cluster.get("memories", [])),
                        "subtasks": build_tree(tid)
                    }
                    children.append(task)
            return sorted(children, key=lambda x: x["mass"], reverse=True)

        return build_tree(task_id)

    def auto_cluster_memory(self, memory_id: str, tags: List[str], content: str):
        """Automatically attach a memory to relevant task clusters based on tags/content.

        Uses semantic matching to find the best task cluster.
        """
        clusters = self.index.get("task_clusters", {})
        if not clusters:
            return

        # Score each cluster based on tag/content overlap
        scores = []
        content_words = set(content.lower().split())
        tag_set = set(t.lower() for t in tags)

        for tid, cluster in clusters.items():
            score = 0
            cluster_name_words = set(cluster["name"].lower().replace("-", " ").split())
            cluster_desc_words = set(cluster.get("description", "").lower().split())

            # Tag matches
            score += len(tag_set & cluster_name_words) * 3
            score += len(tag_set & cluster_desc_words) * 2

            # Content word matches
            score += len(content_words & cluster_name_words) * 2
            score += len(content_words & cluster_desc_words)

            if score > 0:
                scores.append((tid, score))

        # Attach to highest scoring cluster if score is significant
        if scores:
            scores.sort(key=lambda x: x[1], reverse=True)
            best_tid, best_score = scores[0]
            if best_score >= 3:  # Threshold
                self.attach_memory_to_task(memory_id, best_tid)

    # CONTEXT INJECTION
    
    def get_relevant_context(self, query: str, project_path: str = None,
                             include_preferences: bool = True,
                             include_solutions: bool = True,
                             include_project: bool = True,
                             include_errors: bool = True,
                             include_antipatterns: bool = True,
                             include_git_conventions: bool = True,
                             include_testing: bool = True,
                             include_api_notes: bool = True) -> str:
        """Get all relevant context for a given query.

        This is the main function to call at the start of a session or when
        Claude Code needs additional context.

        Args:
            query: The current task or question
            project_path: Current project path if available
            include_preferences: Whether to include user preferences
            include_solutions: Whether to search for relevant solutions
            include_project: Whether to include project-specific context
            include_errors: Whether to include relevant error patterns
            include_antipatterns: Whether to include relevant antipatterns
            include_git_conventions: Whether to include git conventions
            include_testing: Whether to include testing patterns
            include_api_notes: Whether to include API notes

        Returns:
            Formatted string with relevant context
        """
        context_parts = []

        # Add preferences
        if include_preferences:
            prefs = self.get_preferences(query, top_k=3)
            if prefs:
                context_parts.append("=== USER PREFERENCES ===")
                for pref in prefs:
                    context_parts.append(f"\n[{pref['category']}]")
                    context_parts.append(pref['content'])

        # Add project context
        if include_project and project_path:
            project_ctx = self.get_project_context(project_path)
            if project_ctx:
                context_parts.append("\n=== PROJECT CONTEXT ===")
                context_parts.append(json.dumps(project_ctx, indent=2))

        # Add relevant solutions
        if include_solutions:
            solutions = self.search_solutions(query, top_k=2)
            if solutions:
                context_parts.append("\n=== RELEVANT PAST SOLUTIONS ===")
                for sol in solutions:
                    context_parts.append(f"\nProblem: {sol['problem']}")
                    context_parts.append(f"Solution: {sol['solution']}")
                    if sol.get('code_snippet'):
                        context_parts.append(f"```\n{sol['code_snippet']}\n```")

        # Add relevant error patterns
        if include_errors:
            errors = self.search_errors(query, top_k=2)
            if errors:
                context_parts.append("\n=== RELEVANT ERROR PATTERNS ===")
                for err in errors:
                    context_parts.append(f"\nError: {err['error_message']}")
                    context_parts.append(f"Resolution: {err['resolution']}")
                    if err.get('context'):
                        context_parts.append(f"Context: {err['context']}")

        # Add relevant antipatterns
        if include_antipatterns:
            antipatterns = self.search_antipatterns(query, top_k=2)
            if antipatterns:
                context_parts.append("\n=== ANTIPATTERNS (AVOID THESE) ===")
                for ap in antipatterns:
                    context_parts.append(f"\nDon't: {ap['pattern']}")
                    context_parts.append(f"Why: {ap['reason']}")
                    context_parts.append(f"Instead: {ap['alternative']}")

        # Add relevant git conventions
        if include_git_conventions:
            conventions = self.search_git_conventions(query, top_k=2)
            if conventions:
                context_parts.append("\n=== GIT CONVENTIONS ===")
                for conv in conventions:
                    context_parts.append(f"\n[{conv['convention_type']}]")
                    context_parts.append(f"Pattern: {conv['pattern']}")
                    context_parts.append(f"Example: {conv['example']}")

        # Add relevant testing patterns
        if include_testing:
            testing_patterns = self.search_testing_patterns(query, top_k=2)
            if testing_patterns:
                context_parts.append("\n=== TESTING PATTERNS ===")
                for tp in testing_patterns:
                    context_parts.append(f"\n[{tp['strategy']} - {tp['framework']}]")
                    context_parts.append(f"Pattern: {tp['pattern']}")
                    if tp.get('example'):
                        context_parts.append(f"Example:\n```\n{tp['example']}\n```")

        # Add relevant API notes
        if include_api_notes:
            api_notes = self.search_api_notes(query, top_k=2)
            if api_notes:
                context_parts.append("\n=== API NOTES ===")
                for note in api_notes:
                    context_parts.append(f"\n[{note['service_name']}]")
                    if note.get('endpoint'):
                        context_parts.append(f"Endpoint: {note['endpoint']}")
                    context_parts.append(f"Notes: {note['notes']}")

        return "\n".join(context_parts) if context_parts else "No relevant context found."
    
    # UTILITY METHODS
    
    def export_memory(self, output_path: str):
        """Export all memberberries to a single JSON file for backup."""
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "index": self.index
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"🫐 Memberberries exported to {output_path}")
    
    def get_stats(self) -> Dict:
        """Get statistics about stored berries."""
        return {
            "preferences": len(self.index["preferences"]),
            "projects": len(self.index["projects"]),
            "solutions": len(self.index["solutions"]),
            "sessions": len(self.index["sessions"]),
            "errors": len(self.index["errors"]),
            "antipatterns": len(self.index["antipatterns"]),
            "git_conventions": len(self.index["git_conventions"]),
            "dependencies": len(self.index["dependencies"]),
            "testing": len(self.index["testing"]),
            "environment": len(self.index["environment"]),
            "api_notes": len(self.index["api_notes"]),
            "pinned": len(self.index.get("pinned", []))
        }


if __name__ == "__main__":
    # Example usage
    bm = BerryManager()
    
    print("🫐 Memberberries Berry Manager initialized!")
    print(f"Base path: {bm.base_path}")
    print(f"Stats: {bm.get_stats()}")
