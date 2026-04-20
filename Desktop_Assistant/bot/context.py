"""
context.py — Runtime context for the bot UI layer.

This is NOT the same as the Brain's context engine.
This file tracks session-level runtime state for the bot itself:
    - whether the bot is running
    - last user input/output
    - turn counters
    - session metadata
    - debug flags (optional)
"""

import time


class BotContext:
    def __init__(self, debug: bool = False):
        # Runtime flags
        self.running = True
        self.debug = debug

        # Session metadata
        self.session_start = time.time()
        self.turn_count = 0

        # Last interaction
        self.last_input = None
        self.last_output = None

        # Optional: store arbitrary session data
        self.session_data = {}

    # --------------------------------------------------------------
    # Update context after each turn
    # --------------------------------------------------------------
    def update(self, user_text: str, bot_text: str):
        self.last_input = user_text
        self.last_output = bot_text
        self.turn_count += 1

    # --------------------------------------------------------------
    # Helper: get session duration
    # --------------------------------------------------------------
    def session_duration(self) -> float:
        return time.time() - self.session_start

    # --------------------------------------------------------------
    # Helper: store arbitrary session-level data
    # --------------------------------------------------------------
    def set(self, key: str, value):
        self.session_data[key] = value

    def get(self, key: str, default=None):
        return self.session_data.get(key, default)
