<p align="center">
  <img src="Memberberries.png" alt="Memberberries Logo" width="100">
</p>

# Memberberries

Persistent memory for Claude Code sessions.

Claude Code sessions are ephemeral—context resets on every conversation. Memberberries gives Claude a simple folder structure to store and retrieve insights across sessions.

## Philosophy

**Claude manages the memories.** Claude decides what to remember, what to archive, and what to retrieve. The system handles file I/O. Semantic search via `[RECALL]` is opt-in for when you need to find related berries without exact tags.

## Quick Start

```bash
git clone https://github.com/wylloh/memberberries.git
cd memberberries

# Add to PATH (or create alias)
echo 'export PATH="$PATH:$HOME/memberberries"' >> ~/.zshrc
source ~/.zshrc

# In your project
cd your-project
member setup
member
```

## How It Works

### Six Markers

Claude writes these in responses. Hooks parse and persist them.

| Marker | Effect |
|--------|--------|
| `[BERRY #tag] insight` | Save to Active Berries (global) |
| `[BERRY #tag @path] insight` | Anchor to location (spatial memory) |
| `[ARCHIVE id]` | Move berry to archive folder |
| `[RETRIEVE #tag]` | Pull archived berries into context |
| `[RECALL query]` | Semantic search across all berries |
| `[AUTOBERRY] state` | Save task checkpoint (overwrites previous) |

### Session Flow

1. **Start**: Active berries sync to CLAUDE.md
2. **Work**: Claude references berries, creates new ones
3. **End**: Markers parsed, files updated

### Spatial Memory

Anchor berries to locations with `@path`:

```
[BERRY #gotcha @src/auth/] JWT refresh tokens need rotation on use
```

This creates `MEMBERME.md` files in those directories—breadcrumbs Claude discovers while exploring the codebase. Like a memory palace, but for code.

```
src/
├── auth/
│   ├── MEMBERME.md      # "Here's what I know about this area"
│   ├── jwt.ts
│   └── session.ts
└── api/
    └── routes.ts
```

- Global berries (no `@path`): Show in CLAUDE.md at session start
- Located berries (`@path`): Discovered during navigation

### What Claude Sees

In CLAUDE.md at session start:
```markdown
## 📍 Checkpoint
**[2026-01-04 15:30]** Implementing auth | Login done | Next: token refresh

## Active Berries
- `a1b2c3d4` [2026-01-04] #auth: JWT in httpOnly cookies, not localStorage
- `b2c3d4e5` [2026-01-04] #debugging: Check nginx logs first for 502 @src/api/

## Archives
`#architecture` (3) · `#deployment` (5)
```

In `src/api/MEMBERME.md` while exploring:
```markdown
# 🫐 Memories for this area

- `b2c3d4e5` [2026-01-04] #debugging: Check nginx logs first for 502 errors

---
*Add memories here with: `[BERRY #tag @src/api/] Your insight`*
```

## Storage

```
your-project/
├── CLAUDE.md                    # Instructions + active berries
├── src/
│   └── auth/
│       └── MEMBERME.md          # Spatial breadcrumbs (gitignored)
└── .memberberries/
    ├── active.json              # Current berries (source of truth)
    └── archive/                 # By primary tag
        ├── architecture/
        ├── deployment/
        └── debugging/
```

- `active.json` is the source of truth for all berries
- `MEMBERME.md` files are auto-generated projections (gitignored)
- Everything is JSON. No black boxes.

## Commands

| Command | Description |
|---------|-------------|
| `member` | Sync and launch Claude Code |
| `member setup` | Configure hooks for project |
| `member status` | Berry counts, hook health |
| `member sync` | Sync only, don't launch |
| `member save` | Prompt Claude to write a checkpoint |
| `member upgrade` | Pull latest, update hooks and template |

## Requirements

- Python 3.8+
- Claude Code CLI
- `sentence-transformers` (optional, for `[RECALL]` semantic search)

### Semantic Search

`[RECALL]` uses sentence-transformers for semantic similarity search. To enable:

```bash
pip install sentence-transformers
```

**Note:** First use downloads the embedding model (~80MB). You'll see "Loading semantic model..." on cold start. Subsequent uses are instant.

## Design

~800 lines of Python. Core functionality uses stdlib only (file I/O and regex). Semantic search is the one optional dependency.

The system is scaffolding for Claude—structure and automation, not intelligence. Claude provides the intelligence.

## License

MIT
