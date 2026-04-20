"""
listener.py — OS-aware listener router for JARVIS (Omega)
"""

from commands.os_scanner import current_os

if current_os == "macintosh":
    from .listener_mac import listen
elif current_os == "windows":
    from .listener_windows import listen
else:
    from .listener_linux import listen
