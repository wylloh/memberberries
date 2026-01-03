# 🫐 Memberberries

<p align="center">
  <img src="Memberberries.svg" alt="Memberberries Logo" width="200"/>
</p>

### *Member when Claude Code... didn't?*

> Persistent memory system for Claude Code - because AI assistants deserve to remember too.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

## What is this?

Memberberries is a lightweight, file-based memory system that enables Claude Code to remember:
- **Your preferences** - coding style, favorite tools, workflows
- **Project context** - architecture decisions, tech stack, conventions
- **Past solutions** - problems you've solved and how
- **Session history** - what you accomplished each day
- **Error patterns** - debugging insights and resolutions
- **Antipatterns** - what NOT to do and why
- **Git conventions** - commit style, branch naming, PR templates
- **Dependencies** - library preferences, version constraints, gotchas
- **Testing patterns** - test strategies, frameworks, mocking approaches
- **Environment configs** - local, Docker, CI setup notes
- **API notes** - rate limits, auth patterns, service quirks

Instead of starting fresh every time, Claude Code picks up where you left off.

## Key Features

- **Semantic Search** - Find relevant memories by meaning, not just keywords
- **Local-First** - All data stays on your machine, zero cloud dependencies
- **Zero Config** - Works out of the box, no setup required
- **Extensible** - Plugin architecture for embeddings and storage backends
- **Human-Readable** - All data stored in JSON/markdown files
- **Lightweight** - Just Python + numpy, no heavy dependencies
- **Secure** - File permissions (0600), sensitive data warnings
- **Flexible Storage** - Global (`~/.memberberries`) or per-project (`.memberberries/`)

## Quick Start

```bash
# Clone and run setup
git clone https://github.com/wylloh/memberberries.git
cd memberberries
bash setup.sh
```

The setup wizard will:
1. Install dependencies
2. Check for Claude Code (help install if needed)
3. Run interactive project setup
4. Configure hooks for automatic context sync
5. Install the `member` command globally

See [QUICKSTART.md](QUICKSTART.md) for the full guide.

### Seamless Workflow

```bash
# Start a session - just like 'claude' but with memory
member "implement user authentication"

# That's it! Memberberries:
# 1. Syncs relevant memories into CLAUDE.md
# 2. Launches Claude Code
# 3. Hooks keep context fresh on EVERY prompt throughout the session
```

The `member` command is a drop-in enhancement for `claude`:
- Your existing CLAUDE.md content is preserved
- Memberberries manages its own section (below a delimiter)
- Context automatically updates based on what you're working on

### AI-Powered Deep Scan (New!)

For complex tasks, use AI to intelligently select the most relevant memories:

```bash
# Configure your API key (one-time setup)
member config api-key sk-ant-your-key-here

# Deep scan for task-specific context
member deep "implement OAuth authentication"

# Filter by memory type
member deep "fix database issues" --types errors,solutions

# Set as active task focus
member deep "refactor payment module" --focus
```

Deep scan uses Claude Haiku (~$0.001/scan) to semantically analyze your entire memory store and select the 5-15 most relevant memories for your task.

### Building Your Memory

```bash
# Store a coding preference
python memberberries.py concentrate coding_style \
  "Always use type hints and docstrings" \
  -t python,style

# Store a solution you discovered
python memberberries.py concentrate-solution \
  "How to handle JWT refresh" \
  "Use Redis with 7-day expiry" \
  -t auth,jwt

# Store an error pattern you solved
python memberberries.py concentrate-error \
  "ModuleNotFoundError: numpy" \
  "Use conda on M1 Mac, not pip"
```

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  $ member "implement auth"                                  │
│     ↓                                                       │
│  1. Syncs relevant memories → CLAUDE.md                     │
│  2. Launches Claude Code                                    │
│     ↓                                                       │
│  You're now in Claude Code with your context loaded!        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Every prompt you type:                              │   │
│  │    → Hook triggers memberberries sync               │   │
│  │    → CLAUDE.md updates with relevant context        │   │
│  │    → Claude processes your prompt with fresh memory │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Context stays relevant throughout your entire session!     │
└─────────────────────────────────────────────────────────────┘
```

### Interactive Project Setup

When you run `member init` or `member setup`, the wizard helps you create CLAUDE.md:

```
$ member init

============================================================
  MEMBERBERRIES PROJECT SETUP WIZARD
============================================================

Setting up: my-awesome-project

