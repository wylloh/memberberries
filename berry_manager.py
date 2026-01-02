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

        # Create directories if they don't exist
        all_paths = [
            self.preferences_path, self.projects_path,
            self.solutions_path, self.sessions_path,
            self.errors_path, self.antipatterns_path,
            self.git_conventions_path, self.dependencies_path,
            self.testing_path, self.environment_path, self.api_notes_path
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
            "api_notes": []
        }

        if self.index_path.exists():
            with open(self.index_path, 'r') as f:
                loaded = json.load(f)
                # Merge with defaults to handle upgrades
                for key in default_index:
                    if key not in loaded:
                        loaded[key] = default_index[key]
                return loaded
        return default_index
    
    def _save_index(self):
        """Save the memory index with secure permissions."""
        with open(self.index_path, 'w') as f:
            json.dump(self.index, f, indent=2)
        self._set_file_permissions(self.index_path)
    
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
            solution_embedding = np.array(solution["embedding"])
            similarity = self._cosine_similarity(query_embedding, solution_embedding)
            scored_solutions.append((similarity, solution))
        
        # Sort by similarity
        scored_solutions.sort(reverse=True, key=lambda x: x[0])
        return [sol for _, sol in scored_solutions[:top_k]]
    
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
            "api_notes": len(self.index["api_notes"])
        }


if __name__ == "__main__":
    # Example usage
    bm = BerryManager()
    
    print("🫐 Memberberries Berry Manager initialized!")
    print(f"Base path: {bm.base_path}")
    print(f"Stats: {bm.get_stats()}")
