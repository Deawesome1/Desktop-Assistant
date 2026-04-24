"""
Desktop_Assistant.boot.dependency_manager

Combined boot + runtime dependency manager.

Public API:
  - install_all_dependencies(venv_python: str, force: bool=False, dry_run: bool=False)
  - ensure(package: str, venv_python: str | None = None, timeout: int | None = None) -> bool

Design goals:
  - Use "<venv_python> -m pip" to avoid broken pip.exe launchers on Windows.
  - Install base + OS-specific requirements from Desktop_Assistant/requirements/.
  - Record a requirements hash and pip freeze to skip redundant installs.
  - Provide a conservative runtime `ensure()` that can auto-install missing packages.
  - No side effects at import time.
"""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from .boot_utils import PROJECT_ROOT, current_os, run, resolve_req_dir

# Config
REQ_CACHE = PROJECT_ROOT / ".jarvis_requirements_hash"
FREEZE_FILE = PROJECT_ROOT / ".jarvis_installed.txt"
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = 2  # seconds (exponential backoff)
DISABLE_DEPENDENCY_CHECKS = False


# -------------------------
# Internal helpers
# -------------------------
def _file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _combined_requirements_hash(files: List[Path]) -> str:
    h = hashlib.sha256()
    for f in files:
        if f.exists():
            h.update(f.read_bytes())
    return h.hexdigest()


def _run_with_retries(cmd: str, attempts: int = RETRY_ATTEMPTS) -> None:
    last_exc = None
    for i in range(1, attempts + 1):
        try:
            run(cmd)
            return
        except Exception as exc:
            last_exc = exc
            wait = RETRY_BACKOFF ** (i - 1)
            print(f"[DependencyManager] Attempt {i} failed. Retrying in {wait}s...")
            time.sleep(wait)
    raise last_exc


def _pip_cmd_for_venv(venv_python: str) -> str:
    """
    Return a safe pip command string using the provided venv python.
    Example: '"C:\\path\\to\\venv\\Scripts\\python.exe" -m pip'
    """
    p = Path(venv_python).resolve()
    return f'"{str(p)}" -m pip'


def _write_freeze(venv_python: str) -> None:
    try:
        cmd = f'{_pip_cmd_for_venv(venv_python)} freeze > "{FREEZE_FILE}"'
        run(cmd)
    except Exception:
        # best-effort; don't fail the whole boot if freeze fails
        pass


def _installed_from_freeze(package: str) -> bool:
    if not FREEZE_FILE.exists():
        return False
    try:
        lines = FREEZE_FILE.read_text(encoding="utf-8").splitlines()
        pkg_lower = package.lower()
        for line in lines:
            if line.lower().startswith(pkg_lower + "==") or line.lower().startswith(pkg_lower + " @"):
                return True
    except Exception:
        return False
    return False


# -------------------------
# Public: Boot installer
# -------------------------
def install_all_dependencies(venv_python: str, force: bool = False, dry_run: bool = False) -> None:
    """
    Install base + OS-specific requirements into the provided venv python.

    Args:
      venv_python: absolute path to the venv python executable (string)
      force: if True, force reinstall even if requirements unchanged
      dry_run: if True, only print what would be installed
    """
    venv_python_path = Path(venv_python).resolve()
    if not venv_python_path.exists():
        raise FileNotFoundError(f"venv python not found at: {venv_python_path}")

    pip_cmd = _pip_cmd_for_venv(str(venv_python_path))

    req_dir = resolve_req_dir()
    base_req = req_dir / "base.txt"
    os_map = {"windows": "windows.txt", "macintosh": "mac.txt", "linux": "linux.txt"}
    os_req = req_dir / os_map.get(current_os, "")

    combined_hash = _combined_requirements_hash([base_req, os_req])

    if REQ_CACHE.exists() and not force:
        prev = REQ_CACHE.read_text(encoding="utf-8").strip()
        if prev == combined_hash:
            print("[DependencyManager] Requirements unchanged; skipping install.")
            return

    if dry_run:
        print("[DependencyManager] Dry run mode. Would install:")
        if base_req.exists():
            print(" -", base_req)
        if os_req.exists():
            print(" -", os_req)
        return

    # Upgrade pip/setuptools/wheel first (best practice)
    try:
        print("\n[DependencyManager] Upgrading pip, setuptools, wheel inside venv...")
        _run_with_retries(f'{pip_cmd} install --upgrade pip setuptools wheel')
    except Exception as e:
        print("[DependencyManager] pip upgrade failed:", e)

    # Install base requirements
    if base_req.exists():
        try:
            print("\n[DependencyManager] Installing base requirements from:", base_req)
            _run_with_retries(f'{pip_cmd} install -r "{base_req}"')
        except Exception as e:
            print("[DependencyManager] Failed to install base requirements:", e)
            raise
    else:
        print(f"[DependencyManager] Base requirements file not found at: {base_req}")

    # Install OS-specific requirements
    if os_req.exists():
        try:
            print(f"\n[DependencyManager] Installing {current_os} requirements from:", os_req)
            _run_with_retries(f'{pip_cmd} install -r "{os_req}"')
        except Exception as e:
            print(f"[DependencyManager] Failed to install {current_os} requirements:", e)
            raise
    else:
        print(f"[DependencyManager] No OS-specific requirements found for {current_os} at: {os_req}")

    # Record freeze and hash
    try:
        _write_freeze(str(venv_python_path))
        REQ_CACHE.write_text(combined_hash, encoding="utf-8")
    except Exception:
        pass

    print("\n[DependencyManager] Dependencies installed.")


# -------------------------
# Public: Runtime ensure
# -------------------------
def ensure(package: str, venv_python: Optional[str] = None, timeout: Optional[int] = None) -> bool:
    """
    Ensure a Python package is importable. If missing, attempt a conservative install.

    Args:
      package: package name (as used in importlib.util.find_spec)
      venv_python: optional path to venv python to use for installation; if None, uses sys.executable
      timeout: reserved for future use (not blocking now)

    Returns:
      True if the package is importable after this call, False otherwise.
    """
    if DISABLE_DEPENDENCY_CHECKS:
        print(f"[DependencyManager] Skipping ensure('{package}') — dependency checks disabled.")
        return False

    try:
        if importlib.util.find_spec(package) is not None:
            return True
    except Exception:
        # If find_spec fails for some reason, continue to attempt install
        pass

    # Check recorded freeze first (fast)
    if _installed_from_freeze(package):
        # reload import system check
        try:
            return importlib.util.find_spec(package) is not None
        except Exception:
            pass

    # Attempt install using provided venv python or sys.executable
    python_exec = venv_python or sys.executable
    pip_cmd = f'"{python_exec}" -m pip'

    try:
        print(f"[DependencyManager] Package '{package}' missing — attempting install via {python_exec} -m pip")
        _run_with_retries(f'{pip_cmd} install {package}')
        # After install, update freeze (best-effort)
        try:
            _write_freeze(python_exec)
        except Exception:
            pass
        return importlib.util.find_spec(package) is not None
    except Exception as e:
        print(f"[DependencyManager] Runtime install failed for {package}: {e}")
        return False
