class FakeCtx:
    def push(self, *args, **kwargs):
        print("[FAKE CTX] push:", args, kwargs)

    def pop(self, *args, **kwargs):
        print("[FAKE CTX] pop:", args, kwargs)

    def get_open_apps(self):
        return ["FakeApp.exe"]

fake_ctx = FakeCtx()
