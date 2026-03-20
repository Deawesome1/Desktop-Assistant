"""
commands/weather.py — Fetch current weather via Open-Meteo + geocoding.
No API key required. More reliable than wttr.in.
Triggers: "weather", "what's the weather", "weather in X", "temperature"
"""
import re
import json
import urllib.request
import urllib.parse
from bot.speaker import speak

DEFAULT_CITY = "Indianapolis"

# WMO weather condition codes → human readable
WMO_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "icy fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    71: "slight snow", 73: "moderate snow", 75: "heavy snow",
    80: "slight showers", 81: "moderate showers", 82: "heavy showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "heavy thunderstorm",
}


def _geocode(city: str) -> tuple[float, float] | None:
    """Get lat/lon for a city name using Open-Meteo's geocoding API."""
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


def run(query: str) -> str:
    q = query.lower()

    city = DEFAULT_CITY
    match = re.search(r"(?:weather in|weather for|weather at|temperature in)\s+(.+)", q)
    if match:
        city = match.group(1).strip().title()

    # Geocode the city
    coords = _geocode(city)
    if coords is None:
        speak(f"I couldn't find {city}. Try a different city name.")
        return f"Failed: could not geocode {city}"

    lat, lon = coords

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
            f"&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto"
        )
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read())

        current   = data["current"]
        temp      = round(current["temperature_2m"])
        feels     = round(current["apparent_temperature"])
        humidity  = current["relative_humidity_2m"]
        wind      = round(current["wind_speed_10m"])
        condition = WMO_CODES.get(current["weather_code"], "unknown conditions")

        response = (
            f"In {city}: {condition}, {temp} degrees Fahrenheit, "
            f"feels like {feels}. Humidity {humidity} percent, "
            f"wind {wind} miles per hour."
        )
        speak(response)
        return response

    except Exception as e:
        speak("I couldn't get the weather right now.")
        return f"Failed: weather error: {e}"