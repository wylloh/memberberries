# Memberberries

Persistent memory for Claude Code sessions.

Claude Code sessions are ephemeral—context resets on every conversation. Memberberries gives Claude a simple folder structure to store and retrieve insights across sessions.

## Philosophy

**Claude manages the memories.** No embeddings, no search algorithms, no AI trying to guess what's relevant. Claude decides what to remember, what to archive, and what to retrieve. The system just handles file I/O.

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

### Three Markers

Claude writes these in responses. Hooks parse and persist them.

| Marker | Effect |
|--------|--------|
| `[BERRY #tag1 #tag2] insight` | Save a new berry |
| `[ARCHIVE id]` | Move berry to archive folder |
| `[RETRIEVE #tag]` | Pull archived berries into context |

### Session Flow

1. **Start**: Active berries sync to CLAUDE.md
2. **Work**: Claude references berries, creates new ones
3. **End**: Markers parsed, files updated

### What Claude Sees

```markdown
## Berry Instructions
Write `[BERRY #tag1 #tag2] one-line insight` to save a berry.
Write `[ARCHIVE id]` to archive a berry.
Write `[RETRIEVE #tag]` to pull archived berries into context.

## Active Berries
- `a1b2c3d4` [2026-01-04] #architecture #auth: JWT in httpOnly cookies, not localStorage
- `b2c3d4e5` [2026-01-04] #debugging: Check nginx logs first for 502 errors

## Available Archives
`#architecture` (3) · `#deployment` (5) · `#debugging` (8)
```

## Storage

```
your-project/
├── CLAUDE.md                    # Instructions + active berries
└── .memberberries/
    ├── active.json              # Current berries
    └── archive/                 # By primary tag
        ├── architecture/
        ├── deployment/
        └── debugging/
```

Everything is JSON. No black boxes.

## Commands

| Command | Description |
|---------|-------------|
| `member` | Sync and launch Claude Code |
| `member setup` | Configure hooks for project |
| `member status` | Berry counts, hook health |
| `member sync` | Sync only, don't launch |
| `member upgrade` | Pull latest memberberries, re-sync template (preserves berries) |

## Requirements

- Python 3.8+
- Claude Code CLI

## Design

~600 lines of Python. No numpy. No ML dependencies. Just file I/O and regex.

The system is scaffolding for Claude to work within—structure and automation, not intelligence. Claude provides the intelligence.

## License

MIT
