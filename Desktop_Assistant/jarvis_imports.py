"""
jarvis_imports.py
Centralized import router for JARVIS (Omega)

This file makes the system self-aware of its own structure.
All commands import from here instead of hardcoding paths.
"""

from pathlib import Path
import importlib


# ------------------------------------------------------------
# Detect project root dynamically
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent


def _import(path: str):
    """Safe dynamic import."""
    return importlib.import_module(path)


# ------------------------------------------------------------
# Brain + Engine
# ------------------------------------------------------------
def get_brain():
    return _import("Desktop_Assistant.brain.engine.brain").Brain


def get_speaker():
    return _import("Desktop_Assistant.brain.engine.speaker").speak


def get_listener():
    return _import("Desktop_Assistant.brain.engine.listener").listen


# ------------------------------------------------------------
# OS Scanner
# ------------------------------------------------------------
def get_current_os():
    return _import("Desktop_Assistant.commands.os_scanner").current_os


# ------------------------------------------------------------
# CommandHub
# ------------------------------------------------------------
def get_command_hub():
    return _import("Desktop_Assistant.commands.command_hub").CommandHub
