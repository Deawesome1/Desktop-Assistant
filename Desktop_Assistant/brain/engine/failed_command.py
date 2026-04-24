# Desktop_Assistant/brain/engine/failed_command.py
import logging
from typing import Dict, Any

logger = logging.getLogger("jarvis.failed_command")

class FailedCommand:
    """
    Lightweight placeholder for a command module that failed to import.
    When invoked, returns a friendly failure dict and logs the original import error.
    """
    def __init__(self, module_path: str, metadata: Dict[str, Any]):
        self.module_path = module_path
        self._meta = metadata or {}
        self.name = self._meta.get("name", module_path.split(".")[-1])
        self.metadata = self._meta

    def get_metadata(self) -> Dict[str, Any]:
        return dict(self._meta)

    def invoke(self, brain, user_text: str) -> Dict[str, Any]:
        # Log once per invocation so the user sees the cause but boot stays quiet
        logger.warning("Attempted to run broken command %s (module: %s). Error: %s", self.name, self.module_path, self._meta.get("error"))
        return {
            "success": False,
            "message": f"Command '{self.name}' is unavailable (failed to load).",
            "data": {"loaded": False, "error": self._meta.get("error")},
        }
