# Desktop_Assistant/commands/non_os_specific/voice_toggle.py
def run(brain, user_text):
    """
    Toggle voice speaking on/off.
    Usage: 'voice toggle' or create aliases 'speak on', 'speak off' if desired.
    """
    try:
        current = brain.get_setting("voice_speaking_enabled", True)
    except Exception:
        # fallback to memory if get_setting not available
        mem = brain.memory.get("voice_speaking_enabled") if hasattr(brain, "memory") else None
        current = mem if isinstance(mem, bool) else True

    new = not bool(current)
    try:
        brain.set_setting("voice_speaking_enabled", new)
    except Exception:
        try:
            brain.remember("voice_speaking_enabled", {"value": new})
        except Exception:
            pass

    return {"success": True, "message": f"Voice speaking {'enabled' if new else 'disabled'}", "data": {"voice_speaking_enabled": new}}
