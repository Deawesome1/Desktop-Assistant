"""
commands/top_processes.py — Report what's using the most CPU or RAM.
Triggers: "what's using cpu", "top processes", "what's running", "memory hog"
"""
from bot.speaker import speak


def run(query: str) -> str:
    try:
        import psutil
        q = query.lower()
        by_ram = any(w in q for w in ["ram", "memory", "mem"])

        procs = []
        for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except Exception:
                pass

        # Second pass for accurate CPU (first call always returns 0)
        import time
        time.sleep(0.5)
        for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
            try:
                for existing in procs:
                    if existing["name"] == p.info["name"]:
                        existing["cpu_percent"] = p.info["cpu_percent"]
            except Exception:
                pass

        key = "memory_percent" if by_ram else "cpu_percent"
        top = sorted(procs, key=lambda x: x.get(key, 0) or 0, reverse=True)[:5]

        label = "RAM" if by_ram else "CPU"
        lines = []
        for i, p in enumerate(top, 1):
            val = p.get(key, 0) or 0
            lines.append(f"{p['name']} at {val:.1f} percent")

        response = f"Top {label} users: " + ", ".join(lines) + "."
        speak(response)
        return response

    except ImportError:
        speak("This requires psutil. Run pip install psutil.")
        return "Not installed: psutil"
    except Exception as e:
        speak("I couldn't get process info.")
        return f"Failed: {e}"