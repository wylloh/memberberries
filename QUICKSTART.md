# Quick Start Guide

Get memberberries working in under 2 minutes.

## Installation

```bash
# Clone the repository
git clone https://github.com/wylloh/memberberries.git
cd memberberries

# Run setup (installs dependencies + launches wizard)
bash setup.sh
```

The wizard will:
1. Check for Claude Code (help you install if needed)
2. Set up your project's CLAUDE.md interactively
3. Configure hooks for automatic context sync
4. Install the `member` command

## Basic Usage

### Start a Session

```bash
# Navigate to your project
cd ~/my-project

# Start with memberberries context
member "implement user authentication"

# Or just start with general context
member
```

That's it! You're now in Claude Code with your memories loaded.

### Context Syncs Automatically

Every prompt you type in Claude Code will:
1. Trigger the memberberries hook
2. Search for relevant memories
3. Update CLAUDE.md with fresh context
4. Claude sees your memories before responding

No manual steps needed during your session.

## Automatic Memory Building

Memberberries automatically captures insights as you work:

- **Solutions** - When Claude explains how to fix something
- **Error patterns** - When you encounter and resolve errors
- **Antipatterns** - When Claude warns against certain approaches
- **Dependencies** - When packages are recommended

You don't need to do anything - just code normally and your memory builds itself.

### How It Works

```
You type a prompt
    ↓
[Hook 1: Sync] - Loads relevant memories into CLAUDE.md
    ↓
Claude responds
    ↓
[Hook 2: Concentrate] - Extracts and stores new insights
    ↓
Next prompt has even better context
```

### Optional Manual Entry

If you want to explicitly store something:

```bash
# Store a preference
python3 memberberries.py concentrate coding_style \
  "Always use type hints" -t python

# Store a session summary
python3 memberberries.py concentrate-session \
  "What I accomplished today"
```

But this is optional - the system learns automatically.

## Useful Commands

| Command | What it does |
|---------|-------------|
| `member` | Start session with context |
| `member "task"` | Start session focused on task |
| `member --status` | Show memberberries status |
| `member init` | Re-run project setup wizard |
| `member --clean` | Remove memberberries from CLAUDE.md |
| `python3 memberberries.py stats` | Show memory statistics |
| `python3 memberberries.py search "query"` | Search your memories |

## Project Setup

If you need to set up a new project:

```bash
cd ~/new-project
member init
```

The wizard will:
- Auto-detect your tech stack
- Suggest architecture based on structure
- Let you add conventions and notes
- Create a populated CLAUDE.md

## Tips

1. **Just start coding** - Memories are captured automatically
2. **Use `member` instead of `claude`** - Ensures hooks are active
3. **Check your memories** - Run `member --status` to see what's stored
4. **It gets smarter over time** - The more you use it, the better context you get

## Troubleshooting

**"Building your memory..."**
- This is normal for new projects
- Memories are captured automatically as you work
- The more you use memberberries, the richer your context

**"claude command not found"**
- Run `member setup` to install Claude Code

**"Hooks not working"**
- Check status: `member --status`
- Re-run setup: `member setup`

## Next Steps

1. Start using `member` instead of `claude`
2. Store your first preference or solution
3. Watch your context improve over time
4. See [README.md](README.md) for advanced features

---

*Member when you had to repeat yourself every session?*
