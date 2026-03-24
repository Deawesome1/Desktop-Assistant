"""
bot/listener.py — JARVIS speech recognition module.

Tuning guide (edit config/voice.json under "listener"):
  energy_threshold:     How loud audio must be to count as speech.
                        Lower  = more sensitive (picks up quiet speech, more false triggers)
                        Higher = less sensitive (misses quiet speech, fewer false triggers)
                        Default 300. Try 200 if it misses you, 400 if it triggers on noise.
  dynamic_energy:       true = auto-adjusts threshold over time. Recommended.
  pause_threshold:      Seconds of silence that marks end of phrase. Default 0.8.
                        Increase if it cuts you off mid-sentence.
  phrase_limit:         Max seconds to listen once speech starts. Default 10.
  timeout:              Seconds to wait for speech to begin. Default 8.
  ambient_duration:     Seconds to calibrate for background noise each call. Default 0.3.
  retry_on_unknown:     true = if speech was heard but not understood, listen once more.
"""

import os
import json

CONFIG_PATH   = os.path.join(os.path.dirname(__file__), "..", "config", "keywords.json")
VOICE_CONFIG  = os.path.join(os.path.dirname(__file__), "..", "config", "voice.json")

_recognizer = None


def _load_keywords() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def _load_listener_config() -> dict:
    defaults = {
        "energy_threshold":  300,
        "dynamic_energy":    True,
        "pause_threshold":   0.8,
        "phrase_limit":      10,
        "timeout":           8,
        "ambient_duration":  0.3,
        "retry_on_unknown":  True,
        "language":          "en-US",
    }
    try:
        with open(VOICE_CONFIG, "r") as f:
            data = json.load(f)
        defaults.update(data.get("listener", {}))
    except Exception:
        pass
    return defaults


def _get_recognizer():
    global _recognizer
    cfg = _load_listener_config()
    if _recognizer is None:
        import speech_recognition as sr
        _recognizer = sr.Recognizer()
    _recognizer.energy_threshold         = cfg["energy_threshold"]
    _recognizer.dynamic_energy_threshold = cfg["dynamic_energy"]
    _recognizer.pause_threshold          = cfg["pause_threshold"]
    return _recognizer


def _build_phrase_hints() -> list[str]:
    """
    Feed known JARVIS vocabulary to the Google Speech API so it biases
    recognition toward wake words, cancel words, and command triggers.
    """
    hints = []
    try:
        kw = _load_keywords()
        hints += kw.get("wake_words",   [])
        hints += kw.get("cancel_words", [])
    except Exception:
        pass
    try:
        registry_path = os.path.join(os.path.dirname(__file__), "..", "config", "commands.json")
        with open(registry_path) as f:
            registry = json.load(f)
        for entry in registry.get("commands", {}).values():
            hints += entry.get("triggers", [])
    except Exception:
        pass
    seen, clean = set(), []
    for h in hints:
        h = h.strip()
        if h and h not in seen:
            seen.add(h)
            clean.append(h)
    return clean[:500]


def _load_triggers() -> list[str]:
    """Load all known command triggers + wake words for scoring."""
    triggers = []
    try:
        kw = _load_keywords()
        triggers += kw.get("wake_words",   [])
        triggers += kw.get("cancel_words", [])
    except Exception:
        pass
    try:
        registry_path = os.path.join(os.path.dirname(__file__), "..", "config", "commands.json")
        with open(registry_path) as f:
            registry = json.load(f)
        for entry in registry.get("commands", {}).values():
            triggers += entry.get("triggers", [])
    except Exception:
        pass
    return [t.lower().strip() for t in triggers if t.strip()]


# Wake words to strip before command scoring so "jarvis" alone
# doesn't give noise transcripts a free cmd=1.0
_WAKE_WORDS_FOR_SCORING = {"jarvis", "hey jarvis", "jarvis please",
                            "ok jarvis", "okay jarvis"}


