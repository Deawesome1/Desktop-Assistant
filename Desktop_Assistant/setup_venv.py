# Desktop_Assistant/setup_venv.py
"""
Cross-platform virtual environment setup for JARVIS (Omega)

Creates:
    venv_windows/ on Windows
    venv_macos/   on macOS
    venv_linux/   on Linux

Installs:
    requirements/base.txt
    requirements/<os>.txt

Uses the centralized path hub for robust path resolution and OS detection.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from Desktop_Assistant.boot.path_hub import repo_path, package_path, OS_KEY, venv_paths


def run(cmd: str) -> None:
    """Run a shell command safely (prints and raises on failure)."""
    print(f"→ {cmd}")
    subprocess.check_call(cmd, shell=True)


def create_venv(venv_path: Path) -> None:
    """Create a virtual environment at venv_path."""
    print(f"\nCreating virtual environment at: {venv_path}")
    run(f'"{sys.executable}" -m venv "{str(venv_path)}"')


def install_requirements(venv_path: Path) -> None:
    """Install requirements into the venv at venv_path."""
    # Determine pip path using venv_paths helper
    paths = venv_paths(venv_path)
    pip_path = paths.get("pip")
    if not pip_path:
        raise RuntimeError("Could not determine pip path for venv")

    print(f"\nUsing pip at: {pip_path}")

    # Resolve requirements directory via package_path
    req_dir = package_path("requirements")

    # Base requirements
    base_req = req_dir / "base.txt"
    if base_req.exists():
        print("\nInstalling base requirements...")
        run(f'"{pip_path}" install -r "{str(base_req)}"')
    else:
        print(f"Base requirements file not found at: {base_req}")

    # OS-specific requirements
    os_map = {"windows": "windows.txt", "macintosh": "mac.txt", "linux": "linux.txt"}
    os_req = req_dir / os_map.get(OS_KEY, "")

    if os_req.exists():
        print(f"\nInstalling {OS_KEY} requirements...")
        run(f'"{pip_path}" install -r "{str(os_req)}"')
    else:
        print(f"No OS-specific requirements found for {OS_KEY} at: {os_req}")


def main() -> None:
    print(f"Detected OS: {OS_KEY}")

    # Choose venv folder name
    venv_name = "venv_windows" if OS_KEY == "windows" else ("venv_macos" if OS_KEY == "macintosh" else "venv_linux")
    venv_path = Path(os.getcwd()) / venv_name

    # Create venv
    create_venv(venv_path)

    # Install requirements
    install_requirements(venv_path)

    # Activation instructions
    print("\n✓ Virtual environment created successfully!")
    print("\nTo activate it:")

    if OS_KEY == "windows":
        print(f'  {venv_name}\\Scripts\\activate')
    else:
        print(f'  source {venv_name}/bin/activate')

    print("\nYou're ready to run main.py!")


if __name__ == "__main__":
    main()
