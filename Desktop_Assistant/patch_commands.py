"""
patch_everything.py
Global aggressive import patcher for JARVIS (Omega)

Patches:
 - Desktop_Assistant/commands/**
 - Desktop_Assistant/bot/**
 - Desktop_Assistant/brain/**
 - Desktop_Assistant/brain/engine/**

Removes ANY import line containing:
 brain, bot, speaker, listener, engine, pyttsx3, commands.os_scanner (old form)

Then inserts correct modular imports for command files.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET_DIRS = [
    ROOT / "Desktop_Assistant" / "commands",
    ROOT / "Desktop_Assistant" / "bot",
    ROOT / "Desktop_Assistant" / "brain",
    ROOT / "Desktop_Assistant" / "brain" / "engine",
]

BAD_KEYWORDS = [
    "brain",
    "bot",
    "speaker",
    "listener",
    "engine",
    "pyttsx3",
    "commands.os_scanner",
]

CORRECT_IMPORTS = """import re
import math
from typing import Any, Dict, List, Optional

from Desktop_Assistant.commands.os_scanner import current_os
"""

def patch_file(path: Path):
    original = path.read_text().splitlines()
    cleaned = []

    for line in original:
        stripped = line.strip()
        if stripped.startswith("from") or stripped.startswith("import"):
            if any(keyword in stripped for keyword in BAD_KEYWORDS):
                print(f"  Removed: {stripped}")
                continue
        cleaned.append(line)

    text = "\n".join(cleaned)
    text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)

    # Only commands get the modular import block
    if "commands" in str(path):
        lines = text.splitlines()
        idx = 0

        if lines and lines[0].startswith("#!"):
            idx = 1

        if idx < len(lines) and lines[idx].startswith('"""'):
            idx += 1
            while idx < len(lines) and not lines[idx].startswith('"""'):
                idx += 1
            idx += 1

        text = (
            "\n".join(lines[:idx])
            + "\n\n"
            + CORRECT_IMPORTS
            + "\n"
            + "\n".join(lines[idx:])
        )

    path.write_text(text)
    print(f"Patched: {path}")


def scan_and_patch():
    for folder in TARGET_DIRS:
        print(f"\n=== PATCHING {folder} ===")
        for file in folder.rglob("*.py"):
            if not file.name.startswith("_"):
                patch_file(file)

    print("\n=== GLOBAL PATCH COMPLETE ===")


if __name__ == "__main__":
    scan_and_patch()
