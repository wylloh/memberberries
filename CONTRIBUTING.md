# Contributing to Memberberries

Thank you for your interest in contributing! Memberberries makes Claude Code smarter by providing persistent memory across sessions.

## Project Vision

Create a seamless memory system that:
- Works automatically with zero manual entry
- Respects user privacy (local-first, all data on your machine)
- Learns from natural conversation
- Gets smarter over time

## Getting Started

### Development Setup

```bash
# 1. Fork the repository on GitHub
# https://github.com/wylloh/memberberries

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/memberberries.git
cd memberberries

# 3. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Test the setup
python3 member.py --status

# 6. Run tests (when available)
python -m pytest tests/
```

### Project Structure

```
memberberries/
├── member.py              # Main entry point - the 'member' command
├── memberberries.py       # CLI for manual memory operations
├── berry_manager.py       # Core memory storage and search
├── auto_concentrate.py    # Automatic memory extraction
├── juice.py               # Context retrieval utility
├── storage_backends.py    # Pluggable storage (file, ChromaDB)
├── setup.sh               # One-command installation
├── install_member.sh      # Member command installer
├── templates/
│   └── gitignore_template # For per-project storage
├── README.md
├── QUICKSTART.md
├── ARCHITECTURE.md
├── COMPATIBILITY.md
├── CONTRIBUTING.md        # You are here
├── RELEASING.md
├── VECTOR_DB_UPGRADE.md
└── requirements.txt
```

### Key Components

| File | Purpose |
|------|---------|
| `member.py` | Seamless Claude Code integration, hooks, setup wizard |
| `auto_concentrate.py` | Automatic insight extraction with semantic signals |
| `berry_manager.py` | Memory storage, search, and retrieval |
| `memberberries.py` | Manual CLI for power users |

## How to Contribute

### Reporting Bugs

Before creating a bug report:
- Check if the issue already exists
- Run `member --status` to gather system info
- Try to reproduce with minimal steps

Create an issue with:
- **Clear title**: "Hooks not triggering on macOS"
- **Description**: What happened vs. what you expected
- **Steps to reproduce**: Minimal steps to trigger the bug
- **Environment**: OS, Python version, `member --status` output
- **Logs**: Any error messages

### Suggesting Features

We love feature ideas! Good feature requests include:
- **Use case**: Why do you need this?
- **Proposal**: How should it work?
- **Alignment**: Does it fit the "automatic, seamless" vision?

### Code Contributions

#### Priority Areas

**High Priority:**
1. Test coverage (we need tests!)
2. Bug fixes
3. Signal detection improvements (auto_concentrate.py)
4. Documentation

**Medium Priority:**
1. Better embedding models
2. Additional storage backends
3. Performance optimizations
4. New memory types

**Future/Big Features:**
1. Web UI for browsing memories
2. Team sharing (encrypted)
3. Cross-project memory search
4. Analytics dashboard

#### Pull Request Process

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/better-signal-detection
   # or
   git checkout -b fix/hook-path-issue
   ```

2. **Make your changes**:
   - Follow existing code style
   - Add docstrings to new functions
   - Update documentation if needed
   - Test your changes

3. **Commit with clear messages**:
   ```bash
   git commit -m "feat: Add detection for 'remember' signal word"
   git commit -m "fix: Handle spaces in project paths"
   ```

4. **Push and create PR**:
   ```bash
   git push origin feature/better-signal-detection
   ```

5. **PR Description should include**:
   - What does this change?
   - Why is it needed?
   - How was it tested?
   - Any breaking changes?

## Coding Standards

### Python Style

- Follow PEP 8
- Use type hints
- Write docstrings for public functions

Example:
```python
def detect_signals(self, text: str) -> Dict[str, bool]:
    """Detect semantic signals in conversation text.

    Args:
        text: The conversation text to analyze

    Returns:
        Dictionary mapping signal types to presence (True/False)

    Example:
        >>> extractor = MemoryExtractor()
        >>> signals = extractor.detect_signals("please help me fix this again")
        >>> signals['request']  # True
        >>> signals['repetition']  # True
    """
```

### Commit Messages

Use conventional commits:
```
feat: Add new signal type for learning moments
fix: Correct hook path on Windows
docs: Update COMPATIBILITY.md with hook details
test: Add tests for signal detection
refactor: Extract signal patterns to constants
perf: Cache embedding calculations
```

## Architecture Overview

### The Flow

```
User: member "implement auth"
        ↓
[member.py] Syncs relevant memories → CLAUDE.md
        ↓
[member.py] Launches Claude Code
        ↓
User types prompt
        ↓
[Hook: UserPromptSubmit] member.py --sync-only --query "prompt"
        ↓
Claude responds
        ↓
[Hook: Stop] auto_concentrate.py --transcript path
        ↓
Memories extracted and stored
        ↓
Next prompt has better context
```

### Key Classes

**BerryManager** (berry_manager.py):
- Stores and retrieves memories
- Handles embeddings and semantic search
- Manages index and file storage

**MemoryExtractor** (auto_concentrate.py):
- Detects semantic signals
- Extracts solutions, errors, antipatterns
- Calculates importance scores

**ClaudeMDManager** (member.py):
- Manages CLAUDE.md integration
- Syncs context on prompts
- Handles hook setup

## Testing

Priority test areas:

```python
# tests/test_auto_concentrate.py
def test_signal_detection():
    """Test semantic signal detection."""
    extractor = MemoryExtractor()

    signals = extractor.detect_signals("please help me fix this again")
    assert signals['request'] == True
    assert signals['repetition'] == True

def test_importance_scoring():
    """Test importance calculation."""
    extractor = MemoryExtractor()

    # Repetition should score high
    score = extractor.calculate_importance("I keep getting this error again")
    assert score >= 3

# tests/test_berry_manager.py
def test_add_solution():
    """Test adding a solution."""
    bm = BerryManager()
    bm.add_solution("Problem", "Solution", ["tag1"])
    results = bm.search_solutions("Problem")
    assert len(results) >= 1
```

Run tests:
```bash
python -m pytest tests/ -v
```

## Design Principles

1. **Automatic by default** - Users shouldn't have to do anything manually
2. **Local-first** - All data stays on the user's machine
3. **Seamless integration** - Works with Claude Code, not against it
4. **Smart prioritization** - Important things (repetition!) get remembered first
5. **Extensible** - Easy to add new signal types, storage backends, etc.

## Good First Issues

Look for issues tagged `good-first-issue`:
- Adding new signal words to detection
- Documentation improvements
- Simple bug fixes
- Test coverage

## Community

- Be respectful and inclusive
- Help others in issues/discussions
- Share your use cases
- Provide constructive feedback

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

- Open a Discussion on GitHub
- Check existing documentation
- Comment on relevant issues

Thank you for contributing to Memberberries!
