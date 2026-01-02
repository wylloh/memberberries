#!/usr/bin/env python3
"""
🫐 Memberberries Berry Manager

Member when Claude Code had no memory? We memberberry!
A lightweight berry storage system for persisting and juicing context across sessions.
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np


class BerryManager:
    """Manages memberberries for Claude Code sessions."""
    
    def __init__(self, base_path: str = None):
        """Initialize the berry manager.
        
        Args:
            base_path: Base directory for berry storage. Defaults to ~/.memberberries
        """
        if base_path is None:
            base_path = os.path.expanduser("~/.memberberries")
        
        self.base_path = Path(base_path)
        self.preferences_path = self.base_path / "preferences"
        self.projects_path = self.base_path / "projects"
        self.solutions_path = self.base_path / "solutions"
        self.sessions_path = self.base_path / "sessions"
        
        # Create directories if they don't exist
        for path in [self.preferences_path, self.projects_path, 
                     self.solutions_path, self.sessions_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Load or create berry index
        self.index_path = self.base_path / "berry_index.json"
        self.index = self._load_index()
    
    def _load_index(self) -> Dict:
        """Load the memory index or create a new one."""
        if self.index_path.exists():
            with open(self.index_path, 'r') as f:
                return json.load(f)
        return {
            "preferences": [],
            "projects": {},
            "solutions": [],
            "sessions": []
        }
    
    def _save_index(self):
        """Save the memory index."""
        with open(self.index_path, 'w') as f:
            json.dump(self.index, f, indent=2)
    
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
    
    # CONTEXT INJECTION
    
    def get_relevant_context(self, query: str, project_path: str = None,
                           include_preferences: bool = True,
                           include_solutions: bool = True,
                           include_project: bool = True) -> str:
        """Get all relevant context for a given query.
        
        This is the main function to call at the start of a session or when
        Claude Code needs additional context.
        
        Args:
            query: The current task or question
            project_path: Current project path if available
            include_preferences: Whether to include user preferences
            include_solutions: Whether to search for relevant solutions
            include_project: Whether to include project-specific context
            
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
            "sessions": len(self.index["sessions"])
        }


if __name__ == "__main__":
    # Example usage
    bm = BerryManager()
    
    print("🫐 Memberberries Berry Manager initialized!")
    print(f"Base path: {bm.base_path}")
    print(f"Stats: {bm.get_stats()}")