def _strip_wake_word(text: str) -> str:
    """Remove wake word prefix from transcript before command scoring."""
    t = text.lower().strip()
    for w in sorted(_WAKE_WORDS_FOR_SCORING, key=len, reverse=True):
        if t.startswith(w):
            t = t[len(w):].strip()
            break
    return t


def _command_match_score(text: str, triggers: list[str]) -> float:
    """
    Score how well a transcript matches known command vocabulary.
    Returns a value between 0.0 and 1.0.

    Wake words are stripped first so "jarvis presley" doesn't score
    1.0 just because "jarvis" is a registered wake-word trigger.

    Scoring (applied to the post-wake-word text):
      - Exact trigger match anywhere in text:       1.0
      - All trigger words present in text:          0.8
      - Partial word overlap with any trigger:      proportional (max 0.7)
      - Fuzzy per-word similarity:                  up to 0.9
      - No match:                                   0.0
    """
    from difflib import SequenceMatcher

    # Score both raw and wake-stripped; take the higher
    # (preserves cases where wake word IS the command, e.g. "jarvis")
    raw        = text.lower().strip()
    stripped   = _strip_wake_word(raw)

    def _score(t: str, skip_wake: bool = False) -> float:
        t_words = t.split()
        t_set   = set(t_words)
        best    = 0.0
        for trigger in triggers:
            trig_lower = trigger.lower().strip()
            trig_words = set(trig_lower.split())
            # Skip bare wake-word triggers unless the text IS just the wake word
            # This prevents "jarvis presley" scoring 1.0 from "jarvis" alone
            if skip_wake and trig_lower in _WAKE_WORDS_FOR_SCORING:
                continue
            if trig_lower in t:
                # Only count as 1.0 if it's more than just the wake word prefix
                # i.e. there must be a non-wake-word match
                if trig_lower in _WAKE_WORDS_FOR_SCORING and len(t_words) > 1:
                    # Give credit but not full 1.0 — the wake word is expected
                    best = max(best, 0.5)
                    continue
                return 1.0
            if trig_words and trig_words.issubset(t_set):
                best = max(best, 0.8)
                continue
            if trig_words:
                overlap = len(trig_words & t_set) / len(trig_words)
                best = max(best, overlap * 0.7)
            for tw in t_words:
                for trigw in trig_lower.split():
                    # Require both words to be >= 4 chars and sim > 0.75
                    # to avoid short words like "for" fuzzy-matching gibberish
                    if len(tw) < 4 or len(trigw) < 4:
                        continue
                    sim = SequenceMatcher(None, tw, trigw).ratio()
                    if sim > 0.75:
                        best = max(best, sim * 0.9)
        return best

    raw_score      = _score(raw, skip_wake=False)
    stripped_score = _score(stripped, skip_wake=True) if stripped != raw else raw_score
    return max(raw_score, stripped_score)


def _score_candidates(candidates: list[dict]) -> str:
    """
    Score all STT candidates on two axes:
      1. Google speech confidence (0.0 - 1.0)
      2. Command match score     (0.0 - 1.0)

    Final score = (speech_confidence * 0.4) + (command_match * 0.6)

    Command relevance is weighted higher than raw speech confidence
    so that a lower-confidence but on-vocabulary transcript beats a
    high-confidence transcript that matches nothing JARVIS knows.

    Prints a ranked table so you can see exactly how each candidate scored.
    """
    triggers = _load_triggers()

    scored = []
    for i, c in enumerate(candidates):
        transcript = c.get("transcript", "").lower().strip()
        if not transcript:
            continue

        # Google only provides confidence for alternatives[1+], not [0].
        # Assign a generous default to the first result so it isn't penalised.
        if "confidence" in c:
            stt_conf = float(c["confidence"])
        else:
            stt_conf = 0.85 if i == 0 else 0.5

        cmd_score = _command_match_score(transcript, triggers)
        final     = (stt_conf * 0.4) + (cmd_score * 0.6)
        scored.append((final, stt_conf, cmd_score, transcript))

    if not scored:
        return ""

    scored.sort(reverse=True)

    # If the top candidate has zero command score but a lower-ranked candidate
    # has a meaningful command match, prefer the command-matching one.
    # Prevents high-confidence noise ("jarvis presley") beating an actual
    # command attempt ("jarvis press play") on speech confidence alone.
    best = scored[0]
    if best[2] == 0.0:
        for candidate in scored[1:]:
            final, stt, cmd, text = candidate
            if cmd >= 0.3 and (best[0] - final) < 0.25:
                best = candidate
                break

    # Print ranked table
    print(f"[Listener] Scored {len(scored)} candidate(s):")
    for i, (final, stt, cmd, text) in enumerate(scored):
        marker = "  <-- selected" if (final, stt, cmd, text) == best else ""
        print(f"           [{i+1}] stt={stt:.2f} cmd={cmd:.2f} final={final:.2f}  '{text}'{marker}")

    return best[3]