Describe your project in 1-2 sentences:
  (Enter to skip, ? for suggestions): ?
  Suggested: A microservices project using Python, FastAPI, Docker
  Use this? [Y/n]:

What's your project architecture?
  [1] Monolith
  [2] Microservices
  [3] Serverless
  ...
  [?] Suggest based on codebase

Detected tech stack: Python, FastAPI, pytest, Docker
Add or modify? [Enter to confirm]:

Coding conventions (one per line, empty line to finish):
  > Use type hints everywhere
  > Prefer async functions for I/O
  >
```

### What Gets Synced

```bash
$ member "add rate limiting to API"

🫐 Juicing memberberries...

=== MEMBERBERRIES FROM YOUR PREFERENCES ===
- Use async functions for I/O operations
- Prefer Redis for caching and rate limiting
- Always add comprehensive error handling

=== MEMBERBERRIES FROM YOUR PROJECT ===
Project: My API
Architecture: Clean Architecture with FastAPI
Tech Stack: FastAPI, PostgreSQL, Redis

=== RELEVANT MEMBERBERRIES ===
Problem: How to implement rate limiting in FastAPI
Solution: Use slowapi with Redis backend...
```

### Copy → Paste into Claude Code → Enhanced Context!

Claude Code now members:
- Your coding style and preferences
- Your project's architecture
- Solutions to similar problems you've solved
- Relevant code patterns and conventions

## Results

| Without Memberberries | With Memberberries |
|----------------------|-------------------|
| Repeats same questions each session | Memberberries preferences |
| Suggests generic solutions | Tailored to your project |
| No awareness of past work | Memberberries previous solutions |
| Starts from scratch | Continues seamlessly |

## Documentation

- [**Quick Start Guide**](QUICKSTART.md) - Get up and running in 60 seconds
- [**Architecture Overview**](ARCHITECTURE.md) - System design and internals
- [**Vector DB Upgrade**](VECTOR_DB_UPGRADE.md) - Scaling to 10,000+ memories
- [**Contributing Guide**](CONTRIBUTING.md) - How to contribute

## Example Workflows

### Daily Coding Workflow

```bash
# Morning: Juice memberberries from yesterday
python juice.py "continue yesterday's work" ~/project

# During: Concentrate new insights as they happen
python memberberries.py concentrate-solution \
  "How to handle JWT refresh tokens" \
  "Store in Redis with 7-day expiry" \
  -t auth,jwt,security

# Concentrate an error pattern you solved
python memberberries.py concentrate-error \
  "ModuleNotFoundError: No module named 'numpy'" \
  "Install via conda on M1 Mac, not pip" \
  -t python,macos,m1

# Concentrate an antipattern to avoid
python memberberries.py concentrate-antipattern \
  "Using moment.js for date formatting" \
  "Causes massive bundle bloat (300KB+)" \
  "Use date-fns or native Intl.DateTimeFormat" \
  -t javascript,performance

# Concentrate git conventions
python memberberries.py concentrate-git-convention \
  commit_message \
  "type(scope): description" \
  "feat(auth): add JWT refresh token support" \
  -t conventional-commits

# Evening: Concentrate session summary
python memberberries.py concentrate-session \
  "Implemented JWT auth with refresh tokens" \
  -l "Use Redis for token storage|Always validate expiry|Rotate tokens on use"
```

### Per-Project Storage

```bash
# Initialize per-project storage (adds to .gitignore too)
python memberberries.py init-gitignore ~/my-project

# Use local storage for this project
python memberberries.py --local concentrate-dependency \
  fastapi -v ">=0.100.0" -n "Required for lifespan support"

# Force global storage
python juice.py --global "implement auth" ~/my-project
```

### Searching Your Memberberries

```bash
# Find relevant memberberries
python memberberries.py search "database connection pooling"

# Results are ranked by semantic similarity
1. How to handle database connections in FastAPI
   Solution: Use lifespan context manager with connection pooling...
