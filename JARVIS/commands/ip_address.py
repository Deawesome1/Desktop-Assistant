"""
commands/ip_address.py — Report local or public IP address.
Triggers: "ip address", "what's my ip", "my ip", "public ip"
"""
import socket
import urllib.request
from bot.speaker import speak

def run(query: str) -> str:
    q = query.lower()

    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "unknown"

    if "public" in q or "external" in q:
        try:
            with urllib.request.urlopen("https://api.ipify.org", timeout=4) as resp:
                public_ip = resp.read().decode()
            response = f"Your public IP address is {public_ip}."
        except Exception:
            response = "I couldn't retrieve your public IP right now."
        speak(response)
        return response

    response = f"Your local IP address is {local_ip}."
    speak(response)
    return response