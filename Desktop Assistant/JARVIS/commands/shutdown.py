"""
commands/shutdown.py — Cross-platform shutdown, restart, sleep, lock.
DISABLED by default in commands.json. Enable when ready.
"""
from bot.speaker import speak
from JARVIS.platform_utils import shutdown, restart, sleep_system, lock_screen


def run(query: str) -> str:
    q = query.lower()

    if any(w in q for w in ["restart", "reboot"]):
        speak("Restarting in 10 seconds.")
        restart(10)
        return "Restart initiated."

    if any(w in q for w in ["sleep", "hibernate", "suspend"]):
        speak("Going to sleep.")
        sleep_system()
        return "Sleep initiated."

    if any(w in q for w in ["lock"]):
        speak("Locking your screen.")
        lock_screen()
        return "Screen locked."

    if any(w in q for w in ["shutdown", "shut down", "turn off"]):
        speak("Shutting down in 10 seconds.")
        shutdown(10)
        return "Shutdown initiated."

    speak("Say shutdown, restart, sleep, or lock.")
    return "Failed: no power action matched"