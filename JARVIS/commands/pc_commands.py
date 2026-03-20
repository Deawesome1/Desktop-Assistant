"""
commands/shutdown.py — Shutdown, restart, sleep, or lock the computer.
Triggers: "shutdown", "restart", "sleep", "lock"
DISABLED in commands.json by default. Enable it there when you're ready.
"""
import os
import subprocess
from bot.speaker import speak

def run(query: str) -> str:
    q = query.lower()

    if "restart" in q or "reboot" in q:
        speak("Restarting in 10 seconds.")
        os.system("shutdown /r /t 10")
        return "Restart initiated."

    if "sleep" in q or "hibernate" in q:
        speak("Going to sleep.")
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return "Sleep initiated."

    if "lock" in q:
        speak("Locking your PC.")
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return "PC locked."

    if "shutdown" in q or "shut down" in q or "turn off" in q:
        speak("Shutting down in 10 seconds.")
        os.system("shutdown /s /t 10")
        return "Shutdown initiated."

    speak("I didn't catch what you wanted. Say shutdown, restart, sleep, or lock.")
    return "No power action matched."