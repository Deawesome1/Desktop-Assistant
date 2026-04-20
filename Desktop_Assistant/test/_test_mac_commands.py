"""
test/_test_mac_commands.py
Runs ALL macOS commands after OS detection.

This test runner:
- Confirms the OS is macOS
- Loads macOS commands (shared + version-specific)
- Executes each command safely
- Prints pass/fail results
"""

import os
import platform
import traceback
import importlib

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
COMMANDS_ROOT = os.path.join(PROJECT_ROOT, "commands", "mac_commands")

def is_macos() -> bool:
    return platform.system().lower() == "darwin"


def discover_mac_commands():
    """
    Walks mac_commands/ and returns a list of import paths for all command modules.
    Example: commands.mac_commands.shared.volume
    """
    modules = []

    for root, dirs, files in os.walk(COMMANDS_ROOT):
        for file in files:
            if not file.endswith(".py") or file.startswith("__"):
                continue

            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, PROJECT_ROOT)

            # Convert path → module import string
            module = rel_path.replace("/", ".").replace("\\", ".")
            module = module[:-3]  # remove .py

            modules.append(module)

    return sorted(modules)


def run_command_module(module_name: str):
    """
    Imports a command module and runs its run() function.
    """
    try:
        mod = importlib.import_module(module_name)

        if not hasattr(mod, "run"):
            return False, "No run() function"

        result = mod.run()
        return True, result

    except Exception as e:
        return False, f"{type(e).__name__}: {e}\n{traceback.format_exc()}"


def main():
    print("=== macOS Command Test Runner ===")

    if not is_macos():
        print("[SKIP] Not running on macOS. Exiting.")
        return

    modules = discover_mac_commands()

    if not modules:
        print("[ERROR] No macOS command modules found.")
        return

    print(f"Discovered {len(modules)} macOS command modules.\n")

    passed = 0
    failed = 0

    for module in modules:
        print(f"Running: {module} ... ", end="")
        ok, result = run_command_module(module)

        if ok:
            print("PASS")
            passed += 1
        else:
            print("FAIL")
            print(result)
            failed += 1

    print("\n=== Summary ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")


if __name__ == "__main__":
    main()
