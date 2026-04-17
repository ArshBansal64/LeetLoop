#!/bin/bash
# LeetLoop Setup Script for macOS and Linux
# This script sets up LeetLoop from source

set -e

cd "$(dirname "$0")"

echo ""
echo "======================================"
echo "LeetLoop - Setup"
echo "======================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ using your package manager:"
    echo "  macOS:  brew install python3"
    echo "  Ubuntu: sudo apt-get install python3-pip python3-venv"
    echo "  Fedora: sudo dnf install python3-pip python3-venv"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Detected Python $PYTHON_VERSION"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "[OK] Virtual environment created"
else
    echo "[OK] Virtual environment already exists"
fi

echo ""
echo "Activating virtual environment..."
source .venv/bin/activate

echo "Upgrading pip..."
python3 -m pip install --upgrade pip -q

echo "Installing dependencies..."
pip install -r requirements.txt -q

echo "[OK] Dependencies installed"
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "======================================"
    echo "Configuration Required"
    echo "======================================"
    echo ""

    if [ -f ".env.example" ]; then
        cp .env.example .env
        chmod 600 .env
        echo "[OK] Created .env from .env.example"
    else
        echo "ERROR: .env.example was not found"
        exit 1
    fi

    echo ""
    echo "You need an OpenAI API key to use LeetLoop"
    echo "Get one at: https://platform.openai.com/api-keys"
    echo ""

    read -p "Enter your OpenAI API key: " OPENAI_KEY

    if [ -z "$OPENAI_KEY" ]; then
        echo "ERROR: API key is required"
        exit 1
    fi

    OPENAI_KEY="$OPENAI_KEY" python3 - <<'PY'
import os
from pathlib import Path
path = Path('.env')
content = path.read_text(encoding='utf-8')
content = content.replace(
    'OPENAI_API_KEY=your_openai_api_key_here',
    f"OPENAI_API_KEY={os.environ['OPENAI_KEY']}"
)
path.write_text(content, encoding='utf-8')
PY
    chmod 600 .env

    echo "[OK] Configuration saved to .env"
    echo ""
    echo "Remaining required fields are still in .env with placeholder values:"
    echo "  - LEETCODE_SESSION"
    echo "  - LEETCODE_CSRFTOKEN"
    echo "Fill those in before starting the app."
else
    echo "[OK] .env already configured"
fi

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "  1. Open .env and fill in any remaining placeholder values"
echo "  2. Run ./run_app.sh"
echo ""
echo "Or make run_app.sh executable, then run it to start LeetLoop:"
echo "  chmod +x run_app.sh"
echo "  ./run_app.sh"
echo ""
