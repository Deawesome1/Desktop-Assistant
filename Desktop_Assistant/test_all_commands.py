"""
test_all_commands.py — REAL COMMAND TEST HARNESS
Runs every JARVIS command using the REAL Brain + CommandHub.
This version does NOT use FakeBrain or faux inputs.

Place this file in the project root (Desktop_Assistant/).
Run with:  python test_all_commands.py
"""

import traceback
from pathlib import Path
import importlib

from Desktop_Assistant.brain import dependency_manager
from brain import Brain
from commands import CommandHub


# ---------------------------------------------------------------------------
# Default test phrases for each command
# (You can expand this later)
# ---------------------------------------------------------------------------

DEFAULT_TEST_PHRASES = {
    "calculator": "calculate 5 plus 7",
    "converter": "convert 5 miles to kilometers",
    "date": "what is today's date",
    "dictionary": "define entropy",
    "exit": "exit",
    "jokes": "tell me a joke",
    "news": "latest news",
    "pause": "pause for 1 second",
    "stopwatch": "start stopwatch",
    "time": "what time is it",
    "timer": "set a timer for 3 seconds",
    "weather": "what's the weather",
    "wikipedia": "wikipedia python programming",
    "youtube": "play lo-fi music on youtube",
    "brightness": "set brightness to 50 percent",
    "ip_address": "what is my ip address",
    "media_volume": "volume up",
    "open_browser": "open google",
    "pc_commands": "lock my pc",
    "recycle_bin": "empty recycle bin",
    "system_info": "system information",
    "top_processes": "show top processes",
    "wifi_info": "wifi info",
}


# ---------------------------------------------------------------------------
# Load all commands from the real Brain
# ---------------------------------------------------------------------------
def load_real_commands():
    import Desktop_Assistant.brain.dependency_manager as dependency_manager
    dependency_manager.DISABLE_DEPENDENCY_CHECKS = True

    brain = Brain()
    hub = CommandHub(brain, debug=False, dry_run=False)
    return brain, hub

# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

def run_all_commands():
    print("\n=== Running REAL JARVIS Command Tests ===\n")

    brain, hub = load_real_commands()

    results = []

    for cmd_name, module in brain.commands.items():
        test_phrase = DEFAULT_TEST_PHRASES.get(cmd_name, cmd_name)

        print(f"\n--- Testing: {cmd_name} ---")
        print(f"Phrase: \"{test_phrase}\"")

        try:
            response = hub.execute(test_phrase)

            if response.get("success", False):
                print(f"[PASS] {cmd_name}")
                results.append((cmd_name, "PASS", None))
            else:
                err = response.get("meta", {}).get("error_type", "unknown")
                print(f"[FAIL] {cmd_name} — {err}")
                results.append((cmd_name, "FAIL", err))

        except Exception as e:
            print(f"[ERROR] {cmd_name} — Exception occurred")
            traceback.print_exc()
            results.append((cmd_name, "ERROR", str(e)))

    # ----------------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------------

    print("\n=== Summary ===")
    passed = sum(1 for _, status, _ in results if status == "PASS")
    failed = sum(1 for _, status, _ in results if status == "FAIL")
    errors = sum(1 for _, status, _ in results if status == "ERROR")

    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Errors: {errors}")
    print(f"Total: {len(results)}")

    print("\nDone.\n")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_all_commands()
