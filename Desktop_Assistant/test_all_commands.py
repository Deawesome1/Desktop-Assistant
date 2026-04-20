"""
test_all_commands.py — Unified command test harness for JARVIS
"""

import os
import sys
import importlib
import traceback
from pathlib import Path

# --- Path setup ---
ROOT = Path(__file__).resolve().parent
COMMANDS_DIR = ROOT / "commands"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- Inject fakes BEFORE importing any commands ---
from tests.fake_brain import FakeBrain
from tests.fake_speaker import fake_speaker_module
from tests.fake_listener import fake_listener_module
from tests.fake_jarvis import fake_jarvis
from tests.fake_context import fake_ctx

# Fake bot.speaker
sys.modules["bot.speaker"] = fake_speaker_module

# Fake bot.listener
sys.modules["bot.listener"] = fake_listener_module

# Fake bot.context.ctx
sys.modules["bot.context"] = type("FakeContextModule", (), {"ctx": fake_ctx})

# Fake JARVIS package + submodules
sys.modules["JARVIS"] = fake_jarvis
sys.modules["JARVIS.platform_utils"] = fake_jarvis.platform_utils

results = []


def safe_import(module_path: str):
    try:
        module = importlib.import_module(module_path)
        return module, None
    except Exception as e:
        return None, e


def safe_run(module, label: str):
    if not hasattr(module, "run"):
        return False, "No run() function"

    run_fn = module.run
    code = run_fn.__code__
    argcount = code.co_argcount

    brain = FakeBrain()
    user_text = "test input"

    try:
        if argcount == 0:
            run_fn()
        elif argcount == 1:
            run_fn(brain)
        else:
            run_fn(brain, user_text)

        return True, None

    except Exception as e:
        return False, e


def test_module(module_path: str, label: str):
    module, err = safe_import(module_path)
    if err:
        results.append((label, "FAIL", f"ImportError: {err}"))
        return

    ok, err = safe_run(module, label)
    if ok:
        results.append((label, "PASS", None))
    else:
        tb = "".join(traceback.format_exception_only(type(err), err)).strip()
        results.append((label, "FAIL", f"RuntimeError: {tb}"))


def discover_and_test():
    print("=== Running JARVIS Command Tests ===\n")

    # --- Non-OS-specific commands ---
    non_os = COMMANDS_DIR / "non_os_specific"
    if non_os.exists():
        for file in sorted(non_os.glob("*.py")):
            if file.name.startswith("_"):
                continue
            module_path = f"commands.non_os_specific.{file.stem}"
            test_module(module_path, file.stem)

    # --- OS-specific commands ---
    os_specific = COMMANDS_DIR / "os_specific"
    current_os = sys.platform.lower()

    if "win" in current_os:
        os_dir = os_specific / "windows"
        prefix = "commands.os_specific.windows"
    elif "darwin" in current_os:
        os_dir = os_specific / "macintosh"
        prefix = "commands.os_specific.macintosh"
    else:
        os_dir = os_specific / "linux"
        prefix = "commands.os_specific.linux"

    if os_dir.exists():
        for file in sorted(os_dir.glob("*.py")):
            if file.name.startswith("_"):
                continue
            module_path = f"{prefix}.{file.stem}"
            label = f"{file.stem}_{os_dir.name}"
            test_module(module_path, label)

    print("\n=== Test Results ===\n")
    for name, status, err in results:
        if status == "PASS":
            print(f"[PASS] {name}")
        else:
            print(f"[FAIL] {name} — {err}")

    print("\n=== Summary ===")
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {len(results)}")

if __name__ == "__main__":
    discover_and_test()
