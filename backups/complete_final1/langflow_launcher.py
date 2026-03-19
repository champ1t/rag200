#!/usr/bin/env python3
"""
Langflow Launcher with Python 3.13 Compatibility Fix
"""
import os
import sys

# Fix daemon threads issue
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

# Disable problematic multiprocessing
os.environ['LANGFLOW_WORKERS'] = '1'

# Run langflow
if __name__ == '__main__':
    from langflow.__main__ import main
    sys.exit(main())
