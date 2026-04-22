"""
dependency_manager.py — Cross-platform dependency installer for JARVIS (Omega)
Updated to support requirements/ folder.
"""

from Desktop_Assistant import imports as I
from importlib import util
import subprocess
import sys
import logging
import os
from pathlib import Path

logger = logging.getLogger("jarvis.dependency_manager")

DISABLE_DEPENDENCY_CHECKS = False

# Resolve absolute path to requirements/ folder
PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQ_DIR = PROJECT_ROOT / "requirements"


# ------------------------------------------------------------
# Helper: pip install
# ------------------------------------------------------------
def _pip_install(package: str):
    try:
        logger.info(f"Installing missing package: {package}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except Exception as e:
        logger.error(f"Failed to install {package}: {e}")


# ------------------------------------------------------------
# Public: ensure a package is installed
# ------------------------------------------------------------
def ensure(package: str):
    """
    Ensure a Python package is installed.
    Skips installation when DISABLE_DEPENDENCY_CHECKS is True.
    """
    if DISABLE_DEPENDENCY_CHECKS:
        logger.debug(f"[DependencyManager] Skipping ensure('{package}') — dependency checks disabled.")
        return

    try:
        if util.find_spec(package) is None:
            logger.warning(f"[DependencyManager] Package '{package}' missing — installing...")
            _pip_install(package)
        else:
            logger.debug(f"[DependencyManager] Package already installed: {package}")
    except Exception as e:
        logger.error(f"[DependencyManager] Error checking package '{package}': {e}")


# ------------------------------------------------------------
# Install base + OS-specific requirements
# ------------------------------------------------------------
def install_requirements():
    """
    Install base requirements + OS-specific requirements from requirements/ folder.
    """

    os_key = I.os_key()

    # Base file
    base_file = REQ_DIR / "base.txt"

    # OS-specific files
    os_files = {
        "windows": REQ_DIR / "windows.txt",
        "macintosh": REQ_DIR / "mac.txt",
        "linux": REQ_DIR / "linux.txt",
    }

    # Install base
    if base_file.exists():
        logger.info("Installing base requirements...")
        _install_from_file(base_file)
    else:
        logger.warning("Base requirements file not found.")

    # Install OS-specific
    os_file = os_files.get(os_key)
    if os_file and os_file.exists():
        logger.info(f"Installing {os_key} requirements...")
        _install_from_file(os_file)
    else:
        logger.warning(f"No OS-specific requirements file found for {os_key}.")


# ------------------------------------------------------------
# Helper: install from file
# ------------------------------------------------------------
def _install_from_file(path: Path):
    try:
        with open(path, "r") as f:
            for line in f:
                pkg = line.strip()
                if pkg and not pkg.startswith("#"):
                    ensure(pkg)
    except Exception as e:
        logger.error(f"Failed to read requirements file {path}: {e}")