```

## Command Reference

### Core Commands

| Command | Description |
|---------|-------------|
| `member "task"` | Sync context and launch Claude Code |
| `member init` | Interactive project setup wizard |
| `member setup` | Full installation wizard |
| `member sync` | Sync CLAUDE.md without launching Claude |

### Memory Management

| Command | Description |
|---------|-------------|
| `member stats` | View memory analytics and distribution |
| `member lookup <id>` | Get full content of a memory by ID |
| `member expand` | Show all memories in full detail |
| `member refresh` | Output context for mid-session refresh |
| `member context` | Show current CLAUDE.md memberberries section |

### Task & Focus

| Command | Description |
|---------|-------------|
| `member deep "task"` | AI-powered context selection for task |
| `member focus <task-id>` | Set active task for priority context |
| `member focus --clear` | Clear active task focus |
| `member tasks` | List all task clusters |
| `member feedback <id> useful` | Mark memory as useful (+gravity) |
| `member feedback <id> not-useful` | Mark memory as not useful (-gravity) |

### Configuration

| Command | Description |
|---------|-------------|
| `member config` | View current configuration |
| `member config api-key <key>` | Set Anthropic API key for deep scan |

### Pinned Memories

| Command | Description |
|---------|-------------|
| `member pin "name" "content"` | Create a pinned memory |
| `member pins` | List all pinned memories |
| `member unpin <id>` | Remove a pinned memory |

## Advanced Features

### Upgrade to Better Embeddings

```bash
# Install sentence transformers for better juicing
pip install sentence-transformers

# Update berry_manager.py to use it
# See VECTOR_DB_UPGRADE.md for details
```

### Apple Silicon (M1/M2/M3) Setup

For native arm64 performance on Apple Silicon Macs:

```bash
# Install Homebrew Python (arm64 native)
brew install python@3.11

# Install dependencies
/opt/homebrew/bin/python3.11 -m pip install numpy anthropic

# Update hooks to use Homebrew Python
# Edit .claude/hooks/*.sh and set:
# PYTHON="/opt/homebrew/bin/python3.11"
```

The setup script handles this automatically on Apple Silicon.

### Optional Vector Database

For 10,000+ memberberries, upgrade to ChromaDB:

```bash
pip install chromadb
python migrate_to_chromadb.py
```

See [Vector DB Upgrade Guide](VECTOR_DB_UPGRADE.md) for details.

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to report bugs
- How to suggest features
- Pull request process
- Coding standards

**Good first issues:** Look for issues tagged `good-first-issue`

## Roadmap

### v1.0
- ✅ File-based berry storage
- ✅ Semantic juicing
- ✅ CLI interface
- ✅ Claude Code integration

### v1.1
- ✅ Extended memory types (errors, antipatterns, git, deps, testing, env, API)
- ✅ Per-project storage support
- ✅ Security features (file permissions, sensitive data warnings)
- ✅ Gitignore integration
- ✅ Seamless `member` command with hook-based sync
- ✅ Interactive project setup wizard
- ✅ Auto-detection of tech stack and architecture
- ✅ Claude Code installation guidance

### v1.2 (Current)
- ✅ AI-powered deep scan (`member deep`) using Claude Haiku
- ✅ Memory ID system for token-efficient context
- ✅ Memory lookup by ID (`member lookup`)
- ✅ Gravitational memory clustering (task-based organization)
- ✅ Memory feedback system (useful/not-useful)
- ✅ Pinned memories for critical context
- ✅ Auto-capture of Claude's decisions and summaries
- ✅ Apple Silicon (arm64) native support
- ✅ Staleness decay for aging memories
- [ ] Vector database support (optional)
- [ ] Better embedding models for juicing
- [ ] Test coverage

### v2.0 (Future)
- [ ] Web UI for browsing memberberries
- [ ] Team sharing (encrypted berries)
- [ ] Claude Code plugin/extension
- [ ] Multi-model support for deep scan

## Performance

| Metric | File Storage | ChromaDB (Optional) |
|--------|-------------|---------------------|
| Search (100 items) | ~10ms | ~5ms |
| Search (1,000 items) | ~100ms | ~10ms |
| Search (10,000 items) | ~1s | ~15ms |
| Storage (1,000 items) | ~3MB | ~5MB |

## Acknowledgments

Inspired by the need for continuity in coding sessions with Claude Code. Built to be:
- Simple enough for anyone to use
- Powerful enough for heavy users
- Private and local-first
- Easy to extend and customize

*Member when AI had no memory?* 🫐

## License

MIT License - see [LICENSE](LICENSE) for details

## Links

- [Report a Bug](https://github.com/wylloh/memberberries/issues)
- [Request a Feature](https://github.com/wylloh/memberberries/issues)
- [Discussions](https://github.com/wylloh/memberberries/discussions)

---

**Made with lurve for the Claude Code community**

Star this repo if it helps you member better 🫐
