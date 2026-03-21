"""
dev.py — JARVIS development entry point.
Skips dependency checks and app scanning for fast startup.
Use main.py for full deployment.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from logs.logger import log_event, log_error
from bot.speaker import speak, get_response
from bot.context import ctx
from bot.listener import listen_once, is_cancel, _load_keywords
import bot.command_hub as command_hub

STAY_AWAKE_SENTINEL = "__STAY_AWAKE__"

log_event("JARVIS starting (dev mode).")
    ctx.start_app_watcher()
print("\n╔══════════════════════════════╗")
print("║    J.A.R.V.I.S.  [DEV]       ║")
print("╚══════════════════════════════╝")
print("  Dev mode — skipping dependency checks and app scan.")
print("  Listening. Say a wake word to activate. (Ctrl+C to quit)\n")

try:
    from bot.personality.engine import greet
    speak(greet())
except Exception:
    pass


def _get_wake_words() -> list[str]:
    try:
        return _load_keywords().get("wake_words", ["jarvis"])
    except Exception:
        return ["jarvis"]


def _parse_utterance(text: str) -> tuple[bool, str | None]:
    lower = text.lower().strip()
    for wake in sorted(_get_wake_words(), key=len, reverse=True):
        if wake.lower() in lower:
            remainder = lower.split(wake.lower(), 1)[-1].strip(" ,.")
            return True, (remainder if remainder else None)
    return False, None


def _run_command(command_input: str) -> bool:
    log_event(f"Command received: '{command_input}'")
    try:
        result = command_hub.handle(command_input)
        return result == STAY_AWAKE_SENTINEL
    except Exception as e:
        log_error("Unhandled exception in command_hub.handle()", exc=e)
        speak(get_response("command_failed"))
        return False


if __name__ == "__main__":
    try:
        while True:
            utterance = listen_once(prompt="[Listening]...", timeout=10)
            if not utterance:
                continue

            wake_found, command = _parse_utterance(utterance)
            if not wake_found:
                continue

            log_event(f"Wake word detected in: '{utterance}'")

            if command:
                print(f"[Inline] '{command}'")
                stay = _run_command(command)
            else:
                speak(get_response("wake_acknowledged"))
                speak(get_response("waiting_for_command"))
                command = listen_once(prompt="[Listening] Waiting for command...", timeout=8)

                if not command or is_cancel(command):
                    speak(get_response("cancelled"))
                    continue

                stay = _run_command(command)

            while stay:
                follow_up = listen_once(prompt="[Listening] Follow-up...", timeout=8)
                if not follow_up or is_cancel(follow_up):
                    speak(get_response("cancelled"))
                    break
                stay = _run_command(follow_up)

    except KeyboardInterrupt:
        speak(get_response("goodbye"))
        log_event("JARVIS shut down by user (KeyboardInterrupt).")
        print("\n[JARVIS] Goodbye.")
        try:
            from logs.logger import print_session_summary
            print_session_summary()
        except Exception:
            pass