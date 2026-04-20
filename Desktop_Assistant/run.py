# run.py — JARVIS Boot Manager + Launcher

from pathlib import Path
import subprocess

from boot.python_checker import verify_python_range
from boot.python_selector import select_python_interpreter
from boot.venv_manager import ensure_venv_with_interpreter
from boot.dependency_installer import install_all_dependencies
from boot.version_manager import load_version, record_version
from boot.updater import check_for_updates


def launch_jarvis(venv_python: str):
    print("\n✓ Boot sequence complete. Launching JARVIS...\n")
    subprocess.check_call([venv_python, "main.py"])


def main():
    print("=== JARVIS BOOT MANAGER ===")

    # 1. Check current Python (IDE / caller)
    verify_python_range()

    # 2. Find a compatible Python interpreter (3.9–3.11)
    interpreter = select_python_interpreter()
    if interpreter is None:
        print("\n❌ No compatible Python (3.9–3.11) found on this system.")
        print("Please install Python 3.10 (recommended) from:")
        print("  https://www.python.org/downloads/release/python-31011/")
        return

    print(f"✓ Using interpreter: {interpreter}")

    # 3. Ensure venv exists using that interpreter
    venv_python = ensure_venv_with_interpreter(interpreter)

    # 4. Install dependencies into that venv
    install_all_dependencies(venv_python)

    # 5. Version tracking
    old_version = load_version()
    record_version()

    # 6. Update check (non-blocking)
    check_for_updates(old_version)

    # 7. Launch JARVIS
    launch_jarvis(venv_python)


if __name__ == "__main__":
    main()
