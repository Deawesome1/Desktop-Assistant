# brain/engine/context_engine.py

from typing import Any, Dict


class ContextEngine:
    def __init__(self, brain: "Brain") -> None:
        self.brain = brain

    def get_context(self):
        return dict(self.brain.conversation_state)

    def set_current_topic(self, topic):
        self.brain.conversation_state["current_topic"] = topic

    def set_current_project(self, project):
        self.brain.conversation_state["current_project"] = project

    def set_last_command(self, name):
        self.brain.conversation_state["last_command"] = name

    def add_touched_file(self, path):
        files = self.brain.conversation_state.setdefault("last_files_touched", [])
        if path not in files:
            files.append(path)