def listen_once(prompt: str = "", timeout: int = None,
                phrase_limit: int = None) -> str | None:
    """
    Capture a single spoken utterance and return it as lowercase text.
    Returns None if nothing was heard or recognition failed.
    """
    try:
        import speech_recognition as sr
    except ImportError:
        print("[Listener] SpeechRecognition not installed — falling back to text input.")
        return _text_fallback(prompt)

    cfg          = _load_listener_config()
    timeout      = timeout      if timeout      is not None else cfg["timeout"]
    phrase_limit = phrase_limit if phrase_limit is not None else cfg["phrase_limit"]
    recognizer   = _get_recognizer()
    hints        = _build_phrase_hints()
    language     = cfg.get("language", "en-US")
    retry        = cfg.get("retry_on_unknown", True)

    def _attempt() -> str | None:
        try:
            with sr.Microphone() as source:
                if prompt:
                    print(prompt)
                recognizer.adjust_for_ambient_noise(
                    source, duration=cfg["ambient_duration"]
                )
                print("[Listener] Ready.")
                try:
                    audio = recognizer.listen(
                        source,
                        timeout=timeout,
                        phrase_time_limit=phrase_limit
                    )
                except sr.WaitTimeoutError:
                    print("[Listener] Timeout — no speech detected.")
                    return None

            try:
                all_results = recognizer.recognize_google(
                    audio,
                    language=language,
                    show_all=True,
                )
                if not all_results or "alternative" not in all_results:
                    return "UNKNOWN"

                candidates = all_results["alternative"]
                best = _score_candidates(candidates)
                print(f"[Listener] Heard: '{best}'")
                return best

            except sr.UnknownValueError:
                return "UNKNOWN"
            except sr.RequestError as e:
                print(f"[Listener] Google Speech API error: {e}")
                return None

        except OSError as e:
            print(f"[Listener] Microphone error: {e}")
            return _text_fallback(prompt)
        except Exception as e:
            print(f"[Listener] Unexpected error: {type(e).__name__}: {e}")
            return None

    result = _attempt()

    if result == "UNKNOWN":
        if retry:
            # Mishear humor
            try:
                from bot.personality.engine import get_situational
                line = get_situational("mishear")
                if line:
                    from bot.speaker import speak
                    speak(line)
            except Exception:
                pass
            print("[Listener] Didn't catch that — listening again...")
            result = _attempt()
        if result == "UNKNOWN":
            print("[Listener] Could not understand audio.")
            return None

    return result


def _text_fallback(prompt: str) -> str | None:
    try:
        result = input(f"{prompt or '[Type command]'} >> ").lower().strip()
        return result or None
    except (EOFError, KeyboardInterrupt):
        return None


def contains_wake_word(text: str) -> bool:
    if not text:
        return False
    return any(w.lower() in text.lower() for w in _load_keywords().get("wake_words", ["jarvis"]))


def is_cancel(text: str) -> bool:
    if not text:
        return False
    return any(w.lower() in text.lower() for w in _load_keywords().get("cancel_words", ["cancel"]))