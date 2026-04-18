#!/bin/bash
# LeetLoop Setup Script for macOS and Linux
# This script sets up LeetLoop from source

set -e

print_recovery_help() {
    local failed_command="$1"
    echo ""
    echo "Setup did not finish."
    echo "The failing step was: $failed_command"
    echo ""
    echo "Helpful recovery steps:"
    echo "  1. Confirm Python 3.10+ is installed: python3 --version"
    echo "  2. If virtualenv creation failed, install venv support:"
    echo "     macOS:  brew install python"
    echo "     Ubuntu/Debian: sudo apt-get install python3-venv"
    echo "     Fedora: sudo dnf install python3"
    echo "  3. If dependency install failed, try:"
    echo "     .venv/bin/python -m pip install --upgrade pip"
    echo "     .venv/bin/python -m pip install -r requirements.txt"
    echo "  4. If pip still fails, check your network connection and Python build tools."
    echo ""
    echo "After fixing the issue, rerun:"
    echo "  ./setup.sh"
}

trap 'print_recovery_help "$BASH_COMMAND"' ERR

cd "$(dirname "$0")"

echo ""
echo "======================================"
echo "LeetLoop - Setup"
echo "======================================"
echo ""

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

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "[OK] Virtual environment created"
else
    echo "[OK] Virtual environment already exists"
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "ERROR: Virtual environment exists but .venv/bin/python is missing."
    echo "Delete .venv and rerun ./setup.sh"
    exit 1
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

if python3 src/env_file_utils.py needs-config .env
then
    echo "======================================"
    echo "Configuration Required"
    echo "======================================"
    echo ""

    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            chmod 600 .env
            echo "[OK] Created .env from .env.example"
        else
            echo "ERROR: .env.example was not found"
            exit 1
        fi
    else
        echo "[OK] Existing .env is missing required values and will be updated"
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

    LEETLOOP_SETUP_OPENAI_API_KEY="$OPENAI_KEY" \
    LEETLOOP_SETUP_LEETCODE_SESSION="$LEETCODE_SESSION_VALUE" \
    LEETLOOP_SETUP_LEETCODE_CSRFTOKEN="$LEETCODE_CSRF_VALUE" \
    python3 src/env_file_utils.py update .env
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
