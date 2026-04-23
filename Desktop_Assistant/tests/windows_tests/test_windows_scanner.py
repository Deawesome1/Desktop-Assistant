"""
Standalone test runner for the Windows app scanner.

Run manually:
    python Desktop_Assistant/tests/windows_tests/test_windows_scanner.py
"""

import sys
from pathlib import Path
import json

# ------------------------------------------------------------
# Ensure project root is on sys.path
# ------------------------------------------------------------
FILE = Path(__file__).resolve()
PROJECT_ROOT = FILE.parents[3]  # A:\GitHub\Desktop-Assistant
sys.path.insert(0, str(PROJECT_ROOT))

# Import the REAL API
from Desktop_Assistant.commands.app_scanner import build_cache, get_cache


def main():
    print("=== Testing Windows App Scanner ===")

    try:
        # Build the cache (forces a fresh scan)
        cache = build_cache(force=True)
    except Exception as e:
        print("❌ Scanner crashed:")
        print(e)
        return

    print(f"\n✓ Scan complete — {cache['app_count']} apps found.\n")

    for app in cache["apps"][:20]:
        print(f"- {app.get('name')}  ({app.get('path')})")

    with open("windows_scan_output.json", "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

    print("\n✓ Output written to windows_scan_output.json")


if __name__ == "__main__":
    main()
