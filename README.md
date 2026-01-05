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

### Four Markers

Claude writes these in responses. Hooks parse and persist them.

| Marker | Effect |
|--------|--------|
| `[BERRY #tag] insight` | Save knowledge to Active Berries |
| `[ARCHIVE id]` | Move berry to archive folder |
| `[RETRIEVE #tag]` | Pull archived berries into context |
| `[AUTOBERRY] state` | Save task checkpoint (overwrites previous) |

### Session Flow

1. **Start**: Active berries sync to CLAUDE.md
2. **Work**: Claude references berries, creates new ones
3. **End**: Markers parsed, files updated

### What Claude Sees

```markdown
## 📍 Checkpoint
**[2026-01-04 15:30]** Implementing auth | Login done | Next: token refresh

↳ Continue from here. Write `[AUTOBERRY]` to update.

## Active Berries
- `a1b2c3d4` [2026-01-04] #auth: JWT in httpOnly cookies, not localStorage
- `b2c3d4e5` [2026-01-04] #debugging: Check nginx logs first for 502 errors

## Archives
`#architecture` (3) · `#deployment` (5)
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
| `member save` | Prompt Claude to write a checkpoint |
| `member upgrade` | Pull latest, update hooks and template |

## Requirements

- Python 3.8+
- Claude Code CLI

## Design

~800 lines of Python. No dependencies beyond stdlib. Just file I/O and regex.

The system is scaffolding for Claude—structure and automation, not intelligence. Claude provides the intelligence.

## License

MIT
