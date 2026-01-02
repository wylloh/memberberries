# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Vector database support (ChromaDB, Pinecone)
- Sentence transformers for better embeddings
- Web UI for browsing memories
- Comprehensive test coverage
- Auto-extraction from Claude Code transcripts

## [1.0.0] - 2026-01-02

### Added
- Initial release
- File-based memory storage system
- Semantic search using simple embeddings
- CLI interface (claude_memory.py)
- Integration helper for Claude Code (integration.py)
- Core memory management (memory_manager.py)
- Support for preferences, projects, solutions, and sessions
- Automated setup script (setup.sh)
- Interactive demo (demo.py)
- Comprehensive documentation:
  - README.md - Main documentation
  - QUICKSTART.md - 60-second setup guide
  - ARCHITECTURE.md - System design
  - PROJECT_SUMMARY.md - Overview
  - CONTRIBUTING.md - Contribution guidelines
- MIT License

### Features
- Store and retrieve coding preferences
- Manage project-specific context
- Save and search past solutions
- Track session history
- Export/import functionality
- Shell integration helpers
- Zero external dependencies (except numpy)
- Local-first, privacy-focused design
- Human-readable storage format

### Performance
- Handles up to 1,000 entries efficiently
- Search: ~10-100ms for typical workloads
- Minimal storage footprint (~3-5KB per entry)

## [0.1.0] - Development

### Added
- Initial prototype
- Basic storage functionality
- Simple search capability
- Command-line interface

---

## Version History

### How to Read This Changelog

- **Added** - New features
- **Changed** - Changes in existing functionality
- **Deprecated** - Soon-to-be removed features
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Security fixes

### Versioning

- **Major version** (1.x.x) - Breaking changes
- **Minor version** (x.1.x) - New features, backward compatible
- **Patch version** (x.x.1) - Bug fixes, backward compatible

[unreleased]: https://github.com/yourusername/claude-code-memory/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/claude-code-memory/releases/tag/v1.0.0
[0.1.0]: https://github.com/yourusername/claude-code-memory/releases/tag/v0.1.0
