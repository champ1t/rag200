#!/bin/bash
# Robust Langflow Starter for macOS/Python 3.11
# Uses absolute path to ensure VENV is used

# Fix for grpc/multiprocessing crash on macOS
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
export NO_PROXY=*

# Get absolute path to this script's directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_BIN="$DIR/venv/bin"

# Check if venv exists
if [ ! -d "$VENV_BIN" ]; then
    echo "❌ Error: Virtual environment not found at $VENV_BIN"
    exit 1
fi

echo "Using Python: $($VENV_BIN/python3 --version)"

echo "🧹 Cleaning up port 7860..."
lsof -t -i:7860 | xargs kill -9 2>/dev/null

echo "🚀 Starting Langflow..."
echo "👉 Open http://localhost:7860 in your browser when ready."

# Use the 'langflow' binary inside venv/bin
"$VENV_BIN/langflow" run --host 0.0.0.0 --port 7860
