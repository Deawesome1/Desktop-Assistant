"""
loader.py — Function-based command loader for JARVIS (Omega)

Loads commands from:
- Desktop_Assistant.commands.non_os_specific
- Desktop_Assistant.commands.os_specific.<os_key>

Each command file may define:
- run()          ← preferred
- execute()
- main()
- ALIASES = ["alias1", "alias2"]  ← optional

Command name is derived from the filename (e.g., greet.py → "greet").
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Any, Dict, Tuple

from Desktop_Assistant import commands


class CommandLoader:
    def __init__(self, os_key: str) -> None:
        self.os_key = os_key.lower()

        # Root of project: .../Desktop-Assistant/
        self.project_root = Path(__file__).resolve().parents[2]

        # Python package base
        self.base_pkg = "Desktop_Assistant.commands"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_all(self) -> Tuple[Dict[str, Any], Dict[str, str]]:
        commands: Dict[str, Any] = {}
        aliases: Dict[str, str] = {}

        # Load non-OS-specific commands
        self._load_from_package(
            f"{self.base_pkg}.non_os_specific",
            commands,
            aliases,
        )

        # Load OS-specific commands
        self._load_from_package(
            f"{self.base_pkg}.os_specific.{self.os_key}",
            commands,
            aliases,
        )

        return commands, aliases

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_from_package(
        self,
        package_name: str,
        commands: Dict[str, Any],
        aliases: Dict[str, str],
    ) -> None:

        try:
            package = importlib.import_module(package_name)
        except ModuleNotFoundError:
            return

        if not hasattr(package, "__path__"):
            return

        for module_info in pkgutil.iter_modules(package.__path__):
            if module_info.ispkg:
                continue

            module_name = module_info.name
            full_name = f"{package_name}.{module_name}"

            try:
                module = importlib.import_module(full_name)
            except Exception:
                continue

            # Look for a callable entry point
            entry = (
                getattr(module, "run", None)
                or getattr(module, "execute", None)
                or getattr(module, "main", None)
            )

            if not callable(entry):
                continue

            # Command name = filename
            cmd_name = module_name.lower()
            from Desktop_Assistant.brain.engine.command_adapter import CommandAdapter
            commands[cmd_name] = CommandAdapter(entry, cmd_name)


            # Optional aliases
            module_aliases = getattr(module, "ALIASES", [])
            if isinstance(module_aliases, (list, tuple)):
                for alias in module_aliases:
                    if isinstance(alias, str) and alias.strip():
                        aliases[alias.strip().lower()] = cmd_name
