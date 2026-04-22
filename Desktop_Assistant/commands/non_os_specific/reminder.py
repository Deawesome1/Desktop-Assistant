"""
commands/reminder.py — Set a time-based reminder with a spoken message.
Triggers: "remind me at X to Y", "remind me in X minutes to Y", "set a reminder"
Reminders persist to config/reminders.json and are restored on startup.
"""

from Desktop_Assistant import imports as I
import os
import json
import threading
import time
from datetime import datetime, timedelta

REMINDERS_FILE = os.path.join(
    os.path.dirname(__file__), "..", "config", "reminders.json"
)


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _load_reminders() -> list:
    if not os.path.exists(REMINDERS_FILE):
        return []
    try:
        with open(REMINDERS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save_reminders(reminders: list):
    os.makedirs(os.path.dirname(REMINDERS_FILE), exist_ok=True)
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f, indent=2)


# ---------------------------------------------------------------------------
# Time parsing
# ---------------------------------------------------------------------------

def _parse_absolute_time(text: str) -> datetime | None:
    """Parse time expressions like '3pm', '3:30 pm', '5:00 p.m.'"""
    re = I.re
    now = datetime.now()

    # Normalize p.m./a.m. → pm/am
    text = re.sub(r"p\.m\.", "pm", text, flags=re.IGNORECASE)
    text = re.sub(r"a\.m\.", "am", text, flags=re.IGNORECASE)

    patterns = [
        (r"(\d{1,2}):(\d{2})\s*(am|pm)",
         lambda m: datetime.strptime(f"{m.group(1)}:{m.group(2)} {m.group(3).upper()}", "%I:%M %p")),
        (r"(\d{1,2})\s*(am|pm)",
         lambda m: datetime.strptime(f"{m.group(1)} {m.group(2).upper()}", "%I %p")),
        (r"(\d{2}):(\d{2})",
         lambda m: datetime.strptime(f"{m.group(1)}:{m.group(2)}", "%H:%M")),
    ]

    for pattern, parser in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                t = parser(m)
                target = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
                if target <= now:
                    target += timedelta(days=1)
                return target
            except Exception:
                continue
    return None


def _parse_delta(text: str) -> int:
    """Parse relative time like 'in 5 minutes 30 seconds'. Returns total seconds."""
    re = I.re
    seconds = 0
    for pattern, mult in [
        (r"(\d+)\s*hour", 3600),
        (r"(\d+)\s*minute", 60),
        (r"(\d+)\s*second", 1),
    ]:
        m = re.search(pattern, text)
        if m:
            seconds += int(m.group(1)) * mult
    return seconds


def _extract_message(text: str) -> str:
    """Extract the reminder message after 'to', 'that', or 'about'."""
    for sep in [" to ", " that ", " about "]:
        if sep in text:
            return text.split(sep, 1)[-1].strip(" .,")
    return ""


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------

def _schedule(fire_at: datetime, message: str):
    def _fire():
        delay = (fire_at - datetime.now()).total_seconds()
        if delay > 0:
            time.sleep(delay)
        I.speak(f"Reminder: {message}")

    threading.Thread(target=_fire, daemon=True).start()


# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------

def run(query: str) -> str:
    re = I.re
    q = query.lower().strip()

    # Detect incomplete queries
    trigger_only = all(w in ["remind", "me", "set", "a", "reminder", "for", "an"]
                       for w in q.split())
    has_time = _parse_absolute_time(q) is not None or _parse_delta(q) > 0

    combined = q

    if trigger_only or not has_time:
        I.speak("When and what should I remind you about?")
        follow_up = I.listen_once(timeout=10)
        if follow_up:
            combined = q + " " + follow_up.lower()

    # Parse time
    fire_at = _parse_absolute_time(combined)
    if fire_at is None:
        delta = _parse_delta(combined)
        if delta > 0:
            fire_at = datetime.now() + timedelta(seconds=delta)

    if fire_at is None:
        I.speak("I didn't catch a time. Try: remind me in 10 minutes to drink water.")
        return "Failed: no time parsed"

    # Parse message
    message = _extract_message(combined)
    if not message:
        I.speak("What should I remind you about?")
        heard = I.listen_once(timeout=8)
        message = heard.strip() if heard else "something"

    # Schedule reminder
    _schedule(fire_at, message)

    # Persist
    reminders = _load_reminders()
    reminders.append({"fire_at": fire_at.isoformat(), "message": message})
    _save_reminders(reminders)

    # Respond
    time_str = fire_at.strftime("%I:%M %p").lstrip("0")
    response = f"Reminder set for {time_str}: {message}."
    I.speak(response)
    return response


# ---------------------------------------------------------------------------
# Restore on startup
# ---------------------------------------------------------------------------

def restore_pending():
    """Reschedule reminders that survived a restart."""
    reminders = _load_reminders()
    now = datetime.now()
    active = []

    for r in reminders:
        try:
            fire_at = datetime.fromisoformat(r["fire_at"])
            if fire_at > now:
                _schedule(fire_at, r["message"])
                active.append(r)
        except Exception:
            pass

    _save_reminders(active)
