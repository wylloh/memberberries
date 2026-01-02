"""
Storage Backend Interface - Allows pluggable storage implementations

This module defines an abstract interface that both file-based and vector DB
backends can implement, allowing users to choose based on their needs.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
import numpy as np


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def initialize(self, base_path: str):
        """Initialize the storage backend."""
        pass
    
    @abstractmethod
    def add_preference(self, preference: Dict) -> Dict:
        """Add a preference and return the stored object."""
        pass
    
    @abstractmethod
    def get_preferences(self, query: str = None, top_k: int = 5) -> List[Dict]:
        """Retrieve preferences, optionally filtered by query."""
        pass
    
    @abstractmethod
    def add_solution(self, solution: Dict) -> Dict:
        """Add a solution and return the stored object."""
        pass
    
    @abstractmethod
    def search_solutions(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search for solutions using semantic similarity."""
        pass
    
    @abstractmethod
    def add_project_context(self, project_hash: str, context: Dict) -> str:
        """Add or update project context."""
        pass
    
    @abstractmethod
    def get_project_context(self, project_hash: str) -> Optional[Dict]:
        """Retrieve project context."""
        pass
    
    @abstractmethod
    def add_session(self, session: Dict) -> Dict:
        """Add a session summary."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict:
        """Get statistics about stored items."""
        pass


class FileStorageBackend(StorageBackend):
    """
    File-based storage backend (current implementation).
    
    Pros:
    - Simple, no dependencies
    - Easy to backup/version control
    - Works everywhere
    - Human-readable
    
    Cons:
    - Slower for >1000 items
    - Basic search quality
    - No advanced filtering
    """
    
    def __init__(self):
        self.preferences = []
        self.projects = {}
        self.solutions = []
        self.sessions = []
    
    def initialize(self, base_path: str):
        # Current implementation from memory_manager.py
        pass
    
    # ... implement all abstract methods with current logic


class ChromaDBBackend(StorageBackend):
    """
    ChromaDB vector database backend (optional upgrade).
    
    Pros:
    - Fast for >1000 items
    - Better search quality
    - Advanced filtering
    - Built for embeddings
    
    Cons:
    - Requires chromadb package
    - Slightly more complex setup
    - Less portable
    
    Installation:
        pip install chromadb
    """
    
    def __init__(self, embedding_function=None):
        """
        Args:
            embedding_function: Optional custom embedding function.
                               If None, uses ChromaDB's default.
        """
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise ImportError(
                "ChromaDB backend requires: pip install chromadb"
            )
        
        self.chromadb = chromadb
        self.client = None
        self.collections = {}
        self.embedding_function = embedding_function
    
    def initialize(self, base_path: str):
        """Initialize ChromaDB with persistent storage."""
        self.client = self.chromadb.PersistentClient(
            path=f"{base_path}/chromadb",
            settings=self.chromadb.Settings(anonymized_telemetry=False)
        )
        
        # Create collections for each data type
        self.collections = {
            'preferences': self.client.get_or_create_collection(
                name="preferences",
                metadata={"hnsw:space": "cosine"}
            ),
            'solutions': self.client.get_or_create_collection(
                name="solutions",
                metadata={"hnsw:space": "cosine"}
            ),
            'projects': self.client.get_or_create_collection(
                name="projects",
                metadata={"hnsw:space": "cosine"}
            ),
            'sessions': self.client.get_or_create_collection(
                name="sessions",
                metadata={"hnsw:space": "cosine"}
            )
        }
    
    def add_preference(self, preference: Dict) -> Dict:
        """Add preference to ChromaDB."""
        pref_id = f"pref_{preference['timestamp']}"
        
        self.collections['preferences'].add(
            documents=[preference['content']],
            metadatas=[{
                'category': preference['category'],
                'tags': ','.join(preference['tags']),
                'timestamp': preference['timestamp']
            }],
            ids=[pref_id]
        )
        
        return preference
    
    def get_preferences(self, query: str = None, top_k: int = 5) -> List[Dict]:
        """Retrieve preferences with semantic search."""
        if not query:
            # Get all preferences
            results = self.collections['preferences'].get()
        else:
            # Semantic search
            results = self.collections['preferences'].query(
                query_texts=[query],
                n_results=top_k
            )
        
        # Convert to expected format
        preferences = []
        if results:
            docs = results.get('documents', [[]])[0]
            metas = results.get('metadatas', [[]])[0]
            
            for doc, meta in zip(docs, metas):
                preferences.append({
                    'content': doc,
                    'category': meta.get('category'),
                    'tags': meta.get('tags', '').split(','),
                    'timestamp': meta.get('timestamp')
                })
        
        return preferences
    
    def add_solution(self, solution: Dict) -> Dict:
        """Add solution to ChromaDB."""
        sol_id = solution['id']
        
        # Combine problem and solution for better search
        search_text = f"{solution['problem']} {solution['solution']}"
        
        self.collections['solutions'].add(
            documents=[search_text],
            metadatas=[{
                'problem': solution['problem'],
                'solution': solution['solution'],
                'tags': ','.join(solution['tags']),
                'code_snippet': solution.get('code_snippet', ''),
                'timestamp': solution['timestamp']
            }],
            ids=[sol_id]
        )
        
        return solution
    
    def search_solutions(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search solutions using ChromaDB's vector search."""
        results = self.collections['solutions'].query(
            query_texts=[query],
            n_results=top_k
        )
        
        solutions = []
        if results:
            metas = results.get('metadatas', [[]])[0]
            
            for meta in metas:
                solutions.append({
                    'problem': meta.get('problem'),
                    'solution': meta.get('solution'),
                    'tags': meta.get('tags', '').split(','),
                    'code_snippet': meta.get('code_snippet'),
                    'timestamp': meta.get('timestamp')
                })
        
        return solutions
    
    def add_project_context(self, project_hash: str, context: Dict) -> str:
        """Add project context."""
        # Store as document for searchability
        search_text = f"{context.get('name', '')} {context.get('description', '')} {context.get('architecture', '')}"
        
        self.collections['projects'].upsert(
            documents=[search_text],
            metadatas=[context],
            ids=[project_hash]
        )
        
        return project_hash
    
    def get_project_context(self, project_hash: str) -> Optional[Dict]:
        """Retrieve project context."""
        results = self.collections['projects'].get(
            ids=[project_hash]
        )
        
        if results and results['metadatas']:
            return results['metadatas'][0]
        return None
    
    def add_session(self, session: Dict) -> Dict:
        """Add session summary."""
        session_id = session['id']
        
        self.collections['sessions'].add(
            documents=[session['summary']],
            metadatas=[{
                'summary': session['summary'],
                'key_learnings': ','.join(session['key_learnings']),
                'project_path': session.get('project_path', ''),
                'timestamp': session['timestamp']
            }],
            ids=[session_id]
        )
        
        return session
    
    def get_stats(self) -> Dict:
        """Get statistics."""
        return {
            'preferences': self.collections['preferences'].count(),
            'projects': self.collections['projects'].count(),
            'solutions': self.collections['solutions'].count(),
            'sessions': self.collections['sessions'].count()
        }


def get_backend(backend_type: str = 'file', **kwargs) -> StorageBackend:
    """
    Factory function to get the appropriate storage backend.
    
    Args:
        backend_type: 'file' or 'chromadb'
        **kwargs: Additional arguments for the backend
    
    Returns:
        Initialized storage backend
    
    Example:
        # Use file storage (default)
        backend = get_backend('file')
        
        # Use ChromaDB
        backend = get_backend('chromadb')
    """
    backends = {
        'file': FileStorageBackend,
        'chromadb': ChromaDBBackend
    }
    
    if backend_type not in backends:
        raise ValueError(f"Unknown backend: {backend_type}. Choose from: {list(backends.keys())}")
    
    return backends[backend_type](**kwargs)
