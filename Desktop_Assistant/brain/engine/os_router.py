# brain/engine/os_router.py

import platform
from typing import Any, Dict


class OSRouter:
    def __init__(self, brain: "Brain") -> None:
        self.brain = brain

    def get_os_mapping(self) -> Dict[str, str]:
        return self.brain.os_routing_cfg.get("mapping", {})

    def get_current_os_key(self) -> str:
        sys_name = platform.system().lower()
        mapping = self.get_os_mapping()
        return mapping.get(sys_name, sys_name)
