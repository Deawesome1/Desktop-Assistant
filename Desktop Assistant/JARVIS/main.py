"""
main.py — JARVIS entry point.

Listening model:
  Every utterance is checked for a wake word + command in one pass.
  If a wake word is detected with a command attached, dispatch immediately.
  If just the wake word is heard alone, prompt for a command.
  No separate idle/awake states — one continuous listen loop.
"""
import subprocess, sys, os

# Auto-activate venv if not already active
_venv_python = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "venv", "Scripts", "python.exe")
)

if os.path.exists(_venv_python) and os.path.abspath(sys.executable) != _venv_python:
    subprocess.run([_venv_python] + sys.argv)
    sys.exit()

sys.path.insert(0, os.path.dirname(__file__))

# ── Step 1: Dependencies ──────────────────────────────────────────────────────
from dependency_manager import check_and_install
if not check_and_install():
    print("\n  JARVIS cannot start. Please install the required packages and try again.")
    sys.exit(1)

# ── Step 2: All other imports ─────────────────────────────────────────────────
from logs.logger import log_event, log_error
from bot.speaker import speak, get_response
from bot.listener import listen_once, is_cancel, _load_keywords
import bot.command_hub as command_hub

STAY_AWAKE_SENTINEL = "__STAY_AWAKE__"


def _startup():
    log_event("JARVIS starting up.")
    print("\n╔══════════════════════════════╗")
    print("║         J.A.R.V.I.S.         ║")
    print("╚══════════════════════════════╝\n")

    try:
        import json
        config_path = os.path.join(os.path.dirname(__file__), "config", "apps_config.json")
        scan_on_startup = True
        if os.path.exists(config_path):
            with open(config_path) as f:
                scan_on_startup = json.load(f).get("scan_on_startup", True)
        from commands.app_scanner import get_cache, rescan
        cache = rescan() if scan_on_startup else get_cache()
        print(f"  App directory ready: {cache.get('app_count', 0)} apps indexed.\n")
    except Exception as e:
        log_error("App scanner failed during startup", exc=e)
        print(f"  Warning: app scanner failed ({e}).\n")

    try:
        from commands.reminder import restore_pending
        restore_pending()
    except Exception as e:
        log_error("Failed to restore reminders", exc=e)

    print("  Listening. Say a wake word to activate. (Ctrl+C to quit)\n")


def _get_wake_words() -> list[str]:
    try:
        return _load_keywords().get("wake_words", ["jarvis"])
    except Exception:
        return ["jarvis"]


def _parse_utterance(text: str) -> tuple[bool, str | None]:
    """
    Parse a raw utterance.
    Returns (wake_word_found, command_text_or_None).
    command_text is None if only the wake word was said.
    """
    lower = text.lower().strip()
    wake_words = sorted(_get_wake_words(), key=len, reverse=True)

    for wake in wake_words:
        if wake.lower() in lower:
            remainder = lower.split(wake.lower(), 1)[-1].strip(" ,.")
            return True, (remainder if remainder else None)

    return False, None


def _run_command(command_input: str) -> bool:
    """Dispatch a command. Returns True if JARVIS should stay awake."""
    log_event(f"Command received: '{command_input}'")
    try:
        result = command_hub.handle(command_input)
        return result == STAY_AWAKE_SENTINEL
    except Exception as e:
        log_error("Unhandled exception in command_hub.handle()", exc=e)
        speak(get_response("command_failed"))
        return False


def _await_command(prompt: str = "[Listening] Waiting for command...") -> str | None:
    return listen_once(prompt=prompt, timeout=8)


def main():
    _startup()

    while True:
        # ── Single continuous listen ──────────────────────────────────────────
        utterance = listen_once(prompt="[Listening]...", timeout=10)

        if not utterance:
            continue

        wake_found, command = _parse_utterance(utterance)

        if not wake_found:
            # No wake word — ignore
            continue

        # Wake word detected
        log_event(f"Wake word detected in: '{utterance}'")

        if command:
            # Inline command — "jarvis open notepad" → dispatch immediately
            print(f"[Inline] '{command}'")
            stay = _run_command(command)
        else:
            # Wake word only — prompt for command
            speak(get_response("wake_acknowledged"))
            speak(get_response("waiting_for_command"))
            command = _await_command()

            if not command:
                speak(get_response("cancelled"))
                continue

            if is_cancel(command):
                speak(get_response("cancelled"))
                continue

            stay = _run_command(command)

        # ── Stay-awake loop ───────────────────────────────────────────────────
        # If the command returned STAY_AWAKE, keep listening for follow-ups
        # without requiring the wake word again.
        while stay:
            log_event("Staying awake for follow-up.")
            follow_up = _await_command()

            if not follow_up or is_cancel(follow_up):
                speak(get_response("cancelled"))
                break

            stay = _run_command(follow_up)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        speak(get_response("goodbye"))
        log_event("JARVIS shut down by user (KeyboardInterrupt).")
        print("\n[JARVIS] Goodbye.")