# diagnose_all_commands.py
"""
Full command import diagnostic for JARVIS (Omega)
Scans every command file and reports:
 - Import success/failure
 - Full traceback on failure
 - Metadata on success
"""

import importlib
import traceback
from pathlib import Path

print("\n=== FULL COMMAND DIAGNOSTIC ===")

ROOT = Path(__file__).resolve().parent
CMD_ROOT = ROOT / "Desktop_Assistant" / "commands"

print("Project root:", ROOT)
print("Commands root:", CMD_ROOT)
print("Exists:", CMD_ROOT.exists())

# ---------------------------------------------------------------------
# Helper: test import
# ---------------------------------------------------------------------
def test_import(module_name):
    print(f"\n--- Testing {module_name} ---")
    try:
        mod = importlib.import_module(module_name)
        print("IMPORT OK")

        if hasattr(mod, "get_metadata"):
            try:
                meta = mod.get_metadata()
                print("Metadata:", meta)
            except Exception as e:
                print("Metadata ERROR:", e)

    except Exception as e:
        print("IMPORT FAILED:", e)
        print("TRACEBACK:")
        traceback.print_exc()


# ---------------------------------------------------------------------
# Scan non_os_specific
# ---------------------------------------------------------------------
nos_dir = CMD_ROOT / "non_os_specific"
print("\n=== NON-OS-SPECIFIC COMMANDS ===")
if nos_dir.exists():
    for file in sorted(nos_dir.glob("*.py")):
        if file.name.startswith("_"):
            continue
        module_name = f"Desktop_Assistant.commands.non_os_specific.{file.stem}"
        test_import(module_name)
else:
    print("non_os_specific folder missing!")

# ---------------------------------------------------------------------
# Scan OS-specific
# ---------------------------------------------------------------------
os_dir = CMD_ROOT / "os_specific"
print("\n=== OS-SPECIFIC COMMANDS ===")

if os_dir.exists():
    for os_key in ["windows", "macintosh", "linux"]:
        sub = os_dir / os_key
        print(f"\n--- {os_key.upper()} ---")
        if not sub.exists():
            print("Folder missing")
            continue

        for file in sorted(sub.glob("*.py")):
            if file.name.startswith("_"):
                continue
            module_name = f"Desktop_Assistant.commands.os_specific.{os_key}.{file.stem}"
            test_import(module_name)
else:
    print("os_specific folder missing!")

print("\n=== DIAGNOSTIC COMPLETE ===")
