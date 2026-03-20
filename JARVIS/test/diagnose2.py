"""
test/diagnose2.py — Targeted diagnostics for remaining failures.
"""
import sys, os, json, traceback
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

print("\n=== Diagnose 2: Stopwatch + Small Talk ===\n")

# 1. Check stopwatch in YOUR commands.json
print("1. Stopwatch in commands.json:")
cfg_path = os.path.join(ROOT, "config", "commands.json")
try:
    data = json.load(open(cfg_path))
    sw = data["commands"].get("stopwatch", "NOT FOUND")
    print(f"   enabled: {sw.get('enabled') if isinstance(sw, dict) else sw}")
except Exception as e:
    print(f"   ERROR: {e}")

# 2. Find personality engine
print("\n2. Looking for personality engine:")
for candidate in [
    os.path.join(ROOT, "bot", "personality", "engine.py"),
    os.path.join(ROOT, "personality", "engine.py"),
]:
    exists = os.path.exists(candidate)
    print(f"   {'FOUND' if exists else 'missing'}: {candidate}")

# 3. Try importing personality
print("\n3. Personality import attempts:")
for import_path in ["bot.personality.engine", "personality.engine"]:
    try:
        import importlib
        mod = importlib.import_module(import_path)
        reply = mod.get_small_talk("how are you")
        print(f"   OK via '{import_path}' — reply: '{reply}'")
        break
    except Exception as e:
        print(f"   FAIL via '{import_path}': {e}")

# 4. Try stopwatch directly
print("\n4. Stopwatch direct test:")
try:
    import importlib
    sw = importlib.import_module("commands.stopwatch")
    for q in ["start stopwatch", "stopwatch lap", "stop stopwatch"]:
        r = sw.run(q)
        print(f"   '{q}' -> {r}")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

print("\n=== Done ===\n")