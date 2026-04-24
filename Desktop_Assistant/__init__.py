# Desktop_Assistant/__init__.py
from __future__ import annotations

import os
import threading
from typing import Optional

# Lazy import to avoid import-time cycles
Brain = None
_brain_lock = threading.Lock()
_global_brain: Optional["Brain"] = None

def _load_brain_class():
    global Brain
    if Brain is None:
        # local import to avoid circular imports at package import time
        from .engine.brain import Brain as _Brain
        Brain = _Brain
    return Brain

def get_brain(config_path: Optional[str] = None):
    """
    Return a shared Brain instance. Pass config_path to override the default.
    Uses a thread-safe lazy singleton pattern.
    """
    global _global_brain
    if config_path is None:
        config_path = os.environ.get("JARVIS_BRAIN_CONFIG", "config/brain.json")

    if _global_brain is None:
        with _brain_lock:
            if _global_brain is None:
                BrainClass = _load_brain_class()
                _global_brain = BrainClass(config_path=config_path)
    return _global_brain

__all__ = ["get_brain"]
