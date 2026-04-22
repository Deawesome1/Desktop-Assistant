class FakePlatformUtils:
    @staticmethod
    def get_os_key():
        return "windows"

    @staticmethod
    def get_clipboard():
        return "fake clipboard text"

    @staticmethod
    def get_desktop():
        return "C:/Users/FakeUser/Desktop"

fake_jarvis = type("FakeJarvisPackage", (), {
    "platform_utils": FakePlatformUtils
})
