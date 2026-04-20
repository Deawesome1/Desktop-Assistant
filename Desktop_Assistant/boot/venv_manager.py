# boot/venv_manager.py — FINAL VERSION (handles list-based interpreters)

import os
import platform
import shutil
import subprocess
from pathlib import Path

MIN_PY = (3, 9)
MAX_PY = (3, 11)


def _detect_os():
    name = platform.system().lower()
    if "windows" in name:
        return "windows"
    if "darwin" in name or "mac" in name:
        return "macintosh"
    return "linux"


CURRENT_OS = _detect_os()


def _sh(cmd: list[str]):
    # Flatten nested lists (e.g. ["py","-3.11"] + ["-m","venv"])
    flat = []
    for item in cmd:
        if isinstance(item, list):
            flat.extend(item)
        else:
            flat.append(item)

    print("→", " ".join(flat))
    subprocess.check_call(flat)


def _get_python_version(python_exe: list[str]) -> tuple | None:
    try:
        out = subprocess.check_output(
            python_exe + ["-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
            text=True
        ).strip()
        major, minor = map(int, out.split())
        return major, minor
    except Exception:
        return None


def _is_compatible(ver: tuple) -> bool:
    return MIN_PY <= ver <= MAX_PY


def ensure_venv_with_interpreter(python_exe: list[str]) -> str:
    """
    Ensures venv exists AND uses a compatible interpreter.
    If venv exists but uses wrong Python → rebuild automatically.
    """

    venv_name = "venv_windows" if CURRENT_OS == "windows" else "venv_macos"
    venv_path = Path(venv_name)

    # Determine venv python path
    if CURRENT_OS == "windows":
        venv_python = venv_path / "Scripts" / "python.exe"
    else:
        venv_python = venv_path / "bin" / "python"

    # If venv exists, check its interpreter version
    if venv_path.exists() and venv_python.exists():
        ver = _get_python_version([str(venv_python)])
        if ver and _is_compatible(ver):
            print(f"✓ Virtual environment OK (Python {ver[0]}.{ver[1]})")
            return str(venv_python)

        print(f"❌ Existing venv uses incompatible Python {ver}. Rebuilding...")
        shutil.rmtree(venv_path)

    # Create new venv using the selected interpreter
    print(f"Creating virtual environment using: {python_exe}")
    _sh(python_exe + ["-m", "venv", venv_name])

    return str(venv_python)
