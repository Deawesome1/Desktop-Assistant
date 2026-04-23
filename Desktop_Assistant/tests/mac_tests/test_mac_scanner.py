"""
Standalone test runner for the macOS app scanner.

Run manually:
    python Desktop_Assistant/tests/mac_tests/test_mac_scanner.py
"""

import sys
from pathlib import Path
import json

# ------------------------------------------------------------
# Ensure project root is on sys.path
# ------------------------------------------------------------
FILE = Path(__file__).resolve()

# test file is:
# Desktop_Assistant/tests/mac_tests/test_mac_scanner.py
# project root is THREE levels up
PROJECT_ROOT = FILE.parents[3]  # A:\GitHub\Desktop-Assistant (or mac equivalent)

sys.path.insert(0, str(PROJECT_ROOT))

# Import the unified API (macOS version will be selected automatically)
from Desktop_Assistant.commands.app_scanner import build_cache, get_cache


def main():
    print("=== Testing macOS App Scanner ===")

    try:
        # Force a fresh scan
        cache = build_cache(force=True)
    except Exception as e:
        print("❌ Scanner crashed:")
        print(e)
        return

    print(f"\n✓ Scan complete — {cache['app_count']} apps found.\n")

    # Show first 20 apps
    for app in cache["apps"][:20]:
        print(f"- {app.get('name')}  ({app.get('path')})")

    # Save output for inspection
    with open("mac_scan_output.json", "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

    print("\n✓ Output written to mac_scan_output.json")


if __name__ == "__main__":
    main()
