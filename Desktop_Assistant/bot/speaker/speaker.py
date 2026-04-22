"""
speaker.py — OS-aware speaker router for JARVIS (Omega)
"""

from Desktop_Assistant import imports as I

os_key = I.os_key()

if os_key == "macintosh":
    from .speaker_mac import speak
elif os_key == "windows":
    from .speaker_windows import speak
else:
    from .speaker_linux import speak
