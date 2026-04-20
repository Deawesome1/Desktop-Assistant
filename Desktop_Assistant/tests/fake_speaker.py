# tests/fake_speaker.py

class _FakeSpeakerModule:
    def speak(self, text: str):
        print(f"[FAKE SPEAKER] {text}")

# Expose as a module-like object
fake_speaker_module = _FakeSpeakerModule()
