# runtime/hub.py

from .repl_runtime import repl_runtime
from .voice_runtime import voice_runtime
from .hybrid_runtime import hybrid_runtime
from .daemon_runtime import daemon_runtime


def choose_runtime_mode():
    print("\n===============================================")
    print("        OMEGA / JARVIS — Runtime Selector")
    print("===============================================")
    print("1. Text REPL (Debug Mode)")
    print("2. Voice Mode")
    print("3. Hybrid Mode (Auto-Detect)")
    print("4. Daemon Mode (Silent)")
    print("-----------------------------------------------")

    choice = input("Select a mode (1-4): ").strip()

    return {
        "1": "repl",
        "2": "voice",
        "3": "hybrid",
        "4": "daemon"
    }.get(choice, "repl")


def run_runtime(mode: str):
    if mode == "repl":
        repl_runtime()
    elif mode == "voice":
        voice_runtime()
    elif mode == "hybrid":
        hybrid_runtime()
    elif mode == "daemon":
        daemon_runtime()
