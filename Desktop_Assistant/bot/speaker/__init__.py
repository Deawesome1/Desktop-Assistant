# Desktop_Assistant/bot/speaker/__init__.py
"""
Re-export the canonical speaker module so both layouts work.
"""

try:
    # Prefer the single-file canonical module
    from Desktop_Assistant.bot.speaker import speak, speak_async  # type: ignore
except Exception:
    # If package layout is used, try to import speaker.speaker
    try:
        from Desktop_Assistant.bot.speaker.speaker import speak, speak_async  # type: ignore
    except Exception:
        # Final fallback: minimal no-op implementations
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

__all__ = ["speak", "speak_async"]
