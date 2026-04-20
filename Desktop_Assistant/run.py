# run.py — FORCE JARVIS TO USE THE WORKING VENV

import os
import subprocess
from pathlib import Path

# ⭐ Hard‑lock to your working venv interpreter
VENV_PYTHON = r"A:\Python311_Test\venv\Scripts\python.exe"

def launch_jarvis():
    print("=== JARVIS BOOT MANAGER ===")
    print(f"Using interpreter: {VENV_PYTHON}")

    env = os.environ.copy()

    # Force DLL + package resolution to the venv
    venv_bin = str(Path(VENV_PYTHON).parent)
    env["PATH"] = venv_bin + os.pathsep + env["PATH"]
    env["PYTHONHOME"] = ""
    env["PYTHONPATH"] = ""

    print("\nLaunching JARVIS...\n")

    subprocess.check_call([VENV_PYTHON, "main.py"], env=env)

if __name__ == "__main__":
    launch_jarvis()
