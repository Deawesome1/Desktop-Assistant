from pathlib import Path
import json
import logging

logger = logging.getLogger("jarvis.config_utils")
ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def config_path(name: str) -> Path:
    return CONFIG_DIR / name

def read_config(name: str, default=None):
    p = config_path(name)
    if not p.exists():
        return default
    try:
        with p.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        logger.exception("Failed to read config %s", p)
        return default

def write_config(name: str, data):
    p = config_path(name)
    try:
        with p.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
    except Exception:
        logger.exception("Failed to write config %s", p)
