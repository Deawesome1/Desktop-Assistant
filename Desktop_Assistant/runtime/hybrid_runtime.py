# runtime/hybrid_runtime.py

from .voice_runtime import init_mic, voice_runtime
from .repl_runtime import repl_runtime


def hybrid_runtime():
    print("\n[Hybrid Mode] Auto-detecting microphone…")

    recognizer, mic = init_mic()

    if mic is None:
        print("[Hybrid] No microphone detected — switching to REPL.")
        return repl_runtime()

    print("[Hybrid] Microphone detected — switching to Voice Mode.")
    return voice_runtime()
