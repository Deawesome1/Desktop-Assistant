"""
test/diagnose.py — Run this to see exactly why failing commands fail.
Bypasses command_hub and calls each module directly.

Usage:
    python test/diagnose.py
"""
import sys, os, traceback
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

COMMANDS_TO_CHECK = [
    ("volume",           "volume up"),
    ("screenshot",       "take a screenshot"),
    ("clipboard",        "read clipboard"),
    ("clipboard_history","clipboard history"),
    ("note",             "take a note test"),
    ("wifi_info",        "wifi"),
]

print("\n=== JARVIS Command Diagnostics ===\n")

# Check platform_utils import
print("1. platform_utils import:")
try:
    import platform_utils
    print(f"   OK — IS_WINDOWS={platform_utils.IS_WINDOWS}, IS_MAC={platform_utils.IS_MAC}")
except Exception as e:
    print(f"   FAIL — {e}")
    traceback.print_exc()

# Check personality import
print("\n2. personality.engine import:")
try:
    from bot.personality.engine import get_small_talk
    reply = get_small_talk("how are you")
    print(f"   OK — small talk reply: '{reply}'")
except Exception as e:
    print(f"   FAIL — {e}")
    traceback.print_exc()

# Check each failing command directly
print("\n3. Command module imports:\n")
for cmd_name, test_prompt in COMMANDS_TO_CHECK:
    print(f"   [{cmd_name}] '{test_prompt}'")
    try:
        import importlib
        mod = importlib.import_module(f"commands.{cmd_name}")
        result = mod.run(test_prompt)
        print(f"   -> {result}\n")
    except Exception as e:
        print(f"   -> EXCEPTION: {type(e).__name__}: {e}")
        # Print just the relevant traceback lines
        lines = traceback.format_exc().strip().split("\n")
        for line in lines[-4:]:
            print(f"      {line}")
        print()

# Check stopwatch state persistence
print("4. Stopwatch state persistence:")
try:
    import importlib
    sw = importlib.import_module("commands.stopwatch")
    r1 = sw.run("start stopwatch")
    print(f"   start -> {r1}")
    r2 = sw.run("stopwatch lap")
    print(f"   lap   -> {r2}")
    r3 = sw.run("stop stopwatch")
    print(f"   stop  -> {r3}")
except Exception as e:
    print(f"   FAIL — {e}")
    traceback.print_exc()

print("\n=== Done ===\n")