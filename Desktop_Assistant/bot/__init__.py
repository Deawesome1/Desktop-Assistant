# Desktop_Assistant/bot/__init__.py
"""
Bot package initializer for JARVIS.

Expose speak helper and provide lazy accessors for listener to avoid
circular imports during boot.
"""

# Re-export speak/speak_async from the speaker module
try:
    from Desktop_Assistant.bot.speaker import speak, speak_async  # type: ignore
except Exception:
    # Fallback no-op if import fails
    def speak(text: str, *, brain=None, block: bool = True) -> None:
        try:
            print(f"JARVIS: {text}")
        except Exception:
            pass

    def speak_async(text: str, *, brain=None) -> None:
        try:
            print(f"JARVIS (async): {text}")
        except Exception:
            pass

# Provide a lazy listener loader to avoid importing listener at package import time.
def get_listener():
    """
    Return the platform listener function. Import lazily to avoid import-time errors.
    Usage:
        listen = get_listener()
        text = listen(brain)
    """
    try:
        # Try package-qualified import
        from Desktop_Assistant.listener import listener as _listener_mod  # type: ignore
        return getattr(_listener_mod, "listen", None)
    except Exception:
        try:
            # Relative fallback
            from .listener import listener as _listener_mod  # type: ignore
            return getattr(_listener_mod, "listen", None)
        except Exception:
            return None
