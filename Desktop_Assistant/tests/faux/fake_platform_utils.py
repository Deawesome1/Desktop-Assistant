from ...platform_utils import clear_clipboard, get_desktop

@staticmethod
def clear_clipboard():
    print("[FAKE PLATFORM] clear_clipboard()")

@staticmethod
def get_desktop():
    return "C:/Users/FakeUser/Desktop"
