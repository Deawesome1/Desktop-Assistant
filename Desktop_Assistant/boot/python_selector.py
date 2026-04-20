# boot/python_selector.py — FINAL VERSION (returns arg list)

import shutil
import subprocess
import sys

MIN_PY = (3, 9)
MAX_PY = (3, 11)


def _check_python_version(executable: list[str]) -> tuple | None:
    try:
        out = subprocess.check_output(
            executable + ["-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
            text=True
        ).strip()
        major, minor = map(int, out.split())
        return major, minor
    except Exception:
        return None


def _is_compatible(ver: tuple) -> bool:
    return MIN_PY <= ver <= MAX_PY


def select_python_interpreter() -> list[str] | None:
    """
    Returns a LIST of arguments, e.g.:
      ["python3.11"]
      ["py", "-3.11"]
    """

    candidates: list[list[str]] = []

    # 1. Current interpreter
    candidates.append([sys.executable])

    # 2. PATH-based names
    for name in ["python3.11", "python3.10", "python3.9", "python3", "python"]:
        path = shutil.which(name)
        if path:
            candidates.append([path])

    # 3. py.exe launcher (Windows)
    for tag in ["3.11", "3.10", "3.9"]:
        candidates.append(["py", f"-{tag}"])

    # Evaluate all candidates
    for exe in candidates:
        ver = _check_python_version(exe)
        if ver and _is_compatible(ver):
            print(f"✓ Compatible Python found: {' '.join(exe)} ({ver[0]}.{ver[1]})")
            return exe

    return None
