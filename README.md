# 🫐 Memberberries

<p align="center">
  <img src="Memberberries.svg" alt="Memberberries Logo" width="200"/>
</p>

### *Member when Claude Code remembered everything?*

> Persistent memory system for Claude Code - because AI assistants deserve to remember too.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

## 🎯 What is this?

Memberberries is a lightweight, file-based memory system that enables Claude Code to remember:
- **Your preferences** - coding style, favorite tools, workflows
- **Project context** - architecture decisions, tech stack, conventions
- **Past solutions** - problems you've solved and how
- **Session history** - what you accomplished each day

Instead of starting fresh every time, Claude Code picks up where you left off.

## ✨ Key Features

- 🔍 **Semantic Search** - Find relevant memories by meaning, not just keywords
- 📁 **Local-First** - All data stays on your machine, zero cloud dependencies
- 🚀 **Zero Config** - Works out of the box, no setup required
- 🔌 **Extensible** - Plugin architecture for embeddings and storage backends
- 📝 **Human-Readable** - All data stored in JSON/markdown files
- ⚡ **Lightweight** - Just Python + numpy, no heavy dependencies

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/memberberries.git
cd memberberries

# Run the setup script
bash setup.sh

# Or install manually
pip install -r requirements.txt
python demo.py
```

### Basic Usage

```bash
# Concentrate a coding preference (store a memory)
python memberberries.py concentrate coding_style \
  "Always use type hints and docstrings" \
  -t python,style

# Juice some context for your current task (fetch memories)
python juice.py "implement user authentication" ~/my-project

# Copy the output and paste it into Claude Code
# Claude now memberberries your preferences, project setup, and past solutions!
```

## 📖 How It Works

### Before Claude Code Session
```bash
$ python juice.py "add rate limiting to API" ~/my-project

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

Claude Code now memberberries:
- Your coding style and preferences
- Your project's architecture
- Solutions to similar problems you've solved
- Relevant code patterns and conventions

## 📊 Results

| Without Memberberries | With Memberberries |
|----------------------|-------------------|
| Repeats same questions each session | Memberberries preferences |
| Suggests generic solutions | Tailored to your project |
| No awareness of past work | Memberberries previous solutions |
| Starts from scratch | Continues seamlessly |

## 📚 Documentation

- [**Quick Start Guide**](QUICKSTART.md) - Get up and running in 60 seconds
- [**Architecture Overview**](ARCHITECTURE.md) - System design and internals
- [**Vector DB Upgrade**](VECTOR_DB_UPGRADE.md) - Scaling to 10,000+ memories
- [**Contributing Guide**](CONTRIBUTING.md) - How to contribute

## 💡 Example Workflows

### Daily Coding Workflow

```bash
# Morning: Juice memberberries from yesterday
python juice.py "continue yesterday's work" ~/project

# During: Concentrate new insights as they happen
python memberberries.py concentrate-solution \
  "How to handle JWT refresh tokens" \
  "Store in Redis with 7-day expiry" \
  -t auth,jwt,security

# Evening: Concentrate session summary
python memberberries.py concentrate-session \
  "Implemented JWT auth with refresh tokens" \
  -l "Use Redis for token storage|Always validate expiry|Rotate tokens on use"
```

### Searching Your Memberberries

```bash
# Find relevant memberberries
python memberberries.py search "database connection pooling"

# Results are ranked by semantic similarity
1. How to handle database connections in FastAPI
   Solution: Use lifespan context manager with connection pooling...
```

## 🛠️ Advanced Features

### Upgrade to Better Embeddings

```bash
# Install sentence transformers for better juicing
pip install sentence-transformers

# Update berry_manager.py to use it
# See VECTOR_DB_UPGRADE.md for details
```

### Optional Vector Database

For 10,000+ memberberries, upgrade to ChromaDB:

```bash
pip install chromadb
python migrate_to_chromadb.py
```

See [Vector DB Upgrade Guide](VECTOR_DB_UPGRADE.md) for details.

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to report bugs
- How to suggest features
- Pull request process
- Coding standards

**Good first issues:** Look for issues tagged `good-first-issue`

## 🗺️ Roadmap

### v1.0 (Current)
- ✅ File-based berry storage
- ✅ Semantic juicing
- ✅ CLI interface
- ✅ Claude Code integration

### v1.1 (Next)
- [ ] Vector database support (optional)
- [ ] Better embedding models for juicing
- [ ] Test coverage
- [ ] Migration tools

### v2.0 (Future)
- [ ] Web UI for browsing memberberries
- [ ] Auto-concentration from transcripts
- [ ] Team sharing (encrypted berries)
- [ ] Git integration
- [ ] Claude Code plugin/extension

## 📈 Performance

| Metric | File Storage | ChromaDB (Optional) |
|--------|-------------|---------------------|
| Search (100 items) | ~10ms | ~5ms |
| Search (1,000 items) | ~100ms | ~10ms |
| Search (10,000 items) | ~1s | ~15ms |
| Storage (1,000 items) | ~3MB | ~5MB |

## 🙏 Acknowledgments

Inspired by the need for continuity in coding sessions with Claude Code. Built to be:
- Simple enough for anyone to use
- Powerful enough for heavy users
- Private and local-first
- Easy to extend and customize

*Member when AI had no memory?* 🫐

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## 🔗 Links

- [Report a Bug](https://github.com/yourusername/memberberries/issues)
- [Request a Feature](https://github.com/yourusername/memberberries/issues)
- [Discussions](https://github.com/yourusername/memberberries/discussions)

---

**Made with ❤️ for the Claude Code community**

⭐ Star this repo if it helps you memberberry better!
