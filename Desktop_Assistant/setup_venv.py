"""
setup_venv.py — Cross-platform virtual environment setup for JARVIS (Omega)

Creates:
    venv_windows/ on Windows
    venv_macos/   on macOS

Installs:
    requirements/base.txt
    requirements/<os>.txt

Uses:
    commands.os_scanner for OS detection
"""

import os
import subprocess
import sys
from commands.os_scanner import current_os
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    """Run a shell command safely."""
    print(f"→ {cmd}")
    subprocess.check_call(cmd, shell=True)


def create_venv(venv_path):
    """Create a virtual environment."""
    print(f"\nCreating virtual environment at: {venv_path}")
    run(f"{sys.executable} -m venv {venv_path}")


def install_requirements(venv_path):
    """Install requirements into the venv."""
    pip_path = (
        os.path.join(venv_path, "Scripts", "pip.exe")
        if current_os == "windows"
        else os.path.join(venv_path, "bin", "pip")
    )

    print(f"\nUsing pip at: {pip_path}")

    # Resolve absolute requirements directory
    req_dir = os.path.join(PROJECT_ROOT, "Desktop_Assistant", "requirements")

    # Base requirements
    base_req = os.path.join(req_dir, "base.txt")
    if os.path.exists(base_req):
        print("\nInstalling base requirements...")
        run(f'"{pip_path}" install -r "{base_req}"')
    else:
        print(f"Base requirements file not found at: {base_req}")

    # OS-specific requirements
    os_req_map = {
        "windows": "windows.txt",
        "macintosh": "mac.txt",
        "linux": "linux.txt",
    }

    os_req = os.path.join(req_dir, os_req_map.get(current_os, ""))

    if os.path.exists(os_req):
        print(f"\nInstalling {current_os} requirements...")
        run(f'"{pip_path}" install -r "{os_req}"')
    else:
        print(f"No OS-specific requirements found for {current_os} at: {os_req}")



def main():
    print(f"Detected OS: {current_os}")

    # Choose venv folder name
    venv_name = "venv_windows" if current_os == "windows" else "venv_macos"
    venv_path = os.path.join(os.getcwd(), venv_name)

    # Create venv
    create_venv(venv_path)

    # Install requirements
    install_requirements(venv_path)

    # Activation instructions
    print("\n✓ Virtual environment created successfully!")
    print("\nTo activate it:")

    if current_os == "windows":
        print(f'  {venv_name}\\Scripts\\activate')
    else:
        print(f'  source {venv_name}/bin/activate')

    print("\nYou're ready to run main.py!")


if __name__ == "__main__":
    main()
