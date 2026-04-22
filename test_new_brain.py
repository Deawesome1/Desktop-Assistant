# test_new_brain.py

from Desktop_Assistant.brain import Brain

print("\n=== INITIALIZING BRAIN ===")
brain = Brain()

print("\n=== OS KEY ===")
print("Detected OS:", brain.get_current_os_key())

print("\n=== COMMANDS LOADED ===")
for cmd in brain.commands.keys():
    print(" -", cmd)

print("\n=== DEBUG SNAPSHOT ===")
brain.debug_print()

print("\n=== SELF TEST REPORT ===")
report = brain.self_test()
for key, value in report.items():
    print(f"{key}: {value}")

print("\n=== COMMAND LOOKUP TEST ===")
tests = ["note", "note_mac", "brightness", "volume", "unknowncommand"]

for t in tests:
    module = brain.find_command(t)
    if module:
        print(f"Lookup '{t}': FOUND → {module.__name__}")
    else:
        print(f"Lookup '{t}': NOT FOUND")

print("\n=== DIRECT MODULE EXECUTION TEST ===")
# Only run if the module exists
if "note_mac" in brain.commands:
    mod = brain.commands["note_mac"]
    try:
        result = mod.run(brain, "note_mac test")
        print("note_mac.run() returned:", result)
    except Exception as e:
        print("note_mac.run() ERROR:", e)
else:
    print("note_mac not loaded — skipping direct execution test.")

print("\n=== TEST COMPLETE ===")
