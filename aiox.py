#!/usr/bin/env python3
"""AI-OS Command Line Interface wrapper"""

import sys
from pathlib import Path

# Add the project root to the Python path
root = Path(__file__).parent.resolve()
sys.path.insert(0, str(root))

from aiox.cli import main

if __name__ == "__main__":
    sys.exit(main())