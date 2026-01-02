# Claude Code Compatibility Guide

This document explains how Memberberries integrates with Claude Code and ensures they work together seamlessly.

## How Memberberries Works With Claude Code

Memberberries enhances Claude Code through **native integration**:

```
$ member "implement auth"
      ↓
[1] Syncs relevant memories → CLAUDE.md (memberberries section)
[2] Launches Claude Code
      ↓
Every prompt you type:
  → [UserPromptSubmit Hook] Updates CLAUDE.md with relevant context
  → Claude processes your prompt with fresh memories
  → [Stop Hook] Auto-extracts insights from Claude's response
      ↓
Memory builds automatically as you work
```

### The Integration

Memberberries manages a **dedicated section** at the bottom of your `CLAUDE.md`:

```markdown
# My Project

## Project Overview
Your static project description...

## Conventions
Your coding standards...

---

<!-- MEMBERBERRIES CONTEXT - Auto-managed, do not edit below this line -->

*Context synced: 2024-01-15 10:30*
*Query: implement authentication*

## Your Preferences
- **coding_style**: Always use type hints

## Relevant Solutions
- **JWT refresh tokens**: Store in Redis with 7-day TTL

<!-- END MEMBERBERRIES -->
```

**Key points:**
- Your content above the delimiter is **never touched**
- Memberberries only manages its own section
- Context updates automatically on every prompt via hooks

## Feature Comparison

| Feature | Claude Code Native | Memberberries | How They Work Together |
|---------|-------------------|---------------|------------------------|
| **Project Instructions** | `CLAUDE.md` (static) | Dynamic context section | Memberberries adds to CLAUDE.md, doesn't replace |
| **Session Memory** | Within conversation | Persistent across sessions | Memberberries bridges sessions |
| **Context Loading** | Reads CLAUDE.md at start | Syncs on every prompt | Hooks keep context fresh |
| **Learning** | None | Auto-captures insights | Stop hook extracts from responses |
| **Semantic Search** | None | Full semantic search | Find relevant memories by meaning |

## The Hook System

Memberberries uses Claude Code's native hook system:

### UserPromptSubmit Hook
- **When**: Before each prompt is processed
- **What**: Syncs relevant memories based on your prompt
- **How**: Updates the memberberries section of CLAUDE.md

### Stop Hook
- **When**: After Claude finishes responding
- **What**: Extracts insights from the conversation
- **How**: Auto-concentrates solutions, patterns, and learnings

### Semantic Signal Detection

The auto-concentrate system monitors for strategic signals:

| Signal | Examples | Priority |
|--------|----------|----------|
| **Repetition** | "again", "still", "keep getting" | Highest (was forgotten!) |
| **Success** | "that worked", "perfect", "thanks" | High (confirmed solution) |
| **Emphasis** | "important", "remember", "critical" | High (explicit request) |
| **Request** | "please", "help me", "how do I" | Medium (user need) |
| **Failure** | "doesn't work", "broke", "error" | Medium (learning opportunity) |

## Setup Verification

After running `member setup`, verify integration:

```bash
member --status
```

Should show:
```
Memberberries Status
   Project: /path/to/your/project
   Storage: ~/.memberberries
   CLAUDE.md: exists
   Claude Code: installed
   Hooks: configured    ← Important!

   Memories:
     - solutions: 5
     - preferences: 3
     ...
```

Check hooks are registered:
```bash
# In Claude Code, run:
/hooks
```

Should list `UserPromptSubmit` and `Stop` hooks pointing to memberberries scripts.

## Avoiding Conflicts

### Do's
- Use the **top section** of CLAUDE.md for static project rules
- Let memberberries manage the **bottom section** automatically
- Start sessions with `member` instead of `claude`
- Trust the automatic memory capture

### Don'ts
- Don't manually edit the memberberries section (between the delimiters)
- Don't duplicate information in both sections
- Don't run `claude` directly if you want memory features (use `member`)

## When to Use What

### Put in CLAUDE.md (top section):
- Project name and description
- Architecture overview
- Coding standards and conventions
- File structure explanations
- Static rules that never change

### Let Memberberries Handle:
- Solutions you've discovered
- Error patterns and fixes
- What worked and what didn't
- Preferences that evolve
- Session-to-session context

## Version Compatibility

| Memberberries | Claude Code | Status |
|---------------|-------------|--------|
| v1.1+ | Current | Full integration via hooks |
| v1.0 | All | Manual workflow (copy-paste) |

## Troubleshooting

### "Hooks not configured"
```bash
# Re-run setup
member setup

# Or manually in your project:
cd /your/project
python3 /path/to/memberberries/member.py setup
```

### "Context not updating"
1. Check hooks: Run `/hooks` in Claude Code
2. Verify paths in `.claude/settings.json`
3. Check hook scripts are executable: `ls -la .claude/hooks/`

### "CLAUDE.md has conflicts"
The memberberries section is between special delimiters. If you see issues:
```bash
# Clean the memberberries section
member --clean

# Re-sync
member --sync-only
```

## Future Claude Code Features

If Claude Code adds native memory features:

1. **We'll adapt**: Memberberries will integrate, not compete
2. **Unique value remains**: Semantic search, cross-project memory, auto-extraction
3. **Migration path**: Export your memories anytime with `memberberries.py export`

## Reporting Issues

If you encounter compatibility problems:

1. Run `member --status` and note the output
2. Check `.claude/settings.json` for hook configuration
3. Create an issue at [github.com/wylloh/memberberries/issues](https://github.com/wylloh/memberberries/issues) with:
   - Your `member --status` output
   - Claude Code version
   - Description of the issue
