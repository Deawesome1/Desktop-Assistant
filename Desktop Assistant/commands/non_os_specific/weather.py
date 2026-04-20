"""
weather.py — JARVIS Command
Fetch current weather using Open‑Meteo + geocoding (no API key required).

Examples:
    "weather"
    "what's the weather"
    "weather in Chicago"
    "temperature in Miami"
"""

import re
import json
import urllib.request
import urllib.parse
from typing import Any, Dict, List, Optional
from brain import Brain


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "weather"
COMMAND_ALIASES: List[str] = [
    "weather", "what's the weather", "temperature", "weather in",
    "weather for", "weather at", "temperature in"
]
COMMAND_DESCRIPTION: str = "Fetches current weather conditions using Open‑Meteo."
COMMAND_OS_SUPPORT: List[str] = ["windows", "macintosh", "linux"]
COMMAND_CATEGORY: str = "information"
COMMAND_REQUIRES_INTERNET: bool = True
COMMAND_REQUIRES_ADMIN: bool = False

DEFAULT_CITY = "Indianapolis"


# ---------------------------------------------------------------------------
# Metadata API
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# WMO weather condition codes
# ---------------------------------------------------------------------------

WMO_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "icy fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    71: "slight snow", 73: "moderate snow", 75: "heavy snow",
    80: "slight showers", 81: "moderate showers", 82: "heavy showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "heavy thunderstorm",
}


# ---------------------------------------------------------------------------
# Geocoding helper
# ---------------------------------------------------------------------------

def _geocode(city: str) -> Optional[tuple[float, float]]:
    """Get lat/lon for a city name using Open‑Meteo's geocoding API."""
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
    try:
        with urllib.request.urlopen(url, timeout=6) as resp:
            data = json.loads(resp.read())
        results = data.get("results", [])
        if not results:
            return None
        return results[0]["latitude"], results[0]["longitude"]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public run() entrypoint
# ---------------------------------------------------------------------------

def run(
    brain: Brain,
    user_text: str,
    args: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    if args is None:
        args = []
    if context is None:
        context = {}

    os_key = brain.get_current_os_key()
    if not is_supported_on_os(os_key):
        return {
            "success": False,
            "message": f"The weather command is not supported on {os_key}.",
            "data": {"os_key": os_key},
        }

    q = user_text.lower()

    # ----------------------------------------------------------------------
    # Detect city
    # ----------------------------------------------------------------------
    city = DEFAULT_CITY
    match = re.search(r"(?:weather in|weather for|weather at|temperature in)\s+(.+)", q)
    if match:
        city = match.group(1).strip().title()

    # ----------------------------------------------------------------------
    # Geocode
    # ----------------------------------------------------------------------
    coords = _geocode(city)
    if coords is None:
        brain.event("user_confused")
        return {
            "success": False,
            "message": f"I couldn't find {city}. Try a different city name.",
            "data": {"city": city},
        }

    lat, lon = coords

    # ----------------------------------------------------------------------
    # Fetch weather
    # ----------------------------------------------------------------------
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
            f"&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto"
        )

        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read())

        current = data["current"]
        temp = round(current["temperature_2m"])
        feels = round(current["apparent_temperature"])
        humidity = current["relative_humidity_2m"]
        wind = round(current["wind_speed_10m"])
        condition = WMO_CODES.get(current["weather_code"], "unknown conditions")

        response = (
            f"In {city}: {condition}, {temp} degrees Fahrenheit, "
            f"feels like {feels}. Humidity {humidity} percent, "
            f"wind {wind} miles per hour."
        )

        # Brain integration
        brain.event("task_success")
        brain.remember("weather_queries", f"{city}: {temp}F {condition}")

        return {
            "success": True,
            "message": response,
            "data": {
                "city": city,
                "temperature_f": temp,
                "feels_like_f": feels,
                "humidity_percent": humidity,
                "wind_mph": wind,
                "condition": condition,
                "lat": lat,
                "lon": lon,
            },
        }

    except Exception as e:
        brain.event("user_confused")
        return {
            "success": False,
            "message": "I couldn't get the weather right now.",
            "data": {"error": str(e)},
        }
