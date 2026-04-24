# runtime/repl_runtime.py

import sys
import traceback
from Desktop_Assistant import imports as I


def print_header(brain):
    os_name = brain.get_current_os_key()
    print("\n===============================================")
    print(f"        OMEGA / JARVIS — {os_name.upper()} MODE")
    print("        Text-Only Runtime (Debug Safe)")
    print("===============================================\n")
    print("Type a command. Type 'exit' or 'quit' to stop.\n")


def repl_runtime():
    try:
        Brain = I.Brain()
        brain = Brain()
        print(brain.debug_snapshot())
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
                print(f"JARVIS: {result.get('message', '')}")
            else:
                print(f"JARVIS: {result}")

        except KeyboardInterrupt:
            print("\n\nJARVIS: Interrupted. Type 'exit' to quit.")
        except Exception as e:
            print("\nJARVIS: Unexpected error.")
            print(f"Error: {e}")
            print(traceback.format_exc())
