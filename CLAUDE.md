# Memberberries

## Project Overview

Memberberries is a persistent memory system for Claude Code. It automatically captures insights from coding sessions and provides relevant context on every prompt - like having a perfect memory of everything you've ever worked on.

## Architecture

**Pattern**: Modular Python CLI with hook-based Claude Code integration

**Core Components:**
- `member.py` - Main entry point, hooks, setup wizard
- `auto_concentrate.py` - Automatic memory extraction with semantic signals
- `berry_manager.py` - Memory storage, embeddings, semantic search
- `memberberries.py` - Manual CLI for power users

**Data Flow:**
```
User prompt → [Hook: Sync] → CLAUDE.md updated
Claude responds → [Hook: Concentrate] → Memories extracted
```

## Tech Stack

- Python 3.8+
- NumPy (embeddings)
- JSON file storage (default)
- Optional: ChromaDB, sentence-transformers

## Conventions

- Use type hints everywhere
- Follow PEP 8
- Docstrings for public functions
- Conventional commits (feat:, fix:, docs:)
- Keep functions focused and small

## Key Concepts

- **Concentrate** = Store a memory
- **Juice** = Retrieve relevant memories
- **Berries** = Individual memory items
- **Signals** = Semantic indicators (again, please, thanks, etc.)

## Important Notes

- All data is local-first (no cloud)
- CLAUDE.md has a memberberries section (below delimiter) - don't edit manually
- Hooks auto-sync on every prompt
- "again" signals get highest priority (was forgotten!)

---

<!-- MEMBERBERRIES CONTEXT - Auto-managed, do not edit below this line -->

*Context synced: 2026-01-02 15:54*
*Query: implementing memory features*

## Your Preferences
- **coding_style**: Use type hints and docstrings for all public functions
- **coding_style**: Follow conventional commits: feat:, fix:, docs:, etc.

## Relevant Solutions
- **How to test auto-concentrate**: Use --dry-run flag: python3 auto_concentrate.py --dry-run --text 'your text'
<!-- END MEMBERBERRIES -->
