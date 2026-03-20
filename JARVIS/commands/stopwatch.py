"""
commands/stopwatch.py — Start, stop, lap, reset a stopwatch.
State is stored in sys.modules to survive across different import paths.
"""
import sys
import time
from bot.speaker import speak

# Store state in sys.modules so it persists regardless of how this
# module gets imported (commands.stopwatch, direct import, etc.)
if "_jarvis_stopwatch_state" not in sys.modules:
    sys.modules["_jarvis_stopwatch_state"] = type(sys)("_jarvis_stopwatch_state")
    sys.modules["_jarvis_stopwatch_state"].data = {
        "start_time": None,
        "running":    False,
        "laps":       [],
    }

_state = sys.modules["_jarvis_stopwatch_state"].data


def _elapsed() -> float:
    return (time.time() - _state["start_time"]) if _state["start_time"] else 0.0


def _fmt(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:   return f"{h} hours, {m} minutes, {s} seconds"
    if m:   return f"{m} minutes and {s} seconds"
    return f"{s} seconds"


def run(query: str) -> str:
    q = query.lower()

    if "reset" in q or "clear" in q:
        _state["start_time"] = None
        _state["running"]    = False
        _state["laps"]       = []
        speak("Stopwatch reset.")
        return "Stopwatch reset."

    if "lap" in q:
        if not _state["running"]:
            speak("The stopwatch isn't running.")
            return "Failed: stopwatch not running"
        elapsed = _elapsed()
        _state["laps"].append(elapsed)
        response = f"Lap {len(_state['laps'])}: {_fmt(elapsed)}."
        speak(response)
        return response

    if "start" in q or "begin" in q:
        if _state["running"]:
            speak(f"Stopwatch already running at {_fmt(_elapsed())}.")
            return f"Already running: {_fmt(_elapsed())}"
        _state["start_time"] = time.time()
        _state["running"]    = True
        speak("Stopwatch started.")
        return "Stopwatch started."

    if "stop" in q or "end" in q:
        if not _state["running"]:
            speak("The stopwatch isn't running.")
            return "Failed: not running"
        elapsed = _elapsed()
        _state["running"]    = False
        _state["start_time"] = None
        response = f"Stopwatch stopped at {_fmt(elapsed)}."
        speak(response)
        return response

    # Status check
    if _state["running"]:
        response = f"Stopwatch is at {_fmt(_elapsed())}."
    else:
        response = "Stopwatch is not running."
    speak(response)
    return response