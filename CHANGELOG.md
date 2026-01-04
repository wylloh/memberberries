# Changelog

## [3.0.0] - 2026-01-04

### Changed - Claude-First Architecture

Complete rewrite. Memberberries is now scaffolding for Claude to manage its own memory.

**Before:** 7,500 lines, embeddings, search algorithms, gravity systems
**After:** 600 lines, file I/O, folder structure

### New

- `[BERRY #tag] summary` marker for creating berries
- `[ARCHIVE id]` marker for archiving
- `[RETRIEVE #tag]` marker for pulling from archive
- Folder-based archive organization by primary tag
- `member status` command for observability
- Debug logging (no more silent failures)

### Removed

- `berry_manager.py` (1,800 lines)
- Numpy/embedding dependencies
- Search algorithms
- Gravitational clustering
- Adaptive learning
- Auto-pin credentials
- Legacy memory types (errors, antipatterns, git_conventions, etc.)
- Complex index structures

### Philosophy

Claude understands context better than any embedding algorithm. The new architecture lets Claude decide what to remember, archive, and retrieve. The system handles file I/O.

## [2.0.0] - 2026-01-03

- Claude-managed memory markers (`[MEMORY]`, `[ARCHIVE]`)
- Session detection
- Active memory management

## [1.0.0] - 2026-01-02

- Initial release
- File-based storage
- Semantic search with embeddings
- CLI interface
