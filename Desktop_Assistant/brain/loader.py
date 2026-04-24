"""
loader.py — Function-based command loader for JARVIS (Omega)

Loads commands from:
- Desktop_Assistant.commands.non_os_specific
- Desktop_Assistant.commands.os_specific.<os_key>

Each command module may define:
- get_metadata() -> dict (preferred)
- or a callable entrypoint: run(), execute(), or main()
- Optional: ALIASES = ["alias1", "alias2"]

Command name is derived from metadata 'name' if present, otherwise the filename.

This loader is resilient: if a command module fails to import at boot,
we register a lightweight FailedCommand placeholder so boot continues
quietly and the user receives a friendly error only when they try the
broken command.
"""

from __future__ import annotations

import importlib
import pkgutil
import logging
from pathlib import Path
from typing import Any, Dict, Tuple, Optional

logger = logging.getLogger("jarvis.loader")

# Local package base
BASE_PKG = "Desktop_Assistant.commands"


class CommandLoader:
    def __init__(self, os_key: str) -> None:
        self.os_key = (os_key or "").lower().strip()

        # Resolve package path for commands
        # Desktop_Assistant/commands
        self.base_path = Path(__file__).resolve().parents[1] / "commands"

    # -------------------------
    # Public API
    # -------------------------
    def load_all(self) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Load commands from:
          - commands/non_os_specific
          - commands/os_specific/<os_key>
        OS-specific commands override general ones.
        Returns:
          (commands, alias_map)
            commands: dict[name -> CommandAdapter or fallback wrapper]
            alias_map: dict[alias -> name]
        """
        commands: Dict[str, Any] = {}
        alias_map: Dict[str, str] = {}

        # Load general commands first
        general_pkg = f"{BASE_PKG}.non_os_specific"
        self._load_from_package(general_pkg, commands, alias_map)

        # Then load OS-specific commands (override)
        if self.os_key:
            os_pkg = f"{BASE_PKG}.os_specific.{self.os_key}"
            self._load_from_package(os_pkg, commands, alias_map)

        return commands, alias_map

    # -------------------------
    # Internal helpers
    # -------------------------
    def _load_from_package(
        self,
        package_name: str,
        commands: Dict[str, Any],
        aliases: Dict[str, str],
    ) -> None:
        """
        Import a package and iterate its modules, registering commands.
        If a module fails to import, register a FailedCommand placeholder
        so boot remains quiet and the user sees a friendly error when they
        attempt to run the broken command.
        """
        try:
            package = importlib.import_module(package_name)
        except ModuleNotFoundError:
            logger.debug("Command package not found: %s", package_name)
            return
        except Exception as exc:
            logger.exception("Failed to import package %s: %s", package_name, exc)
            return

        if not hasattr(package, "__path__"):
            logger.debug("Package has no __path__: %s", package_name)
            return

        for module_info in pkgutil.iter_modules(package.__path__):
            if module_info.ispkg:
                continue

            module_name = module_info.name
            full_name = f"{package_name}.{module_name}"

            # Try to import the module; on failure register a placeholder
            try:
                module = importlib.import_module(full_name)
            except Exception as exc:
                logger.debug("Failed to import command module %s: %s", full_name, exc)
                failed_meta = {
                    "name": module_name.lower(),
                    "aliases": [],
                    "category": "broken",
                    "error": str(exc),
                }
                # Try to use a centralized FailedCommand helper if available
                try:
                    from Desktop_Assistant.brain.engine.failed_command import FailedCommand  # type: ignore

                    commands[module_name.lower()] = FailedCommand(full_name, failed_meta)
                except Exception:
                    # Fallback minimal placeholder
                    logger.debug("FailedCommand helper unavailable; using inline placeholder for %s", full_name)

                    def _placeholder(brain, text, _e=str(exc), _m=module_name):
                        return {
                            "success": False,
                            "message": f"Command '{_m}' failed to load: {_e}",
                            "data": {"loaded": False, "error": str(_e)},
                        }

                    commands[module_name.lower()] = {
                        "callable": _placeholder,
                        "name": module_name.lower(),
                        "metadata": failed_meta,
                    }
                # continue to next module
                continue

            # Prefer explicit metadata if present
            meta = self._get_metadata_safe(module)
            cmd_name: Optional[str] = None
            entry_callable = None

            if meta:
                # metadata may provide canonical name and aliases and os_support
                cmd_name = (meta.get("name") or module_name).strip().lower()
                os_support = meta.get("os_support", [])
                # If package is OS-specific, ensure the module supports this OS (if metadata present)
                if package_name.endswith(self.os_key) and os_support and self.os_key not in [o.lower() for o in os_support]:
                    logger.debug("Skipping %s: metadata restricts OS support", full_name)
                    continue
                # If metadata explicitly names an entry (callable or attribute name), resolve it
                entry = meta.get("entry")
                if callable(entry):
                    entry_callable = entry
                elif isinstance(entry, str) and hasattr(module, entry):
                    entry_callable = getattr(module, entry)
                # otherwise we'll fall back to run/execute/main below

            # No metadata or no explicit entry: look for a callable entrypoint
            if not entry_callable:
                entry_callable = getattr(module, "run", None) or getattr(module, "execute", None) or getattr(module, "main", None)

            # If we have a callable entrypoint, wrap it; otherwise skip
            if callable(entry_callable):
                # Use provided name or fallback to filename
                if not cmd_name:
                    cmd_name = module_name.lower()
                # Normalize name
                cmd_name = cmd_name.strip().lower()
                # Wrap with CommandAdapter if available, passing metadata
                adapter = self._make_adapter(module, entry_callable, cmd_name, meta)
                commands[cmd_name] = adapter

                # Register aliases from metadata or module-level ALIASES
                module_aliases = []
                if meta:
                    module_aliases = meta.get("aliases", []) or []
                else:
                    module_aliases = getattr(module, "ALIASES", []) or []

                if isinstance(module_aliases, (list, tuple)):
                    for alias in module_aliases:
                        if isinstance(alias, str) and alias.strip():
                            alias_key = alias.strip().lower()
                            # Avoid overwriting an existing alias mapping unless it's the same command
                            if alias_key in aliases and aliases[alias_key] != cmd_name:
                                logger.warning(
                                    "Alias collision: %s already maps to %s; skipping alias %s for %s",
                                    alias_key,
                                    aliases[alias_key],
                                    alias_key,
                                    cmd_name,
                                )
                                continue
                            aliases[alias_key] = cmd_name
            else:
                logger.debug("Module %s has no callable entrypoint or metadata; skipping", full_name)

    def _get_metadata_safe(self, module) -> Optional[dict]:
        """
        Call module.get_metadata() if present and return a dict, otherwise None.
        Protects against exceptions in user modules.
        """
        try:
            getter = getattr(module, "get_metadata", None)
            if callable(getter):
                meta = getter()
                if isinstance(meta, dict):
                    return meta
        except Exception:
            logger.exception("get_metadata() failed for module %s", getattr(module, "__name__", "<unknown>"))
        return None

    def _make_adapter(self, module, entry_callable, cmd_name: str, metadata: Optional[dict] = None):
        """
        Create a CommandAdapter if available, passing metadata when possible.
        Falls back to a simple wrapper if the adapter import fails.
        """
        try:
            # Lazy import to avoid circular imports at module import time
            from Desktop_Assistant.brain.engine.command_adapter import CommandAdapter  # type: ignore

            # Pass metadata dict to adapter so it can expose aliases, timeout, disabled, etc.
            return CommandAdapter(entry_callable, cmd_name, metadata=metadata or {})
        except Exception:
            # Fallback: return a simple dict-like wrapper
            logger.debug("CommandAdapter unavailable; using fallback wrapper for %s", cmd_name)
            return {"callable": entry_callable, "name": cmd_name, "metadata": metadata or {}}
