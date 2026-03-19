#!/bin/bash
# Langflow Launcher with Python 3.13 Fix

export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
export LANGFLOW_WORKERS=1
export LANGFLOW_AUTO_LOGIN=false

# Use single worker to avoid daemon thread issues
python3 langflow_launcher.py run --host 0.0.0.0 --port 7860 --workers 1
