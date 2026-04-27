# Desktop_Assistant/boot/dependency_manager.py
"""
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
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from .boot_utils import run
from Desktop_Assistant.boot.path_hub import PROJECT_ROOT, OS_KEY as current_os, package_path

# Config
REQ_CACHE = PROJECT_ROOT / ".jarvis_requirements_hash"
FREEZE_FILE = PROJECT_ROOT / ".jarvis_installed.txt"
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = 2  # seconds (exponential backoff)
DISABLE_DEPENDENCY_CHECKS = False

# macOS-specific constants
MAC_PORTAUDIO_PKG = "portaudio"
MAC_PYAUDIO_PIP_NAME = "pyaudio"


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


def _run_with_retries(cmd: str, attempts: int = RETRY_ATTEMPTS, env: Optional[dict] = None) -> None:
    last_exc = None
    for i in range(1, attempts + 1):
        try:
            run(cmd, env=env)
            return
        except Exception as exc:
            last_exc = exc
            wait = RETRY_BACKOFF ** (i - 1)
            print(f"[DependencyManager] Attempt {i} failed for: {cmd}. Retrying in {wait}s...")
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
# macOS preflight helpers
# -------------------------
def _is_macos() -> bool:
    return current_os == "macintosh"


def _ensure_xcode_cli() -> None:
    """
    Ensure Xcode command line tools are installed. Non-fatal if user must accept dialog.
    """
    try:
        if shutil.which("xcode-select") is None:
            print("[DependencyManager] xcode-select not found; skipping Xcode CLI install.")
            return
        out = subprocess.run(["xcode-select", "-p"], capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return
        print("[DependencyManager] Installing Xcode command line tools (may prompt)...")
        subprocess.run(["xcode-select", "--install"], check=False)
    except Exception as e:
        print("[DependencyManager] Xcode CLI install attempt failed:", e)


def _ensure_homebrew() -> None:
    """
    Ensure Homebrew is installed. If not, attempt non-interactive install.
    """
    if shutil.which("brew"):
        return
    print("[DependencyManager] Homebrew not found; attempting install (may require user interaction).")
    try:
        subprocess.run(
            ["/bin/bash", "-c", '$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)'],
            check=False,
        )
    except Exception as e:
        print("[DependencyManager] Homebrew install attempt failed:", e)


def _ensure_portaudio_via_brew() -> None:
    """
    Install PortAudio via Homebrew. Idempotent.
    """
    if shutil.which("brew") is None:
        print("[DependencyManager] brew not available; skipping PortAudio install.")
        return
    try:
        print("[DependencyManager] Ensuring PortAudio (brew install portaudio)...")
        subprocess.run(["brew", "update"], check=False)
        subprocess.run(["brew", "install", MAC_PORTAUDIO_PKG], check=False)
    except Exception as e:
        print("[DependencyManager] PortAudio install attempt failed:", e)


def _portaudio_env_flags() -> dict:
    """
    Return environment variables required for pip to find PortAudio headers/libs.
    """
    env = os.environ.copy()
    try:
        if shutil.which("brew"):
            out = subprocess.run(["brew", "--prefix", MAC_PORTAUDIO_PKG], capture_output=True, text=True)
            prefix = out.stdout.strip() if out.returncode == 0 else None
            if not prefix:
                out2 = subprocess.run(["brew", "--prefix"], capture_output=True, text=True)
                prefix = out2.stdout.strip() if out2.returncode == 0 else None
            if prefix:
                lib = os.path.join(prefix, "lib")
                include = os.path.join(prefix, "include")
                pkgcfg = os.path.join(prefix, "lib", "pkgconfig")
                env["LDFLAGS"] = f"-L{lib} " + env.get("LDFLAGS", "")
                env["CPPFLAGS"] = f"-I{include} " + env.get("CPPFLAGS", "")
                env["PKG_CONFIG_PATH"] = f"{pkgcfg}:{env.get('PKG_CONFIG_PATH','')}"
    except Exception:
        pass
    return env


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

    req_dir = package_path("requirements")
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

    # macOS preflight: ensure system deps for pyaudio
    if _is_macos():
        try:
            _ensure_xcode_cli()
            _ensure_homebrew()
            _ensure_portaudio_via_brew()
        except Exception as e:
            print("[DependencyManager] macOS preflight failed:", e)

    # Upgrade pip/setuptools/wheel first (best practice)
    try:
        print("\n[DependencyManager] Upgrading pip, setuptools, wheel inside venv...")
        _run_with_retries(f'{pip_cmd} install --upgrade pip setuptools wheel')
    except Exception as e:
        print("[DependencyManager] pip upgrade failed:", e)

    # Prepare environment for pip installs (macOS PortAudio flags)
    env = None
    if _is_macos():
        env = _portaudio_env_flags()

    # Install base requirements
    if base_req.exists():
        try:
            print("\n[DependencyManager] Installing base requirements from:", base_req)
            _run_with_retries(f'{pip_cmd} install -r "{base_req}"', env=env)
        except Exception as e:
            print("[DependencyManager] Failed to install base requirements:", e)
            raise
    else:
        print(f"[DependencyManager] Base requirements file not found at: {base_req}")

    # Install OS-specific requirements
    if os_req.exists():
        try:
            print(f"\n[DependencyManager] Installing {current_os} requirements from:", os_req)
            _run_with_retries(f'{pip_cmd} install -r "{os_req}"', env=env)
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

    # If on macOS and package is pyaudio, ensure PortAudio is present and export flags
    env = None
    if _is_macos() and package.lower() in (MAC_PYAUDIO_PIP_NAME, "pyaudio"):
        try:
            _ensure_xcode_cli()
            _ensure_homebrew()
            _ensure_portaudio_via_brew()
            env = _portaudio_env_flags()
        except Exception as e:
            print("[DependencyManager] macOS runtime preflight failed:", e)

    try:
        print(f"[DependencyManager] Package '{package}' missing — attempting install via {python_exec} -m pip")
        _run_with_retries(f'{pip_cmd} install {package}', env=env)
        # After install, update freeze (best-effort)
        try:
            _write_freeze(python_exec)
        except Exception:
            pass
        return importlib.util.find_spec(package) is not None
    except Exception as e:
        print(f"[DependencyManager] Runtime install failed for {package}: {e}")
        return False
