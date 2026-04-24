from Desktop_Assistant import imports as I

os_key = I.os_key()

if os_key == "macintosh":
    from .listener_mac import listen
elif os_key == "windows":
    from .listener_windows import listen
else:
    from .listener_linux import listen
