#!/bin/bash
# 🫐 Memberberries - Install the 'member' command
#
# This script installs the 'member' command for seamless Claude Code integration.
#
# Usage:
#   bash install_member.sh
#
# After installation, you can use:
#   member "your task"     # Sync + launch claude
#   member                 # Sync + launch claude
#   member --sync-only     # Just sync CLAUDE.md

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MEMBER_PY="$SCRIPT_DIR/member.py"

echo "🫐 Memberberries - Installing 'member' command"
echo ""

# Make member.py executable
chmod +x "$MEMBER_PY"
echo "✓ Made member.py executable"

# Determine installation method
INSTALL_METHOD=""

# Check if /usr/local/bin exists and is writable
if [ -d "/usr/local/bin" ] && [ -w "/usr/local/bin" ]; then
    INSTALL_METHOD="symlink"
    INSTALL_PATH="/usr/local/bin/member"
elif [ -d "$HOME/.local/bin" ]; then
    INSTALL_METHOD="symlink"
    INSTALL_PATH="$HOME/.local/bin/member"
else
    INSTALL_METHOD="alias"
fi

if [ "$INSTALL_METHOD" = "symlink" ]; then
    # Create symlink
    if [ -L "$INSTALL_PATH" ] || [ -f "$INSTALL_PATH" ]; then
        rm "$INSTALL_PATH"
    fi
    ln -s "$MEMBER_PY" "$INSTALL_PATH"
    echo "✓ Created symlink: $INSTALL_PATH -> $MEMBER_PY"
    echo ""
    echo "🎉 Installation complete!"
    echo ""
    echo "You can now use:"
    echo "  member \"implement feature X\"    # Sync context + launch claude"
    echo "  member                           # Sync + launch claude"
    echo "  member --sync-only               # Just sync CLAUDE.md"
    echo "  member --status                  # Show memberberries status"
else
    # Provide alias instructions
    echo ""
    echo "Add this line to your shell config (~/.bashrc, ~/.zshrc, etc.):"
    echo ""
    echo "  alias member='python3 $MEMBER_PY'"
    echo ""
    echo "Then run: source ~/.zshrc  (or ~/.bashrc)"
    echo ""
    echo "After that, you can use:"
    echo "  member \"implement feature X\"    # Sync context + launch claude"
fi

echo ""
echo "📖 How it works:"
echo "   1. 'member' syncs relevant memories into your project's CLAUDE.md"
echo "   2. It then launches 'claude' (Claude Code)"
echo "   3. Claude Code automatically reads CLAUDE.md at session start"
echo "   4. Your existing CLAUDE.md content is preserved"
echo ""
