from pathlib import Path
import importlib


class FakeEvent:
    def __call__(self, *args, **kwargs):
        print("[FAKE EVENT] called:", args, kwargs)


class FakeContext:
    def __init__(self):
        self.os_key = "windows"

    def get_current_os_key(self):
        return self.os_key


class FakeBrain:
    """
    Minimal Brain stub that mirrors the real Brain's public API
    AND loads real commands exactly like the real Brain.
    """

    def __init__(self):
        self.context = FakeContext()
        self.event = FakeEvent()

        self.commands = {}
        self.alias_map = {}

        self.load_commands()

    # ------------------------------------------------------------
    # Basic API
    # ------------------------------------------------------------

    def get_current_os_key(self):
        return self.context.get_current_os_key()

    def detect_intent(self, text):
        return "test_intent"

    def is_action_allowed(self, text, intent):
        return True

    def set_last_command(self, name):
        pass

    def remember(self, *args, **kwargs):
        print("[FAKE BRAIN] remember:", args, kwargs)

    # ------------------------------------------------------------
    # Command loader (guaranteed working)
    # ------------------------------------------------------------

    def load_commands(self, commands_package="commands"):
        # This resolves to: Desktop_Assistant/
        project_root = Path(__file__).resolve().parents[1]
        commands_root = project_root / commands_package

        os_key = self.get_current_os_key()

        # Load non_os_specific
        self._register_dir(
            commands_root / "non_os_specific",
            f"{commands_package}.non_os_specific",
            os_key,
        )

        # Load os_specific/<os>
        self._register_dir(
            commands_root / "os_specific" / os_key,
            f"{commands_package}.os_specific.{os_key}",
            os_key,
        )

    def _register_dir(self, directory, base_module, os_key):
        if not directory.exists():
            return

        for file in sorted(directory.glob("*.py")):
            if file.name.startswith("_"):
                continue

            module_name = f"{base_module}.{file.stem}"

            try:
                module = importlib.import_module(module_name)
            except Exception as e:
                print(f"[FakeBrain] Failed to import {module_name}: {e}")
                continue

            if not hasattr(module, "get_metadata") or not hasattr(module, "run"):
                continue

            meta = module.get_metadata()
            name = meta.get("name")
            if not name:
                continue

            key = name.lower().strip()
            self.commands[key] = module

            for alias in meta.get("aliases", []):
                if isinstance(alias, str):
                    self.alias_map[alias.lower().strip()] = key

    # ------------------------------------------------------------
    # Command lookup
    # ------------------------------------------------------------

    def find_command(self, user_text):
        text = user_text.lower().strip()

        if text in self.commands:
            return self.commands[text]

        for alias, key in self.alias_map.items():
            if alias in text:
                return self.commands.get(key)

        return None
