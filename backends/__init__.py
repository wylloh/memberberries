"""
Memberberries storage backends.

Available backends:
- JsonBackend: Default, file-based storage (no dependencies)
- SemanticBackend: Adds embedding-based search (requires sentence-transformers)

Usage:
    from backends import get_backend

    backend = get_backend(project_path)  # Returns configured backend
    berries = backend.load_active()
"""

import json
from pathlib import Path
from typing import Optional

from .base import Berry, Checkpoint, SearchResult, MemoryBackend
from .json_backend import JsonBackend


def get_backend(project_path: Path, backend_type: Optional[str] = None) -> MemoryBackend:
    """Get the configured storage backend.

    Args:
        project_path: Path to the project root
        backend_type: Override backend type ("json" or "semantic")
                      If None, reads from config or defaults to "json"

    Returns:
        Configured MemoryBackend instance
    """
    project_path = Path(project_path)

    # Check config file for backend preference
    if backend_type is None:
        config_file = project_path / ".memberberries" / "config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                backend_type = config.get('backend', 'json')
            except Exception:
                backend_type = 'json'
        else:
            backend_type = 'json'

    # Instantiate the appropriate backend
    if backend_type == 'semantic':
        try:
            from .semantic_backend import SemanticBackend
            return SemanticBackend(project_path)
        except ImportError:
            # Fall back to JSON if sentence-transformers not installed
            print("Warning: sentence-transformers not installed, using JSON backend")
            return JsonBackend(project_path)
    else:
        return JsonBackend(project_path)


def configure_backend(project_path: Path, backend_type: str) -> None:
    """Configure the backend for a project.

    Args:
        project_path: Path to the project root
        backend_type: "json" or "semantic"
    """
    project_path = Path(project_path)
    config_dir = project_path / ".memberberries"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_file = config_dir / "config.json"

    # Load existing config
    config = {}
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except Exception:
            pass

    # Update backend setting
    config['backend'] = backend_type

    # Save config
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)


__all__ = [
    'MemoryBackend',
    'Berry',
    'Checkpoint',
    'SearchResult',
    'JsonBackend',
    'get_backend',
    'configure_backend',
]
