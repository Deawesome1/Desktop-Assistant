"""
dependency_manager.py — Cross-platform dependency installer for JARVIS (Omega)
Updated to support requirements/ folder.
"""

import subprocess
import sys
import pkgutil
import logging
import os
from commands.os_scanner import current_os

logger = logging.getLogger("jarvis.dependency_manager")

REQ_DIR = "requirements"


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
    """
    if pkgutil.find_loader(package) is None:
        _pip_install(package)
    else:
        logger.debug(f"Package already installed: {package}")


# ------------------------------------------------------------
# Install base + OS-specific requirements
# ------------------------------------------------------------
def install_requirements():
    """
    Install base requirements + OS-specific requirements from requirements/ folder.
    """

    # Base file
    base_file = os.path.join(REQ_DIR, "base.txt")

    # OS-specific files
    os_files = {
        "windows": os.path.join(REQ_DIR, "windows.txt"),
        "macintosh": os.path.join(REQ_DIR, "mac.txt"),
        "linux": os.path.join(REQ_DIR, "linux.txt"),
    }

    # Install base
    if os.path.exists(base_file):
        logger.info("Installing base requirements...")
        _install_from_file(base_file)
    else:
        logger.warning("Base requirements file not found.")

    # Install OS-specific
    os_file = os_files.get(current_os)
    if os_file and os.path.exists(os_file):
        logger.info(f"Installing {current_os} requirements...")
        _install_from_file(os_file)
    else:
        logger.warning(f"No OS-specific requirements file found for {current_os}.")


# ------------------------------------------------------------
# Helper: install from file
# ------------------------------------------------------------
def _install_from_file(path: str):
    try:
        with open(path, "r") as f:
            for line in f:
                pkg = line.strip()
                if pkg and not pkg.startswith("#"):
                    ensure(pkg)
    except Exception as e:
        logger.error(f"Failed to read requirements file {path}: {e}")
