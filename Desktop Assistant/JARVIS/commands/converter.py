"""
commands/converter.py — Unit conversion.
Triggers: "convert X miles to kilometers", "how many X in Y"
"""
import re
from bot.speaker import speak

UNITS = {
    # Length (base: meter)
    "meter": 1, "meters": 1, "metre": 1, "metres": 1,
    "kilometer": 1000, "kilometers": 1000, "km": 1000,
    "mile": 1609.34, "miles": 1609.34,
    "yard": 0.9144, "yards": 0.9144,
    "foot": 0.3048, "feet": 0.3048, "ft": 0.3048,
    "inch": 0.0254, "inches": 0.0254,
    "centimeter": 0.01, "centimeters": 0.01, "cm": 0.01,
    "millimeter": 0.001, "millimeters": 0.001, "mm": 0.001,
    # Weight (base: gram)
    "gram": 1, "grams": 1,
    "kilogram": 1000, "kilograms": 1000, "kg": 1000,
    "pound": 453.592, "pounds": 453.592, "lb": 453.592, "lbs": 453.592,
    "ounce": 28.3495, "ounces": 28.3495, "oz": 28.3495,
    "ton": 907185, "tons": 907185,
    # Volume (base: liter)
    "liter": 1, "liters": 1, "litre": 1, "litres": 1,
    "milliliter": 0.001, "milliliters": 0.001, "ml": 0.001,
    "gallon": 3.78541, "gallons": 3.78541,
    "pint": 0.473176, "pints": 0.473176,
    "cup": 0.236588, "cups": 0.236588,
    # Temperature (handled separately)
    "celsius": "temp", "centigrade": "temp",
    "fahrenheit": "temp", "kelvin": "temp",
    # Speed (base: m/s)
    "mph": 0.44704,
    "miles per hour": 0.44704,
    "kph": 0.27778,
    "kilometers per hour": 0.27778,
    "km per hour": 0.27778,
    "km/h": 0.27778,
    "kilometers per second": 1000,
    "km per second": 1000,
    "km/s": 1000,
    "meters per second": 1,
    "m per second": 1,
    "m/s": 1,
    "knot": 0.514444, "knots": 0.514444,
    # Data (base: byte)
    "byte": 1, "bytes": 1,
    "kilobyte": 1024, "kilobytes": 1024, "kb": 1024,
    "megabyte": 1048576, "megabytes": 1048576, "mb": 1048576,
    "gigabyte": 1073741824, "gigabytes": 1073741824, "gb": 1073741824,
}

TEMP_UNITS = {"celsius", "centigrade", "fahrenheit", "kelvin"}


def _convert_temp(value: float, from_unit: str, to_unit: str) -> float:
    if from_unit == "fahrenheit":
        c = (value - 32) * 5 / 9
    elif from_unit == "kelvin":
        c = value - 273.15
    else:
        c = value
    if to_unit == "fahrenheit":
        return c * 9 / 5 + 32
    elif to_unit == "kelvin":
        return c + 273.15
    return c


def _resolve(raw: str) -> str | None:
    """Find the best matching unit key for a spoken unit string."""
    r = raw.lower().strip()
    if r in UNITS:
        return r
    # Try without trailing 's' for plurals
    if r.rstrip("s") in UNITS:
        return r.rstrip("s")
    # Try multi-word units (longest match first)
    for key in sorted(UNITS.keys(), key=len, reverse=True):
        if key in r:
            return key
    return None


def run(query: str) -> str:
    q = query.lower().strip()
    for prefix in ["convert", "how many", "how much", "what is", "what's"]:
        q = q.replace(prefix, "").strip()

    # Pattern A: "5 miles to kilometers"
    m = re.search(r"([\d.]+)\s+([\w/ ]+?)\s+(?:to|in|into)\s+([\w/ ]+?)$", q.strip())
    if m:
        value    = float(m.group(1))
        from_raw = m.group(2).strip()
        to_raw   = re.sub(r"^\d+[\d.]*\s*", "", m.group(3).strip())
    else:
        # Pattern B: "how many feet in 2 meters"
        m2 = re.search(r"([\w/ ]+?)\s+in\s+([\d.]+)\s+([\w/ ]+?)$", q.strip())
        if m2:
            value    = float(m2.group(2))
            from_raw = m2.group(3).strip()   # source unit
            to_raw   = m2.group(1).strip()   # target unit
        else:
            speak("Try saying: convert 5 miles to kilometers.")
            return "Failed: couldn't parse conversion"
    from_key = _resolve(from_raw)
    to_key   = _resolve(to_raw)

    if not from_key or not to_key:
        unknown = from_raw if not from_key else to_raw
        speak(f"I don't recognise the unit '{unknown}'.")
        return f"Failed: unknown unit '{unknown}'"

    if from_key in TEMP_UNITS or to_key in TEMP_UNITS:
        result = _convert_temp(value, from_key, to_key)
    else:
        ff = UNITS[from_key]
        tf = UNITS[to_key]
        if isinstance(ff, str) or isinstance(tf, str):
            speak("I can't mix unit types like length and temperature.")
            return "Failed: incompatible units"
        result = value * ff / tf

    result_str = str(int(result)) if result == int(result) else f"{result:.4f}".rstrip("0").rstrip(".")
    response = f"{value} {from_raw} is {result_str} {to_raw}."
    speak(response)
    return response