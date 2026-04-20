# boot/python_checker.py

import sys

MIN_PY = (3, 9)
MAX_PY = (3, 11)


def _version_tuple():
    return sys.version_info[:2]


def verify_python_range():
    major, minor = _version_tuple()
    print(f"Detected caller Python: {major}.{minor}")

    if (major, minor) < MIN_PY:
        print(f"❌ Python {MIN_PY[0]}.{MIN_PY[1]}+ is required.")
        raise SystemExit(1)

    if (major, minor) > MAX_PY:
        print(f"⚠ Python {major}.{minor} is newer than supported max {MAX_PY[0]}.{MAX_PY[1]}.")
        print("Continuing, but a compatible interpreter will be searched for.")
    else:
        print("✓ Caller Python is within supported range.")
