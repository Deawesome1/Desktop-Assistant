# Desktop_Assistant/boot/run.py
"""
JARVIS Boot Manager

Boot sequence:
 1. Verify caller Python range
 2. Select a compatible interpreter
 3. Ensure venv exists and uses compatible Python
 4. Install dependencies into the venv
 5. Build the app scanner cache inside the venv (OS-aware)
 6. Version tracking + update check
 7. Launch main.py using the venv interpreter (nonblocking by default)
"""

from __future__ import annotations

import os
import subprocess
import sys
import logging
from pathlib import Path
from typing import Sequence, Optional

from .python_checker import verify_python_range
from .python_selector import select_python_interpreter
from .venv_manager import ensure_venv_with_interpreter
from .dependency_manager import install_all_dependencies
from .version_manager import load_version, record_version
from .updater import check_for_updates

logger = logging.getLogger("jarvis.boot")
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [boot] %(message)s"))
    logger.addHandler(ch)
logger.setLevel(logging.INFO)


def _sh(cmd: Sequence[str]) -> None:
    """Run a command and raise on nonzero exit."""
    logger.info("→ %s", " ".join(cmd))
    subprocess.check_call(list(cmd))


def _run_in_venv(venv_python: str, module: str, cwd: str, env: Optional[dict] = None, block: bool = False) -> Optional[subprocess.Popen]:
    """
    Launch a Python module inside the venv.
    If block is True, wait for the process to exit and return None.
    If block is False, return the Popen object so the caller can manage it.
    """
    cmd = [venv_python, "-m", module]
    env = env or os.environ.copy()
    logger.info("Launching: %s", " ".join(cmd))
    proc = subprocess.Popen(cmd, env=env, cwd=cwd, shell=False)
    if block:
        try:
            proc.wait()
        except KeyboardInterrupt:
            logger.info("Interrupted while waiting for child process; terminating")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        return None
    return proc


def launch_jarvis(run_in_process: bool = False, block_child: bool = False) -> None:
    """
    Main boot entry.

    Parameters
    - run_in_process: if True, import and run Desktop_Assistant.main in this process.
      Useful for debugging; not recommended for normal use.
    - block_child: if True and run_in_process is False, wait for the child process to exit.
      If False, the launcher returns after starting the child.
    """
    print("=== JARVIS BOOT MANAGER ===")

    # Project root and main module
    project_root = Path(__file__).resolve().parents[2]
    main_module = "Desktop_Assistant.main"

    # 1 Verify caller Python range
    verify_python_range()

    # 2 Select a compatible interpreter
    interpreter = select_python_interpreter()
    if interpreter is None:
        print("\n❌ No compatible Python (3.9–3.11) found.")
        print("Please install Python 3.10 (recommended).")
        return

    # interpreter may be a sequence like ['py', '-3.11'] or a single path
    # prefer a single executable path string for subprocess calls
    if isinstance(interpreter, (list, tuple)):
        venv_candidate = interpreter[0]
    else:
        venv_candidate = interpreter

    print(f"✓ Compatible Python selected: {' '.join(interpreter) if isinstance(interpreter, (list, tuple)) else interpreter}")

    # 3 Ensure venv exists and uses compatible Python
    venv_python = ensure_venv_with_interpreter(interpreter)
    print(f"✓ Virtual environment ready: {venv_python}")

    # 4 Install dependencies into the venv
    install_all_dependencies(venv_python)

    # 5 Build the app scanner cache inside the venv
    print("\n=== Building application cache ===")
    _sh([venv_python, "-c", "from Desktop_Assistant.commands.app_scanner import build_cache; build_cache(force=True)"])
    print("✓ Application cache built.")

    # 6 Version tracking + update check
    old_version = load_version()
    record_version()
    check_for_updates(old_version)

    # 7 Launch main.py using the venv interpreter
    print("\n✓ Boot sequence complete. Launching JARVIS...\n")
    env = os.environ.copy()

    if run_in_process:
        # Import and run main in this process (useful for debugging)
        logger.info("Running Desktop_Assistant.main in-process (debug mode)")
        try:
            # Ensure project root is on sys.path
            sys.path.insert(0, str(project_root))
            import Desktop_Assistant.main as main_mod  # type: ignore
            if hasattr(main_mod, "main"):
                main_mod.main()
            else:
                logger.error("Desktop_Assistant.main has no main() entrypoint")
        except KeyboardInterrupt:
            logger.info("Interrupted in-process run; exiting")
        except Exception as e:
            logger.exception("In-process run failed: %s", e)
        return

    # Launch as a child process using the venv Python
    proc = _run_in_venv(venv_python, main_module, cwd=str(project_root), env=env, block=block_child)

    if proc is None:
        # We blocked and waited for the child; nothing more to do
        return

    # If we started a child and are not blocking, monitor it lightly and return
    logger.info("Child process started with PID %s", proc.pid)
    try:
        # Optionally wait for the child to exit while allowing KeyboardInterrupt to be handled
        if block_child:
            proc.wait()
    except KeyboardInterrupt:
        logger.info("Launcher interrupted by user; terminating child process")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    # Default behavior: spawn child and block until it exits so CLI behaves as before.
    # If you prefer the launcher to return immediately after starting the child, call with block_child=False.
    launch_jarvis(run_in_process=False, block_child=True)
