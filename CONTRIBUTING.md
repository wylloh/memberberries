# Contributing to Claude Code Memory System

Thank you for your interest in contributing! This project aims to make Claude Code more effective by providing persistent memory across sessions.

## 🎯 Project Vision

Create a simple, effective memory system that:
- Works out of the box with zero configuration
- Respects user privacy (local-first)
- Scales from personal use to power users
- Remains easy to understand and modify

## 🚀 Getting Started

### Development Setup

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/claude-code-memory.git
cd claude-code-memory

# 3. Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the demo to test
python demo.py

# 6. Run tests (once we add them)
python -m pytest tests/
```

### Project Structure

```
claude-code-memory/
├── src/                    # Source code
│   ├── memory_manager.py   # Core memory management
│   ├── claude_memory.py    # CLI interface
│   └── integration.py      # Claude Code integration
├── tests/                  # Test suite
├── examples/               # Example scripts
│   └── demo.py
├── docs/                   # Documentation
│   ├── QUICKSTART.md
│   ├── ARCHITECTURE.md
│   └── VECTOR_DB_UPGRADE.md
└── README.md
```

## 🛠️ How to Contribute

### Reporting Bugs

Before creating a bug report:
- Check if the issue already exists
- Collect relevant information (OS, Python version, error messages)
- Try to reproduce with minimal example

Create an issue with:
- **Clear title**: "Search returns no results on Windows"
- **Description**: What happened vs. what you expected
- **Steps to reproduce**: Minimal code to trigger the bug
- **Environment**: OS, Python version, relevant package versions
- **Logs/Screenshots**: If applicable

### Suggesting Features

We love feature ideas! Before suggesting:
- Check if someone already suggested it
- Consider if it aligns with project vision (simplicity, privacy)
- Think about backward compatibility

Good feature requests include:
- **Use case**: Why do you need this?
- **Proposal**: How should it work?
- **Alternatives**: Other ways to solve this?
- **Impact**: Who else would benefit?

### Code Contributions

#### Types of Contributions Needed

**High Priority:**
1. Test coverage (we have none yet!)
2. Bug fixes
3. Documentation improvements
4. Performance optimizations

**Medium Priority:**
1. Better embedding models (as plugins)
2. Additional storage backends
3. Migration tools
4. CLI improvements

**Future/Big Features:**
1. Web UI for browsing memories
2. Auto-extraction from transcripts
3. Team sharing (encrypted)
4. Git integration
5. Claude Code plugin

#### Pull Request Process

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

2. **Make your changes**:
   - Write clear, commented code
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation if needed

3. **Commit with clear messages**:
   ```bash
   git commit -m "Add semantic search with sentence-transformers"
   git commit -m "Fix: Handle empty search results gracefully"
   ```

4. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub

5. **PR Description should include**:
   - What does this change?
   - Why is this change needed?
   - How has it been tested?
   - Any breaking changes?
   - Related issues (if any)

## 📝 Coding Standards

### Python Style

- Follow PEP 8
- Use type hints where possible
- Write docstrings for public functions
- Keep functions focused and small

Example:
```python
def search_solutions(self, query: str, top_k: int = 3) -> List[Dict]:
    """Search for relevant solutions using semantic similarity.
    
    Args:
        query: The problem or query to search for
        top_k: Number of top results to return
        
    Returns:
        List of solution dictionaries sorted by relevance
        
    Example:
        >>> mm = MemoryManager()
        >>> results = mm.search_solutions("database connection", top_k=5)
    """
    # Implementation
```

### Commit Messages

Use conventional commits format:

```
feat: Add ChromaDB storage backend
fix: Handle empty query in search
docs: Update QUICKSTART with new examples
test: Add tests for preference storage
refactor: Extract embedding logic to separate module
perf: Optimize search for large datasets
```

### Documentation

- Update README.md if you change public API
- Add docstrings to new functions
- Include examples in documentation
- Update CHANGELOG.md with your changes

## 🧪 Testing

We need test coverage! Priority areas:

```python
# tests/test_memory_manager.py
def test_add_preference():
    """Test adding a preference."""
    mm = MemoryManager()
    pref = mm.add_preference("style", "Use type hints", ["python"])
    assert pref['category'] == "style"
    assert "python" in pref['tags']

def test_search_solutions():
    """Test solution search."""
    mm = MemoryManager()
    mm.add_solution("Problem 1", "Solution 1", ["python"])
    results = mm.search_solutions("problem", top_k=1)
    assert len(results) == 1
    assert results[0]['problem'] == "Problem 1"

def test_empty_search():
    """Test search with no results."""
    mm = MemoryManager()
    results = mm.search_solutions("nonexistent query")
    assert results == []
```

Run tests:
```bash
python -m pytest tests/ -v
```

## 🎨 Design Principles

### 1. Simplicity First
- Default configuration should "just work"
- Advanced features should be optional
- Clear error messages

### 2. Local-First
- No required cloud services
- User controls their data
- Privacy by default

### 3. Backward Compatibility
- Don't break existing workflows
- Provide migration paths
- Deprecate gradually

### 4. Extensible
- Plugin architecture for embeddings
- Swappable storage backends
- Easy to customize

## 📋 Good First Issues

Look for issues tagged `good-first-issue`:
- Documentation improvements
- Adding examples
- Simple bug fixes
- Test coverage

## 🤝 Community

- Be respectful and inclusive
- Help others in issues/discussions
- Share your use cases
- Provide constructive feedback

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in documentation (for significant contributions)

## ❓ Questions?

- Open a Discussion on GitHub
- Comment on relevant issues
- Check existing documentation

Thank you for contributing! 🚀
