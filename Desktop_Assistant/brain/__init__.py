# Correct __init__.py for the new modular brain structure

from .engine.brain import Brain

# Optional convenience accessor (if you still want it)
_global_brain = None

def get_brain(config_path="config/brain.json"):
    global _global_brain
    if _global_brain is None:
        _global_brain = Brain(config_path=config_path)
    return _global_brain

__all__ = ["Brain", "get_brain"]
