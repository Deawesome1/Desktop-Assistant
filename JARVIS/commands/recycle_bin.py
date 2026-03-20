"""
commands/recycle_bin.py — Cross-platform trash emptying.
Windows: SHEmptyRecycleBinW. Mac: Finder AppleScript. Linux: gio/shutil.
"""
from bot.speaker import speak
from JARVIS.platform_utils import empty_trash


def run(query: str) -> str:
    if empty_trash():
        speak("Trash emptied.")
        return "Trash emptied."
    else:
        speak("I couldn't empty the trash.")
        return "Failed: empty trash failed"