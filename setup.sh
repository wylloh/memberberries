#!/bin/bash
# Memberberries Setup Script
#
# This script bootstraps memberberries by installing dependencies
# and launching the interactive setup wizard.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "=============================================="
echo "       MEMBERBERRIES SETUP"
echo "=============================================="
echo ""

# Step 1: Check Python
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not found."
    echo "Please install Python 3.8+ and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  Found Python $PYTHON_VERSION"
echo ""

# Step 2: Install dependencies
echo "Installing dependencies..."
pip3 install -r "$SCRIPT_DIR/requirements.txt" --quiet 2>/dev/null || \
pip3 install -r "$SCRIPT_DIR/requirements.txt" --break-system-packages --quiet 2>/dev/null || \
pip3 install numpy --quiet

echo "  Dependencies installed"
echo ""

# Step 3: Make scripts executable
chmod +x "$SCRIPT_DIR/member.py"
chmod +x "$SCRIPT_DIR/memberberries.py"
chmod +x "$SCRIPT_DIR/juice.py"

# Step 4: Launch the interactive setup wizard
echo "Launching interactive setup wizard..."
echo ""

python3 "$SCRIPT_DIR/member.py" setup
