"""
run.py — JARVIS Boot Manager

Boot sequence:
 1. Verify caller Python range
 2. Select a compatible interpreter
 3. Ensure venv exists and uses compatible Python
 4. Install dependencies into the venv
 5. Build the app scanner cache inside the venv (OS-aware)
 6. Version tracking + update check
 7. Launch main.py using the venv interpreter
"""

import os
import subprocess
from pathlib import Path

from .python_checker import verify_python_range
from .python_selector import select_python_interpreter
from .venv_manager import ensure_venv_with_interpreter
from .dependency_manager import install_all_dependencies
from .version_manager import load_version, record_version
from .updater import check_for_updates


def _sh(cmd: list[str]):
    print("→", " ".join(cmd))
    subprocess.check_call(cmd)


def launch_jarvis():
    print("=== JARVIS BOOT MANAGER ===")

    # ------------------------------------------------------------
    # 1. Project root + main.py
    # ------------------------------------------------------------
    project_root = Path(__file__).resolve().parents[2]
    main_py = project_root / "main.py"

    # ------------------------------------------------------------
    # 2. Verify caller Python range
    # ------------------------------------------------------------
    verify_python_range()

    # ------------------------------------------------------------
    # 3. Select a compatible interpreter
    # ------------------------------------------------------------
    interpreter = select_python_interpreter()
    if interpreter is None:
        print("\n❌ No compatible Python (3.9–3.11) found.")
        print("Please install Python 3.10 (recommended).")
        return

    print(f"✓ Compatible Python selected: {' '.join(interpreter)}")

    # ------------------------------------------------------------
    # 4. Ensure venv exists and uses compatible Python
    # ------------------------------------------------------------
    venv_python = ensure_venv_with_interpreter(interpreter)
    print(f"✓ Virtual environment ready: {venv_python}")

    # ------------------------------------------------------------
    # 5. Install dependencies into the venv
    # ------------------------------------------------------------
    install_all_dependencies(venv_python)

    # ------------------------------------------------------------
    # 6. Build the app scanner cache inside the venv
    # ------------------------------------------------------------
    print("\n=== Building application cache ===")
    _sh([
        venv_python,
        "-c",
        (
            "from Desktop_Assistant.commands.app_scanner import build_cache; "
            "build_cache(force=True)"
        ),
    ])
    print("✓ Application cache built.")

    # ------------------------------------------------------------
    # 7. Version tracking + update check
    # ------------------------------------------------------------
    old_version = load_version()
    record_version()
    check_for_updates(old_version)

    # ------------------------------------------------------------
    # 8. Launch main.py using the venv interpreter
    # ------------------------------------------------------------
    print("\n✓ Boot sequence complete. Launching JARVIS...\n")

    env = os.environ.copy()
    cmd = f'"{venv_python}" -m Desktop_Assistant.main'
    subprocess.check_call(cmd, env=env, shell=True, cwd=str(project_root))


if __name__ == "__main__":
    launch_jarvis()
