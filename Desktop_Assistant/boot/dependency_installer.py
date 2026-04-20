# boot/dependency_installer.py

import subprocess
from pathlib import Path


def _sh(cmd: list[str]):
    print("→", " ".join(cmd))
    subprocess.check_call(cmd)


def install_all_dependencies(venv_python: str):
    """
    Uses the venv's python to run dependency_manager.install_requirements()
    so it works regardless of caller Python version.
    """
    print("\n=== Installing JARVIS dependencies ===")

    if not Path("dependency_manager.py").exists():
        print("⚠ dependency_manager.py not found. Skipping managed install.")
        return

    _sh([
        venv_python,
        "-c",
        "from dependency_manager import install_requirements; install_requirements()",
    ])

    print("✓ Dependencies installed.")
