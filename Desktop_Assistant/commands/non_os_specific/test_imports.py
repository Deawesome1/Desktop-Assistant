"""
test_imports.py — Diagnostic command
Verifies that the new imports.py surface works correctly.
"""

from Desktop_Assistant import imports as I

COMMAND_NAME = "test_imports"
COMMAND_ALIASES = ["testimports"]
COMMAND_DESCRIPTION = "Tests the import surface."
COMMAND_OS_SUPPORT = ["windows", "macintosh", "linux"]
COMMAND_CATEGORY = "diagnostic"
COMMAND_REQUIRES_INTERNET = False
COMMAND_REQUIRES_ADMIN = False


def get_metadata():
    return {
        "name": COMMAND_NAME,
        "aliases": COMMAND_ALIASES,
        "description": COMMAND_DESCRIPTION,
        "os_support": COMMAND_OS_SUPPORT,
        "category": COMMAND_CATEGORY,
        "requires_internet": COMMAND_REQUIRES_INTERNET,
        "requires_admin": COMMAND_REQUIRES_ADMIN,
    }


def is_supported_on_os(os_key: str) -> bool:
    return os_key in COMMAND_OS_SUPPORT


def run(brain, user_text, args=None, context=None):
    """
    This command doesn't DO anything — it just verifies that the import
    surface is working and returns a structured report.
    """

    report = {}

    # Test Brain class
    try:
        Brain = I.Brain
        report["Brain"] = f"OK ({Brain})"
    except Exception as e:
        report["Brain"] = f"FAIL ({e})"

    # Test speaker
    try:
        speak = I.speak
        report["speak"] = f"OK ({speak})"
    except Exception as e:
        report["speak"] = f"FAIL ({e})"

    # Test listener
    try:
        listen = I.listen
        report["listen"] = f"OK ({listen})"
    except Exception as e:
        report["listen"] = f"FAIL ({e})"

    # Test OS key
    try:
        os_key = I.os_key
        report["os_key"] = f"OK ({os_key})"
    except Exception as e:
        report["os_key"] = f"FAIL ({e})"

    # Test CommandHub
    try:
        CommandHub = I.CommandHub
        report["CommandHub"] = f"OK ({CommandHub})"
    except Exception as e:
        report["CommandHub"] = f"FAIL ({e})"

    # Test CommandLoader
    try:
        loader = I.CommandLoader
        report["CommandLoader"] = f"OK ({loader})"
    except Exception as e:
        report["CommandLoader"] = f"FAIL ({e})"

    # Test standard libs
    try:
        _ = I.re
        _ = I.json
        _ = I.urllib
        report["stdlib"] = "OK"
    except Exception as e:
        report["stdlib"] = f"FAIL ({e})"

    return {
        "success": True,
        "message": "Import surface test complete.",
        "data": report,
    }
