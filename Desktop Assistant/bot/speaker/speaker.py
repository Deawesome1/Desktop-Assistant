"""
speaker.py — OS-aware speaker router for JARVIS (Omega)
"""

from commands.os_scanner import current_os

if current_os == "macintosh":
    from .speaker_mac import speak
elif current_os == "windows":
    from .speaker_windows import speak
else:
    from .speaker_linux import speak
