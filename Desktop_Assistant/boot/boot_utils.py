# Desktop_Assistant/boot/boot_utils.py
import os
import platform
import subprocess
from pathlib import Path
from typing import Optional, Tuple

# PROJECT_ROOT resolves to repository root (one level above launch.py)
PROJECT_ROOT = Path(__file__).resolve().parents[1].parent

_sys = platform.system().lower()
if "windows" in _sys:
    current_os = "windows"
elif "darwin" in _sys:
    current_os = "macintosh"
else:
    current_os = "linux"

def log(msg: str, level: str = "info") -> None:
    print(f"[{level.upper()}] {msg}")

def run(cmd: str, cwd: Optional[Path] = None, env: Optional[dict] = None) -> int:
    log(cmd, "debug")
    return subprocess.check_call(cmd, shell=True, cwd=str(cwd) if cwd else None, env=env)

def run_capture(cmd: str, cwd: Optional[Path] = None, env: Optional[dict] = None, timeout: Optional[int] = None) -> Tuple[str,str,int]:
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(cwd) if cwd else None, env=env)
    out, err = proc.communicate(timeout=timeout)
    return out.decode(errors="ignore"), err.decode(errors="ignore"), proc.returncode

def which(exe: str) -> Optional[Path]:
    from shutil import which as _which
    p = _which(exe)
    return Path(p) if p else None

def venv_paths(venv_path: Path) -> dict:
    if current_os == "windows":
        return {
            "python": str(venv_path / "Scripts" / "python.exe"),
            "pip": str(venv_path / "Scripts" / "pip.exe"),
            "activate": str(venv_path / "Scripts" / "activate"),
        }
    else:
        return {
            "python": str(venv_path / "bin" / "python"),
            "pip": str(venv_path / "bin" / "pip"),
            "activate": str(venv_path / "bin" / "activate"),
        }

def resolve_req_dir() -> Path:
    return PROJECT_ROOT / "Desktop_Assistant" / "requirements"
