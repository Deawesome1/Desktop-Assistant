class FakeListenerModule:
    def listen_once(self, *args, **kwargs):
        print("[FAKE LISTENER] listen_once() called")
        return "test"

fake_listener_module = FakeListenerModule()
