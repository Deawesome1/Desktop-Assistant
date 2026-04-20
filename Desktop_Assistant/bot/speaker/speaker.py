from commands.os_scanner import current_os

if current_os == "windows":
    from .speaker_windows import speak
elif current_os == "macintosh":
    from .speaker_mac import speak
else:
    from .speaker_linux import speak
