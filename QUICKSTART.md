# Quick Start

## Install

```bash
git clone https://github.com/wylloh/memberberries.git
cd memberberries

# Add to PATH
echo 'export PATH="$PATH:'$(pwd)'"' >> ~/.zshrc
source ~/.zshrc
```

## Set Up a Project

```bash
cd your-project
member setup
```

This creates:
- `.memberberries/` folder for storage
- Hooks in `.claude/hooks/`
- Memberberries section in `CLAUDE.md`

## Use It

```bash
member
```

That's it. Claude Code launches with your berries synced.

## Create Berries

In any response, Claude can write:

```
[BERRY #architecture #api] REST endpoints use snake_case, responses use camelCase
```

The hook captures this and stores it.

## Archive Old Berries

When context drifts:

```
[ARCHIVE a1b2c3d4]
```

Berry moves to `.memberberries/archive/{primary_tag}/`.

## Retrieve from Archive

Need old context?

```
[RETRIEVE #deployment]
```

Archived berries with that tag appear on next sync.

## Check Status

```bash
member status
```

Shows berry counts, archive summary, hook health.

## That's It

- Berries persist across sessions
- Claude manages what to remember
- Everything is JSON files you can inspect
