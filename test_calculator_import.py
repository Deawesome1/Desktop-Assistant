"""
test_calculator_import.py
Standalone test to verify that:

 - imports.py loads correctly
 - calculator.py imports correctly
 - run() executes without dependency errors

This test does NOT require the full assistant runtime.
"""

import traceback

# Try to import the calculator command
try:
    from Desktop_Assistant.commands.non_os_specific import calculator
    print("[OK] calculator.py imported successfully.")
except Exception as e:
    print("[FAIL] calculator.py failed to import:")
    traceback.print_exc()
    raise SystemExit(1)

# Try to import the import surface
try:
    from Desktop_Assistant import imports as I
    print("[OK] imports.py loaded successfully.")
except Exception as e:
    print("[FAIL] imports.py failed to import:")
    traceback.print_exc()
    raise SystemExit(1)

# Create a fake brain object with only the methods calculator.py needs
class FakeBrain:
    def event(self, name):
        print(f"[FakeBrain] event: {name}")

    def remember(self, key, value):
        print(f"[FakeBrain] remember: {key} = {value}")

    def get_current_os_key(self):
        # Return something calculator supports
        return "windows"

brain = FakeBrain()

# Try running the command
try:
    result = calculator.run(brain, "calculate 5 plus 7")
    print("[OK] run() executed successfully.")
    print("Result:", result)
except Exception as e:
    print("[FAIL] run() raised an exception:")
    traceback.print_exc()
    raise SystemExit(1)

print("\nAll tests passed.")
