#!/bin/bash

# Claude Code Memory System - Setup Script
# This script sets up the memory system and optionally installs shell aliases

set -e

INSTALL_DIR="${HOME}/.claude-code-memory"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "================================================"
echo "  Claude Code Memory System - Setup"
echo "================================================"
echo ""

# Step 1: Install dependencies
echo "📦 Installing dependencies..."
pip install numpy --break-system-packages 2>/dev/null || pip install numpy
echo "✓ Dependencies installed"
echo ""

# Step 2: Set up directory structure
echo "📁 Setting up directory structure..."
mkdir -p "$INSTALL_DIR"/{preferences,projects,solutions,sessions}
echo "✓ Directories created at $INSTALL_DIR"
echo ""

# Step 3: Copy files if not already in install location
if [ "$REPO_DIR" != "$INSTALL_DIR" ]; then
    echo "📋 Copying files to installation directory..."
    cp "$REPO_DIR"/*.py "$INSTALL_DIR/"
    cp "$REPO_DIR"/*.md "$INSTALL_DIR/"
    cp "$REPO_DIR"/requirements.txt "$INSTALL_DIR/" 2>/dev/null || true
    chmod +x "$INSTALL_DIR"/*.py
    echo "✓ Files copied and made executable"
    echo ""
fi

# Step 4: Run demo
echo "🎮 Running demo to initialize and test system..."
cd "$INSTALL_DIR"
python3 demo.py
echo ""

# Step 5: Offer to install shell helpers
echo "================================================"
echo "  Optional: Shell Integration"
echo "================================================"
echo ""
echo "Would you like to add shell helpers to your shell config?"
echo "This will add convenient aliases for using the memory system."
echo ""
read -p "Install shell helpers? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Detect shell
    SHELL_CONFIG=""
    if [ -n "$BASH_VERSION" ]; then
        SHELL_CONFIG="$HOME/.bashrc"
    elif [ -n "$ZSH_VERSION" ]; then
        SHELL_CONFIG="$HOME/.zshrc"
    else
        echo "⚠️  Could not detect shell type. Please manually add aliases."
        echo "Add the following to your shell config:"
        echo ""
        cat << 'EOF'
# Claude Code Memory System
export CLAUDE_MEMORY_DIR="$HOME/.claude-code-memory"

alias cmem='python3 $CLAUDE_MEMORY_DIR/claude_memory.py'
alias cmem-stats='python3 $CLAUDE_MEMORY_DIR/claude_memory.py stats'
alias cmem-search='python3 $CLAUDE_MEMORY_DIR/claude_memory.py search'

claude_context() {
    python3 "$CLAUDE_MEMORY_DIR/integration.py" "$1" "${2:-$(pwd)}"
}
EOF
        exit 0
    fi
    
    # Add to shell config
    echo "" >> "$SHELL_CONFIG"
    echo "# Claude Code Memory System - Added by setup script" >> "$SHELL_CONFIG"
    echo "export CLAUDE_MEMORY_DIR=\"$INSTALL_DIR\"" >> "$SHELL_CONFIG"
    echo "" >> "$SHELL_CONFIG"
    echo "# Convenient aliases" >> "$SHELL_CONFIG"
    echo "alias cmem='python3 \$CLAUDE_MEMORY_DIR/claude_memory.py'" >> "$SHELL_CONFIG"
    echo "alias cmem-stats='python3 \$CLAUDE_MEMORY_DIR/claude_memory.py stats'" >> "$SHELL_CONFIG"
    echo "alias cmem-search='python3 \$CLAUDE_MEMORY_DIR/claude_memory.py search'" >> "$SHELL_CONFIG"
    echo "" >> "$SHELL_CONFIG"
    echo "# Function to get context for Claude Code" >> "$SHELL_CONFIG"
    echo "claude_context() {" >> "$SHELL_CONFIG"
    echo "    python3 \"\$CLAUDE_MEMORY_DIR/integration.py\" \"\$1\" \"\${2:-\$(pwd)}\"" >> "$SHELL_CONFIG"
    echo "}" >> "$SHELL_CONFIG"
    echo "" >> "$SHELL_CONFIG"
    
    echo "✓ Shell helpers added to $SHELL_CONFIG"
    echo ""
    echo "⚠️  Run 'source $SHELL_CONFIG' or restart your terminal to use the new aliases"
fi

echo ""
echo "================================================"
echo "  Setup Complete! 🎉"
echo "================================================"
echo ""
echo "Quick commands to try:"
echo "  cmem stats                    - Show memory statistics"
echo "  cmem search 'your query'      - Search solutions"
echo "  claude_context 'task'         - Get context for Claude Code"
echo ""
echo "📚 Documentation:"
echo "  README.md      - Full documentation"
echo "  QUICKSTART.md  - Quick start guide"
echo ""
echo "Happy coding with enhanced memory! 🚀"
