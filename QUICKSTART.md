# Quick Start: Claude Code Integration

## 🚀 60-Second Setup

```bash
# 1. Navigate to the memory system
cd /path/to/claude-code-memory

# 2. Test it works
python3 claude_memory.py stats

# 3. Add your first preference
python3 claude_memory.py add-pref coding_style "Your preference here" -t python
```

## 💡 Three Ways to Use With Claude Code

### Method 1: Copy-Paste (Easiest)

**Before starting Claude Code:**

```bash
# Get context for your task
python3 integration.py "your task description" /path/to/project

# Copy the output and paste it as your first message to Claude Code
```

**Example:**
```bash
$ python3 integration.py "add API rate limiting" ~/my-project

# [Context appears - copy everything]
# Paste into Claude Code chat window
```

### Method 2: Shell Alias (Recommended)

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Add this function
claude_context() {
    python3 /path/to/claude-code-memory/integration.py "$1" "${2:-$(pwd)}"
}

# Usage:
# claude_context "implement user auth"
# claude_context "add rate limiting" ~/projects/my-app
```

Now before starting Claude Code, run:
```bash
claude_context "your task"
```

### Method 3: Auto-Inject (Advanced)

Create a wrapper script `~/bin/claude-code-with-memory`:

```bash
#!/bin/bash
TASK="$1"
PROJECT="${2:-$(pwd)}"

# Get context
CONTEXT=$(python3 /path/to/claude-code-memory/integration.py "$TASK" "$PROJECT")

# Start Claude Code with context pre-loaded
echo "$CONTEXT" | claude-code

# Or save to temp file and reference
echo "$CONTEXT" > /tmp/claude-context.txt
echo "Context saved to /tmp/claude-context.txt"
echo "Paste this content at the start of your Claude Code session"
cat /tmp/claude-context.txt
```

## 📝 Daily Workflow

### Morning (Starting Work)

```bash
# Check what you worked on yesterday
python3 claude_memory.py context "continue yesterday's work" -p ~/project

# Start Claude Code with this context
```

### During Coding

When you discover something useful:

```bash
# Save the insight immediately
python3 claude_memory.py add-solution \
  "Problem description" \
  "How you solved it" \
  -t relevant,tags \
  -c "code snippet if relevant"
```

### End of Day

```bash
# Save session summary
python3 claude_memory.py save-session \
  "Today's accomplishments" \
  -l "key learning 1|key learning 2|key learning 3" \
  -p ~/project
```

## 🎯 Best Practices

### 1. Start Every Session With Context

**Bad:**
```
You: "Help me add authentication"
Claude Code: [starts from scratch]
```

**Good:**
```bash
# First, get context:
python3 integration.py "add authentication" ~/project
```
```
You: [Paste context]
I need to add authentication to my FastAPI project.

Context from previous work:
[Memory system's output]

Please suggest an implementation approach.
```

### 2. Save Insights As They Happen

Don't wait until the end. The moment you solve something:

```bash
python3 claude_memory.py add-solution \
  "How to handle CORS in production" \
  "Use specific origins, not wildcard. Set credentials=True for cookies" \
  -t fastapi,cors,security
```

### 3. Keep Project Context Updated

When architecture changes:

```bash
python3 claude_memory.py add-project ~/my-project \
  -n "My Project" \
  -d "Updated description" \
  -a "New architectural decision"
```

### 4. Use Consistent Tags

Create a personal tagging convention:
- Language: `python`, `javascript`, `rust`
- Framework: `fastapi`, `react`, `django`
- Domain: `auth`, `database`, `api`, `testing`
- Type: `security`, `performance`, `bug-fix`

### 5. Regular Searches

Before asking Claude Code:

```bash
# Search your memory first
python3 claude_memory.py search "your problem"

# If you find a solution, great!
# If not, ask Claude Code and then save the solution
```

## 📋 Example Session

```bash
# 1. Morning: Start new feature
$ python3 integration.py "implement password reset flow" ~/my-app

🧠 Loading relevant memory...
✓ Context loaded

# [Copy output, paste into Claude Code]

# 2. During: Save breakthrough
$ python3 claude_memory.py add-solution \
  "How to securely generate password reset tokens" \
  "Use secrets.token_urlsafe(32) with expiry in Redis" \
  -t python,security,auth \
  -c "token = secrets.token_urlsafe(32)"

💡 Insight saved: a3f8c2e1b4d7

# 3. During: Update project
$ python3 claude_memory.py add-project ~/my-app \
  -n "My App" \
  -d "Added password reset functionality"

📋 Project context updated

# 4. End of day: Save session
$ python3 claude_memory.py save-session \
  "Implemented password reset with email tokens" \
  -l "Use Redis for token storage with TTL|SendGrid has rate limits - add retry logic|Always invalidate token after use" \
  -p ~/my-app

📝 Session saved
```

## 🔧 Troubleshooting

**"No context found"**
- You need to add preferences and solutions first
- Run the demo: `python3 demo.py`

**"Search returns irrelevant results"**
- Use more specific tags
- Consider upgrading to better embeddings (see README)

**"Context is too long for Claude Code"**
- Edit `integration.py` and reduce `top_k` values
- Be more specific in your task description

**"Want to start fresh"**
```bash
# Backup first
python3 claude_memory.py export ~/backup.json

# Then remove memory
rm -rf ~/.claude-code-memory
```

## 🎓 Learning Resources

- Full README: `README.md`
- Demo script: `python3 demo.py`
- View stored data: `ls ~/.claude-code-memory/`
- All commands: `python3 claude_memory.py --help`

## 💪 Pro Tips

1. **Alias Everything**: Add shell aliases for common operations
2. **Tag Consistently**: Develop your own tagging taxonomy
3. **Search First**: Before asking Claude, search your memory
4. **Save Immediately**: Don't wait to save insights
5. **Review Weekly**: Run stats and review what you've learned
6. **Backup Monthly**: Export your memory regularly

---

**Next Steps:**
1. Run `python3 demo.py` to see it in action
2. Add your first real preference
3. Use it with Claude Code on your next task
4. Save what you learn
5. Watch your productivity improve! 🚀
