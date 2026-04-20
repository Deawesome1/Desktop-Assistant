class FakeEvent:
    def __call__(self, *args, **kwargs):
        print("[FAKE EVENT] called:", args, kwargs)

class FakeContext:
    def __init__(self):
        self.os_key = "windows"

    def get_current_os_key(self):
        return self.os_key

    def get_open_apps(self):
        return ["FakeApp.exe"]

class FakeBrain:
    def __init__(self):
        self.context = FakeContext()
        self.event = FakeEvent()

    def get_current_os_key(self):
        return self.context.get_current_os_key()

    def lower(self):
        return "fakebrain"

    def remember(self, *args, **kwargs):
        print("[FAKE BRAIN] remember:", args, kwargs)
