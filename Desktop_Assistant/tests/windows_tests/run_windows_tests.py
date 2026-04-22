"""
run_windows_tests.py — Windows command test runner for JARVIS (Omega)
Author: Nunya

Runs all Windows-specific commands using the Omega architecture.
Forces OS override = "windows" so tests run correctly on any machine.
"""
import sys
from pathlib import Path

# Project root = 3 levels up
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from Desktop_Assistant.brain.engine.brain import Brain
from Desktop_Assistant.brain.loader import CommandLoader

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------
class C:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


# ---------------------------------------------------------------------------
# FakeBrain override for OS = windows
# ---------------------------------------------------------------------------
class FakeBrain(Brain):
    def get_current_os_key(self):
        return "windows"


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------
def run_windows_tests():
    print(f"{C.CYAN}\n=== WINDOWS TEST RUNNER (Omega) ==={C.RESET}")

    b = FakeBrain()
    loader = CommandLoader("windows")

    commands, aliases = loader.load_all()

    print(f"{C.CYAN}Loaded {len(commands)} Windows commands.{C.RESET}")
    print(f"Aliases: {list(aliases.keys())}\n")

    passed = 0
    failed = 0
    slow = []

    for name, cmd in commands.items():
        print(f"{C.YELLOW}Testing: {name}{C.RESET}")

        start = time.time()

        try:
            result = cmd.run(b, name)

            if isinstance(result, dict) and result.get("success") is True:
                print(f"{C.GREEN}PASS{C.RESET}\n")
                passed += 1
            else:
                print(f"{C.RED}FAIL — returned non-success result{C.RESET}")
                print(result)
                print()
                failed += 1

        except Exception as e:
            print(f"{C.RED}ERROR — exception thrown{C.RESET}")
            traceback.print_exc()
            print()
            failed += 1

        duration = time.time() - start
        if duration > 1.0:
            slow.append((name, duration))

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print(f"{C.CYAN}=== TEST SUMMARY ==={C.RESET}")
    print(f"{C.GREEN}Passed: {passed}{C.RESET}")
    print(f"{C.RED}Failed: {failed}{C.RESET}")

    if slow:
        print(f"\n{C.YELLOW}Slow commands (>1s):{C.RESET}")
        for name, t in slow:
            print(f" - {name}: {t:.2f}s")

    print(f"{C.CYAN}\n=== END WINDOWS TESTS ==={C.RESET}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run_windows_tests()
