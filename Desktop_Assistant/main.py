"""
main.py — Omega/JARVIS Entry Point
"""

import sys
from pathlib import Path
import importlib

# Ensure project root is on path
FILE = Path(__file__).resolve()
PROJECT_ROOT = FILE.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Runtime hub
runtime_hub = importlib.import_module("Desktop_Assistant.runtime.runtime_hub")


if __name__ == "__main__":
    # Boot manager ALREADY ran before calling main.py
    mode = runtime_hub.choose_runtime_mode()
    runtime_hub.run_runtime(mode)
