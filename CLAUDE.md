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

*Synced: 2026-01-02 18:09*

**How to use this context:**
- 📌 Pinned = Protected info (credentials, configs) - preserve exactly
- ⚫ High Gravity = Frequently referenced - likely relevant
- 🎯 Active Task = Current focus area - prioritize these memories
- Memories ranked by importance; top items most critical

🎯 **Active Task: memory-analytics**
   Analytics and visualization for memberberries memory system

*Current query: Is there a way to automatically capture your responses/decisions? Those are at l...*

## High Priority
- **Repeated issue: to see:\n- Did the memory-analytics task gain mass**: (Auto-captured - user had to repeat this)
- **Repeated issue: in the **same conversation session** - I have full ctx of everything we discussed**: (Auto-captured - user had to repeat this)
- **Repeated issue: - we can see if the refreshed ctx helps**: (Auto-captured - user had to repeat this)

## Your Preferences
- **coding_style**: Use type hints and docstrs for all public fns
- **coding_style**: Follow conventional commits: feat:, fix:, docs:, etc.

## Relevant Solutions
- **How to test auto-concentrate**: Use --dry-run flag: py3 auto_concentrate.py --dry-run --text 'your text'

## Antipatterns (Avoid)
- **Don't**: edit below this line -->\n\n*Synced: 2026-01-02 18:07*\n\n**How to use this ctx:**\n- 📌 Pinned = Protected info (credentials,...
  - *Why*: Not recommended
  - *Instead*: this ctx:**\n- 📌 Pinned = Protected info (credentials, configs) - preserve exactly\n- ⚫ High Gravity = Frequently referenced - likely relevant\n- 🎯 Active Task = curr focus area -...
<!-- END MEMBERBERRIES -->
