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
    echo "Please install Python 3.10+ using your package manager:"
    echo "  macOS:  brew install python3"
    echo "  Ubuntu: sudo apt-get install python3-pip python3-venv"
    echo "  Fedora: sudo dnf install python3-pip python3-venv"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Detected Python $PYTHON_VERSION"
echo ""

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "ERROR: LeetLoop requires Python 3.10 or newer."
    exit 1
fi

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
    echo "You need three values to use LeetLoop:"
    echo "  1. OPENAI_API_KEY"
    echo "  2. LEETCODE_SESSION"
    echo "  3. LEETCODE_CSRFTOKEN"
    echo ""
    echo "OpenAI API key:"
    echo "  https://platform.openai.com/api-keys"
    echo ""
    echo "LeetCode cookie values:"
    echo "  1. Sign in to https://leetcode.com in your browser"
    echo "  2. Open Developer Tools"
    echo "  3. Go to Application/Storage -> Cookies -> https://leetcode.com"
    echo "  4. Copy the values for LEETCODE_SESSION and csrftoken"
    echo ""

    read -p "Enter your OpenAI API key: " OPENAI_KEY
    read -p "Enter your LEETCODE_SESSION value: " LEETCODE_SESSION_VALUE
    read -p "Enter your LEETCODE_CSRFTOKEN value: " LEETCODE_CSRF_VALUE

    if [ -z "$OPENAI_KEY" ]; then
        echo "ERROR: OPENAI_API_KEY is required"
        exit 1
    fi
    if [ -z "$LEETCODE_SESSION_VALUE" ]; then
        echo "ERROR: LEETCODE_SESSION is required"
        exit 1
    fi
    if [ -z "$LEETCODE_CSRF_VALUE" ]; then
        echo "ERROR: LEETCODE_CSRFTOKEN is required"
        exit 1
    fi

    OPENAI_KEY="$OPENAI_KEY" LEETCODE_SESSION_VALUE="$LEETCODE_SESSION_VALUE" LEETCODE_CSRF_VALUE="$LEETCODE_CSRF_VALUE" python3 - <<'PY'
import os
from pathlib import Path
path = Path('.env')
content = path.read_text(encoding='utf-8')
content = content.replace(
    'OPENAI_API_KEY=your_openai_api_key_here',
    f"OPENAI_API_KEY={os.environ['OPENAI_KEY']}"
)
content = content.replace(
    'LEETCODE_SESSION=your_leetcode_session_here',
    f"LEETCODE_SESSION={os.environ['LEETCODE_SESSION_VALUE']}"
)
content = content.replace(
    'LEETCODE_CSRFTOKEN=your_leetcode_csrf_here',
    f"LEETCODE_CSRFTOKEN={os.environ['LEETCODE_CSRF_VALUE']}"
)
path.write_text(content, encoding='utf-8')
PY
    chmod 600 .env

    echo "[OK] Configuration saved to .env"
else
    echo "[OK] .env already configured"
fi

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "  1. Review .env if you want to confirm the saved values"
echo "  2. Run ./run_app.sh"
echo ""
echo "Or make run_app.sh executable, then run it to start LeetLoop:"
echo "  chmod +x run_app.sh"
echo "  ./run_app.sh"
echo ""
