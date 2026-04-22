"""
demo_windows.py — Scenario-driven command tester for Omega (Windows)
Now with PASS/FAIL tracking and a summary report.
"""
import sys
from pathlib import Path

# Find the project root dynamically
FILE = Path(__file__).resolve()
PROJECT_ROOT = next(p for p in FILE.parents if (p / "Desktop_Assistant").exists())

sys.path.insert(0, str(PROJECT_ROOT))

from Desktop_Assistant.brain.engine.brain import Brain
import traceback


# ----------------------------------------------------------------------
# Per-command realistic test inputs
# ----------------------------------------------------------------------
TEST_INPUTS = {
    "brightness_windows": "brightness up",
    "calculator": "calculate 5 plus 7",
    "clipboard": "clipboard read",
    "clipboard_history": "clipboard history",
    "converter": "convert 5 miles to kilometers",
    "date": "what is today's date",
    "dictionary": "define entropy",
    "greet": "hello",
    "ip_address_windows": "ip address",
    "jokes": "tell me a joke",
    "media_control_windows": "volume up",
    "news": "news",
    "note_windows": "take a note: buy milk",
    "open_browser_windows": "open browser",
    "pause": "pause",
    "pc_commands_windows": "pc commands",
    "recycle_bin_windows": "empty recycle bin",
    "reminder": "remind me in 5 minutes",
    "screenshot_windows": "take a screenshot",
    "stopwatch": "start stopwatch",
    "system_info_windows": "system info",
    "test_imports": "test imports",
    "time": "what time is it",
    "timer": "set a timer for 10 seconds",
    "top_processes_windows": "top processes",
    "weather": "weather in Indianapolis",
    "wifi_info_windows": "wifi info",
    "wikipedia": "wikipedia Albert Einstein",
    "youtube": "open youtube",
}

# ----------------------------------------------------------------------
# Simple PASS/FAIL registry
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


def main():
    print("\n=== OMEGA WINDOWS COMMAND DEMO (Scenario Mode) ===\n")

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

            # Determine if the command logically succeeded
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
