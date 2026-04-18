#!/bin/bash
# LeetLoop Application Runner for macOS and Linux

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Please run setup.sh first:"
    echo "  ./setup.sh"
    exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "Virtual environment looks incomplete because .venv/bin/python was not found."
    echo "Rerun setup to recreate it:"
    echo "  ./setup.sh"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ".env configuration not found. Please run setup.sh first:"
    echo "  ./setup.sh"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Run the service in UI mode
python src/run_service.py --ui

exit $?
