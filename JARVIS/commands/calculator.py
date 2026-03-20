"""
commands/calculator.py — Evaluate math expressions spoken naturally.
Triggers: "calculate", "what is", "what's", "how much is", "solve", "square root", "percent"
"""
import re
import math
from bot.speaker import speak

def _parse_and_eval(q: str) -> float | None:
    # Natural language replacements
    replacements = [
        (r"squared",              "**2"),
        (r"cubed",                "**3"),
        (r"square root of",       "sqrt"),
        (r"cube root of",         "cbrt"),
        (r"(\d+)\s*percent of\s*(\d+[\d\.]*)", r"(\1/100)*\2"),
        (r"(\d+)\s*%\s*of\s*(\d+[\d\.]*)",     r"(\1/100)*\2"),
        (r"plus",    "+"),
        (r"minus",   "-"),
        (r"times",   "*"),
        (r"divided by", "/"),
        (r"over",    "/"),
        (r"x",       "*"),
        (r"pi",      str(math.pi)),
        (r"e\b",     str(math.e)),
    ]
    expr = q
    for pattern, repl in replacements:
        expr = re.sub(pattern, repl, expr, flags=re.IGNORECASE)

    # Strip non-math characters
    expr = re.sub(r"[^0-9\+\-\*\/\(\)\.\%\^sqrt cbrt ]", "", expr)
    expr = expr.replace("^", "**").strip()

    # Handle sqrt/cbrt
    expr = re.sub(r"sqrt\s*\(?(\d+[\d\.]*)\)?", lambda m: str(math.sqrt(float(m.group(1)))), expr)
    expr = re.sub(r"cbrt\s*\(?(\d+[\d\.]*)\)?", lambda m: str(round(float(m.group(1))**(1/3), 6)), expr)

    if not expr:
        return None
    try:
        result = eval(expr, {"__builtins__": {}}, {})
        return float(result)
    except Exception:
        return None


def run(query: str) -> str:
    q = query.lower()
    for prefix in ["calculate", "what is", "what's", "how much is", "solve", "compute"]:
        q = q.replace(prefix, "").strip()

    result = _parse_and_eval(q)
    if result is None:
        speak("I couldn't work that out. Try phrasing it differently.")
        return "Failed: could not parse expression"

    # Format cleanly
    if result == int(result):
        result_str = str(int(result))
    else:
        result_str = f"{result:.6f}".rstrip("0").rstrip(".")

    response = f"The answer is {result_str}."
    speak(response)
    return response