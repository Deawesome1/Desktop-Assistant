import sys
from pathlib import Path
import unittest

# ---------------------------------------------------------
# FIX: Ensure project root is on sys.path
# ---------------------------------------------------------
# This file lives in Desktop_Assistant/tests/... so:
# parents[0] = tests/
# parents[1] = Desktop_Assistant/
# parents[2] = Desktop-Assistant (project root)
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------
# Correct imports for your real structure
# ---------------------------------------------------------
from Desktop_Assistant.brain.loader import CommandLoader
from Desktop_Assistant.brain.engine.brain import Brain


class TestLoadCommands(unittest.TestCase):

    def test_loader_discovers_commands(self):
        """Ensure the loader finds commands for the current OS."""

        brain = Brain()
        os_key = brain.get_current_os_key()

        loader = CommandLoader(os_key)
        commands, aliases = loader.load_all()

        print("\n=== COMMAND DISCOVERY REPORT ===")
        print(f"OS Key: {os_key}")
        print(f"Commands Loaded: {len(commands)}")
        print(f"Aliases Loaded: {len(aliases)}")

        for name, module in commands.items():
            print(f" - {name}: {module}")

        # Hard fail if nothing loads
        self.assertGreater(
            len(commands),
            0,
            f"No commands loaded for OS '{os_key}'. "
            f"Check your folder structure and loader paths."
        )


if __name__ == "__main__":
    unittest.main()
