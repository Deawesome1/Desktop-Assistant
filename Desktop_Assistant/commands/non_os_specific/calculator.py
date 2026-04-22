"""
calculator.py — JARVIS Command
Evaluate natural-language math expressions.

Examples:
    "calculate 5 plus 7"
    "what is 20 percent of 80"
    "square root of 144"
    "solve 5 squared minus 3"
"""

# ------------------------------------------------------------
# Central import surface
# ------------------------------------------------------------
from Desktop_Assistant import imports as I

# Standard libs via import surface
re = I.re

import math
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------
# Command metadata
# ------------------------------------------------------------

COMMAND_NAME: str = "calculator"
COMMAND_ALIASES: List[str] = ["calc", "math", "compute", "solve"]
COMMAND_DESCRIPTION: str = "Evaluates natural-language math expressions."
COMMAND_OS_SUPPORT: List[str] = ["windows", "macintosh", "linux"]
COMMAND_CATEGORY: str = "utility"
COMMAND_REQUIRES_INTERNET: bool = False
COMMAND_REQUIRES_ADMIN: bool = False


# ------------------------------------------------------------
# Metadata API
# ------------------------------------------------------------

def get_metadata() -> Dict[str, Any]:
    return {
        "name": COMMAND_NAME,
        "aliases": COMMAND_ALIASES,
        "description": COMMAND_DESCRIPTION,
        "os_support": COMMAND_OS_SUPPORT,
        "category": COMMAND_CATEGORY,
        "requires_internet": COMMAND_REQUIRES_INTERNET,
        "requires_admin": COMMAND_REQUIRES_ADMIN,
    }


def is_supported_on_os(os_key: str) -> bool:
    return os_key in COMMAND_OS_SUPPORT


# ------------------------------------------------------------
# Internal math parsing logic
# ------------------------------------------------------------

def _parse_and_eval(q: str) -> Optional[float]:
    """
    Convert natural language math into a safe expression and evaluate it.
    Returns float or None if parsing fails.
    """

    q = q.lower().strip()

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
        (r"multiplied by", "*"),
        (r"divided by", "/"),
        (r"over",    "/"),
        (r"x",       "*"),
        (r"pi",      str(math.pi)),
        (r"\be\b",   str(math.e)),
    ]

    expr = q
    for pattern, repl in replacements:
        expr = re.sub(pattern, repl, expr, flags=re.IGNORECASE)

    expr = re.sub(r"[^0-9\+\-\*\/\(\)\.\%\^ sqrtcbrt]", "", expr)
    expr = expr.replace("^", "**").strip()

    expr = re.sub(
        r"sqrt\s*\(?(\d+[\d\.]*)\)?",
        lambda m: str(math.sqrt(float(m.group(1)))),
        expr,
    )
    expr = re.sub(
        r"cbrt\s*\(?(\d+[\d\.]*)\)?",
        lambda m: str(round(float(m.group(1)) ** (1/3), 6)),
        expr,
    )

    if not expr:
        return None

    try:
        result = eval(expr, {"__builtins__": {}}, {})
        return float(result)
    except Exception:
        return None


# ------------------------------------------------------------
# Public run() entrypoint
# ------------------------------------------------------------

def run(
    brain,
    user_text: str,
    args: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    if args is None:
        args = []
    if context is None:
        context = {}

    os_key = I.os_key()
    if not is_supported_on_os(os_key):
        return {
            "success": False,
            "message": f"The calculator command is not supported on {os_key}.",
            "data": {"os_key": os_key},
        }

    q = user_text.lower().strip()
    prefixes = ["calculate", "what is", "what's", "how much is", "solve", "compute"]
    for p in prefixes:
        if q.startswith(p):
            q = q[len(p):].strip()

    result = _parse_and_eval(q)
    if result is None:
        brain.event("user_confused")
        return {
            "success": False,
            "message": "I couldn't work that out. Try phrasing it differently.",
            "data": {"expression": q},
        }

    if result == int(result):
        result_str = str(int(result))
    else:
        result_str = f"{result:.6f}".rstrip("0").rstrip(".")

    response = f"The answer is {result_str}."

    brain.event("task_success")
    brain.remember("technical_queries", f"calc: {user_text} = {result_str}")

    return {
        "success": True,
        "message": response,
        "data": {
            "expression": q,
            "result": result,
            "formatted": result_str,
        },
    }
