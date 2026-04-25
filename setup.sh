#!/usr/bin/env bash
set -euo pipefail

# NORNBRAIN - first-time environment setup
# Supports Linux, macOS, and Git Bash on Windows.
# This script does NOT build the openc2e engine - see https://github.com/thechimpmatrix/openc2e-nb.

echo "=== NORNBRAIN Setup ==="
echo ""

# --- Python version check ---
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is not on PATH."
    echo "Install Python 3.11 or later from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
    echo "Error: Python 3.11 or later is required. Found: Python ${PYTHON_VERSION}"
    exit 1
fi

echo "Python ${PYTHON_VERSION} found."

# --- Virtual environment ---
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment at .venv/ ..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists at .venv/"
fi

# Activate
if [ -f ".venv/Scripts/activate" ]; then
    # Git Bash on Windows
    source .venv/Scripts/activate
else
    source .venv/bin/activate
fi

echo "Installing dependencies from requirements.txt ..."
pip install --upgrade pip --quiet
pip install -r requirements.txt

# --- Environment file ---
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "Created .env from .env.example."
    echo "Edit .env and set C3_DATA_PATH to your Creatures 3 game data directory."
fi

# --- Verify import ---
echo ""
echo "Verifying core imports ..."
python3 -c "import torch; import ncps; print(f'  torch {torch.__version__}, ncps OK')"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env and set C3_DATA_PATH to your Creatures 3 data folder."
echo "  2. Build the openc2e engine (separate repo: openc2e-nb) - see https://github.com/thechimpmatrix/openc2e-nb."
echo "  3. Read README.md for the full quickstart."
echo ""
echo "To activate the environment in future sessions:"
if [ -f ".venv/Scripts/activate" ]; then
    echo "  source .venv/Scripts/activate"
else
    echo "  source .venv/bin/activate"
fi
