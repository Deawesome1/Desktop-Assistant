"""
demo_mac.py — Scenario-driven command tester for Omega (macOS)
Mirrors the Windows version but tests macOS-supported commands.
"""

import sys
from pathlib import Path
import traceback

# Ensure project root is on sys.path BEFORE imports
FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in FILE.parents if (p / "Desktop_Assistant").exists())
sys.path.insert(0, str(PROJECT_ROOT))

from Desktop_Assistant.brain.engine.brain import Brain


# ----------------------------------------------------------------------
# Per-command realistic test inputs (macOS versions)
# ----------------------------------------------------------------------
TEST_INPUTS = {
    "brightness_mac": "brightness up",
    "calculator": "calculate 5 plus 7",
    "clipboard": "clipboard read",
    "clipboard_history": "clipboard history",
    "converter": "convert 5 miles to kilometers",
    "date": "what is today's date",
    "dictionary": "define entropy",
    "greet": "hello",
    "ip_address_mac": "ip address",
    "jokes": "tell me a joke",
    "media_control_mac": "volume up",
    "news": "news",
    "note_mac": "take a note: buy milk",
    "open_browser_mac": "open browser",
    "pause": "pause",
    "pc_commands_mac": "mac commands",
    "recycle_bin_mac": "empty trash",
    "reminder": "remind me in 5 minutes",
    "screenshot_mac": "take a screenshot",
    "stopwatch": "start stopwatch",
    "system_info_mac": "system info",
    "test_imports": "test imports",
    "time": "what time is it",
    "timer": "set a timer for 10 seconds",
    "top_processes_mac": "top processes",
    "weather": "weather in Indianapolis",
    "wifi_info_mac": "wifi info",
    "wikipedia": "wikipedia Albert Einstein",
    "youtube": "open youtube",
}


# ----------------------------------------------------------------------
# PASS/FAIL registry
# ----------------------------------------------------------------------
results = {
    "PASS": [],
    "FAIL": [],
    "SKIPPED": []
}


def record_result(name, success, message=""):
    if success:
        results["PASS"].append(name)
    else:
        results["FAIL"].append((name, message))


# ----------------------------------------------------------------------
# Main test runner
# ----------------------------------------------------------------------
def main():
    print("\n=== OMEGA MACOS COMMAND DEMO (Scenario Mode) ===\n")

    brain = Brain()
    commands = brain.commands

    print(f"Loaded {len(commands)} commands for OS: {brain.get_current_os_key()}\n")

    for name, func in sorted(commands.items()):
        # Skip dangerous commands
        if "exit" in name or "shutdown" in name:
            print(f"→ Skipping dangerous command: {name}")
            results["SKIPPED"].append(name)
            continue

        query = TEST_INPUTS.get(name, "test")

        print(f"→ Testing command: {name}")
        print(f"   Input: {query}")

        try:
            result = func(brain, query)
            print(f"   PASS — returned: {result}")

            if isinstance(result, dict) and result.get("success") is False:
                record_result(name, False, result.get("message"))
            else:
                record_result(name, True)

        except Exception as e:
            print(f"   FAIL — error: {e}")
            print(traceback.format_exc())
            record_result(name, False, str(e))

    # ------------------------------------------------------------------
    # Summary Report
    # ------------------------------------------------------------------
    print("\n=== TEST SUMMARY ===")
    total = len(results["PASS"]) + len(results["FAIL"]) + len(results["SKIPPED"])
    print(f"Total commands tested: {total}")
    print(f"PASS: {len(results['PASS'])}")
    print(f"FAIL: {len(results['FAIL'])}")
    print(f"SKIPPED: {len(results['SKIPPED'])}")

    if results["FAIL"]:
        print("\n--- FAILURES ---")
        for name, msg in results["FAIL"]:
            print(f"❌ {name}: {msg}")

    print("\n=== DEMO COMPLETE ===\n")


if __name__ == "__main__":
    main()
