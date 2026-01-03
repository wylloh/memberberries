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

*Synced: 2026-01-02 17:52*

**How to use this context:**
- 📌 Pinned = Protected info (credentials, configs) - preserve exactly
- ⚫ High Gravity = Frequently referenced - likely relevant
- Memories are ranked by importance; top items most critical

*Current focus: Yes, let's please commit, and then work on implementing your suggestions! And is...*

## Your Preferences
- **coding_style**: Follow conventional commits: feat:, fix:, docs:, etc.
- **coding_style**: Use type hints and docstrs for all public fns

## Relevant Solutions
- **User need: proceed with the curr tasks if applicable'}]}

{'model': 'claude-opus-4-5-20251101', 'id': 'msg_019YzHxdzC28enzgaaJ1pUmS', 'type': 'msg', 'role': 'assistant',...**: (Captured from conversation - pending resolution)
- **How to test auto-concentrate**: Use --dry-run flag: py3 auto_concentrate.py --dry-run --text 'your text'
- **User need: proceed with the curr tasks if applicable'}]}

{'model': 'claude-opus-4-5-20251101', 'id': 'msg_016fz9ETaQzXxJaPd4eir2m7', 'type': 'msg', 'role': 'assistant',...**: (Captured from conversation - pending resolution)
<!-- END MEMBERBERRIES -->
