"""
main.py — Omega/JARVIS Runtime (Text-Only REPL Mode)

This file is the public entry point for the assistant.
It ensures:
 - The correct project root is used
 - The correct Desktop_Assistant package is imported
 - The correct boot system is executed
 - The REPL runs only AFTER boot completes
"""

import sys
import os
import traceback
from pathlib import Path
import importlib

# ------------------------------------------------------------
# 1. Establish correct project root
# ------------------------------------------------------------
FILE = Path(__file__).resolve()
PROJECT_ROOT = FILE.parent  # A:\GitHub\Desktop-Assistant
sys.path.insert(0, str(PROJECT_ROOT))

# ------------------------------------------------------------
# 2. Import boot system from the REAL package root
# ------------------------------------------------------------
# This is the critical fix:
# We MUST import Desktop_Assistant.boot.run as a PACKAGE,
# not as a top-level module, or paths resolve incorrectly.
run = importlib.import_module("Desktop_Assistant.boot.run")
launch_jarvis = run.launch_jarvis


# ------------------------------------------------------------
# 3. REPL header
# ------------------------------------------------------------
def print_header(brain):
    os_name = brain.get_current_os_key()
    print("\n===============================================")
    print(f"        OMEGA / JARVIS — {os_name.upper()} MODE")
    print("        Text-Only Runtime (Debug Safe)")
    print("===============================================\n")
    print("Type a command. Type 'exit' or 'quit' to stop.\n")


# ------------------------------------------------------------
# 4. REPL runtime
# ------------------------------------------------------------
def repl_runtime():
    from Desktop_Assistant import imports as I

    try:
        Brain = I.Brain()
        brain = Brain()
        print(brain.debug_snapshot())
        hub = brain.hub
    except Exception as e:
        print("FATAL: Could not initialize Brain.")
        print(e)
        sys.exit(1)

    print_header(brain)

    while True:
        try:
            user_text = input("You: ").strip()

            if user_text.lower() in ("exit", "quit", "shutdown", "stop"):
                print("\nJARVIS: Goodbye.\n")
                break

            if not user_text:
                continue

            result = brain.process(user_text)

            if isinstance(result, dict):
                msg = result.get("message", "")
                print(f"JARVIS: {msg}")
            else:
                print(f"JARVIS: {result}")

        except KeyboardInterrupt:
            print("\n\nJARVIS: Interrupted. Type 'exit' to quit.")
            continue

        except Exception as e:
            print("\nJARVIS: I hit an unexpected error.")
            print(f"Error: {e}")
            print(traceback.format_exc())
            continue


# ------------------------------------------------------------
# 5. Entry point
# ------------------------------------------------------------
if __name__ == "__main__":
    # Once boot completes, we enter REPL mode
    repl_runtime()
