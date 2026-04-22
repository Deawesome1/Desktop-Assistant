# diagnose_loader.py

from pathlib import Path
import importlib

print("\n=== LOADER DIAGNOSTIC ===")

# 1) Show where we are
root = Path(__file__).resolve().parent
print("Project root:", root)

# 2) Where Python thinks Desktop_Assistant is
pkg_path = root / "Desktop_Assistant"
print("Desktop_Assistant exists:", pkg_path.exists())

# 3) Commands dir
commands_dir = pkg_path / "commands"
print("commands dir:", commands_dir)
print("commands dir exists:", commands_dir.exists())

# 4) List non_os_specific + os_specific/windows
nos_dir = commands_dir / "non_os_specific"
win_dir = commands_dir / "os_specific" / "windows"

print("\nnon_os_specific exists:", nos_dir.exists())
if nos_dir.exists():
    print("non_os_specific files:")
    for f in sorted(nos_dir.glob("*.py")):
        print("  -", f.name)

print("\nos_specific/windows exists:", win_dir.exists())
if win_dir.exists():
    print("os_specific/windows files:")
    for f in sorted(win_dir.glob("*.py")):
        print("  -", f.name)

# 5) Try importing one known module explicitly
print("\n=== IMPORT TESTS ===")
tests = [
    "Desktop_Assistant.commands.non_os_specific.greet",
    "Desktop_Assistant.commands.non_os_specific.calculator",
    "Desktop_Assistant.commands.os_specific.windows.volume",
]

for mod_name in tests:
    try:
        m = importlib.import_module(mod_name)
        print(f"IMPORT OK: {mod_name}")
        if hasattr(m, "get_metadata"):
            print("  metadata:", m.get_metadata())
    except Exception as e:
        print(f"IMPORT FAIL: {mod_name} -> {e}")

print("\n=== DONE ===")
