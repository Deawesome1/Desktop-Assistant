"""
dependency_manager.py — JARVIS dependency checker and installer.
Runs before anything else on startup. Checks all required packages,
shows versions, offers to install missing ones and update outdated ones.
"""

import sys
import subprocess
import importlib.metadata
import importlib.util
from typing import NamedTuple

# ── Dependency manifest ───────────────────────────────────────────────────────
# Format: (import_name, pip_name, minimum_version, required)
#   import_name:     what you'd write in `import X`
#   pip_name:        the pip install name
#   minimum_version: oldest acceptable version (None = any)
#   required:        if True, JARVIS cannot run without this

class Dep(NamedTuple):
    import_name:     str
    pip_name:        str
    min_version:     str | None
    required:        bool
    description:     str

import sys as _sys
_WIN = _sys.platform == "win32"
_MAC = _sys.platform == "darwin"

DEPENDENCIES: list[Dep] = [
    # ── Core (all platforms) ──────────────────────────────────────────────────
    Dep("speech_recognition", "SpeechRecognition", "3.10.0", True,  "Voice input / wake word detection"),
    Dep("pyaudio",            "PyAudio",           "0.2.13", True,  "Microphone access"),
    Dep("pyttsx3",            "pyttsx3",           "2.90",   True,  "Text-to-speech output"),
    Dep("psutil",             "psutil",            "5.9.0",  False, "System info (CPU, RAM, disk, uptime)"),
    Dep("PIL",                "Pillow",            "10.0.0", False, "Screenshots"),
    Dep("pyautogui",          "pyautogui",         "0.9.54", False, "Media key control"),
    Dep("wikipediaapi",       "wikipedia-api",     "0.6.0",  False, "Wikipedia lookups"),
    Dep("difflib",            None,                None,     True,  "Fuzzy matching (stdlib)"),
    # ── Windows only ─────────────────────────────────────────────────────────
    *([
        Dep("pycaw",    "pycaw",    None, False, "Precise volume control (Windows)"),
        Dep("comtypes", "comtypes", None, False, "Windows COM — required by pycaw"),
        Dep("winreg",   None,       None, True,  "Windows registry (stdlib)"),
    ] if _WIN else []),
    # ── Linux only ───────────────────────────────────────────────────────────
    *([
        Dep("gi", "PyGObject", None, False, "Linux desktop integration (optional)"),
    ] if not _WIN and not _MAC else []),
]

# ── ANSI colours (Windows 10+ supports these in terminal) ────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

BAR_WIDTH = 36


# ── Version helpers ───────────────────────────────────────────────────────────

def _parse_version(v: str) -> tuple[int, ...]:
    """Convert '1.2.3' → (1, 2, 3) for comparison."""
    try:
        return tuple(int(x) for x in v.strip().split(".") if x.isdigit())
    except Exception:
        return (0,)


def _installed_version(pip_name: str) -> str | None:
    """Return installed version string, or None if not installed."""
    try:
        return importlib.metadata.version(pip_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _latest_version(pip_name: str) -> str | None:
    """Fetch latest version from PyPI. Returns None on failure."""
    try:
        import urllib.request, json
        url = f"https://pypi.org/pypi/{pip_name}/json"
        with urllib.request.urlopen(url, timeout=4) as resp:
            data = json.loads(resp.read())
        return data["info"]["version"]
    except Exception:
        return None


def _is_importable(import_name: str) -> bool:
    return importlib.util.find_spec(import_name) is not None


# ── Progress bar ──────────────────────────────────────────────────────────────

def _progress_bar(current: int, total: int, label: str = "", width: int = BAR_WIDTH) -> str:
    pct    = current / max(total, 1)
    filled = int(width * pct)
    bar    = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {int(pct*100):3d}%  {label}"


def _print_progress(current: int, total: int, label: str = ""):
    line = f"\r  {_progress_bar(current, total, label)}"
    sys.stdout.write(line.ljust(80))
    sys.stdout.flush()


# ── Install / update ──────────────────────────────────────────────────────────

def _pip_install(pip_name: str, upgrade: bool = False) -> bool:
    """Run pip install (or --upgrade). Returns True on success."""
    cmd = [sys.executable, "-m", "pip", "install", "--quiet"]
    if upgrade:
        cmd.append("--upgrade")
    cmd.append(pip_name)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def _ask_yes_no(prompt: str) -> bool:
    """Prompt user for y/n. Returns True for yes."""
    while True:
        try:
            answer = input(f"  {prompt} [y/n]: ").strip().lower()
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
        except (EOFError, KeyboardInterrupt):
            return False


# ── Status records ────────────────────────────────────────────────────────────

class DepStatus(NamedTuple):
    dep:          Dep
    installed:    bool
    version:      str | None   # installed version
    latest:       str | None   # latest on PyPI
    up_to_date:   bool         # True if installed >= min_version and >= latest (or no latest info)
    stdlib:       bool         # True if it's a stdlib module (no pip needed)


# ── Main check ────────────────────────────────────────────────────────────────

def check_and_install() -> bool:
    """
    Check all dependencies, print a status table, install/update as needed.
    Returns True if all REQUIRED deps are satisfied (JARVIS can start).
    Returns False if a required dep couldn't be installed.
    """
    _enable_ansi()
    print(f"\n{BOLD}{CYAN}  Checking dependencies...{RESET}\n")

    # ── Step 1: gather status with progress ──────────────────────────────────
    statuses: list[DepStatus] = []
    total = len(DEPENDENCIES)

    for i, dep in enumerate(DEPENDENCIES):
        _print_progress(i, total, dep.pip_name or dep.import_name)

        is_stdlib = dep.pip_name is None
        installed = _is_importable(dep.import_name)
        version   = _installed_version(dep.pip_name) if dep.pip_name and installed else None
        latest    = _latest_version(dep.pip_name)    if dep.pip_name and installed else None

        if is_stdlib:
            up_to_date = True
        elif not installed:
            up_to_date = False
        else:
            min_ok     = True
            latest_ok  = True
            if dep.min_version and version:
                min_ok = _parse_version(version) >= _parse_version(dep.min_version)
            if latest and version:
                latest_ok = _parse_version(version) >= _parse_version(latest)
            up_to_date = min_ok  # we consider min_version the hard floor; latest is advisory

        statuses.append(DepStatus(dep, installed, version, latest, up_to_date, is_stdlib))

    _print_progress(total, total, "Done")
    sys.stdout.write("\n\n")

    # ── Step 2: print status table ────────────────────────────────────────────
    _print_table(statuses)

    # ── Step 3: handle missing required deps ──────────────────────────────────
    missing_required = [s for s in statuses if not s.installed and s.dep.required and not s.stdlib]
    missing_optional = [s for s in statuses if not s.installed and not s.dep.required and not s.stdlib]
    outdated         = [s for s in statuses if s.installed and not s.up_to_date and s.dep.pip_name]

    can_start = True

    if missing_required:
        print(f"\n{RED}{BOLD}  Missing required packages:{RESET}")
        for s in missing_required:
            print(f"    • {s.dep.pip_name}  —  {s.dep.description}")
        print()
        if _ask_yes_no("Install all missing required packages now?"):
            for s in missing_required:
                sys.stdout.write(f"  Installing {s.dep.pip_name}... ")
                sys.stdout.flush()
                ok = _pip_install(s.dep.pip_name)
                print(f"{GREEN}done{RESET}" if ok else f"{RED}FAILED{RESET}")
                if not ok:
                    can_start = False
        else:
            print(f"\n  {RED}Warning: JARVIS cannot start without the required packages above.{RESET}")
            can_start = False

    if missing_optional:
        print(f"\n{YELLOW}  Missing optional packages:{RESET}")
        for s in missing_optional:
            print(f"    • {s.dep.pip_name}  —  {s.dep.description}")
        print()
        if _ask_yes_no("Install all optional packages now? (recommended)"):
            for s in missing_optional:
                sys.stdout.write(f"  Installing {s.dep.pip_name}... ")
                sys.stdout.flush()
                ok = _pip_install(s.dep.pip_name)
                print(f"{GREEN}done{RESET}" if ok else f"{RED}FAILED{RESET}")

    if outdated:
        print(f"\n{YELLOW}  Updates available:{RESET}")
        for s in outdated:
            latest_str = s.latest or "unknown"
            print(f"    • {s.dep.pip_name}  {DIM}({s.version} → {latest_str}){RESET}")
        print()
        if _ask_yes_no("Update all outdated packages?"):
            for s in outdated:
                sys.stdout.write(f"  Updating {s.dep.pip_name}... ")
                sys.stdout.flush()
                ok = _pip_install(s.dep.pip_name, upgrade=True)
                print(f"{GREEN}done{RESET}" if ok else f"{RED}FAILED{RESET}")
        else:
            print(f"\n  {YELLOW}⚠  Running with outdated packages. Some features may behave unexpectedly.{RESET}")

    if can_start and not missing_required and not outdated:
        print(f"\n  {GREEN}All dependencies satisfied.{RESET}")

    print()
    return can_start


def _print_table(statuses: list[DepStatus]):
    """Print a formatted dependency status table."""
    col_name    = 22
    col_inst    = 10
    col_latest  = 10
    col_status  = 20
    col_desc    = 36

    header = (
        f"  {'Package':<{col_name}}"
        f"{'Installed':<{col_inst}}"
        f"{'Latest':<{col_latest}}"
        f"{'Status':<{col_status}}"
        f"Description"
    )
    divider = "  " + "─" * (col_name + col_inst + col_latest + col_status + col_desc)
    print(header)
    print(divider)

    for s in statuses:
        name = s.dep.pip_name or s.dep.import_name

        if s.stdlib:
            inst_str   = "stdlib"
            latest_str = "─"
            status_str = f"{GREEN}(built-in){RESET}"
        elif not s.installed:
            inst_str   = "─"
            latest_str = s.latest or "─"
            tag        = "REQUIRED" if s.dep.required else "optional"
            status_str = f"{RED}not installed  [{tag}]{RESET}"
        else:
            inst_str   = s.version or "unknown"
            latest_str = s.latest  or "─"

            if s.latest and s.version and _parse_version(s.version) < _parse_version(s.latest):
                status_str = f"{YELLOW}(out of date){RESET}"
            else:
                status_str = f"{GREEN}(up to date){RESET}"

        print(
            f"  {name:<{col_name}}"
            f"{inst_str:<{col_inst}}"
            f"{latest_str:<{col_latest}}"
            f"{status_str:<{col_status + 20}}"   # +20 for ANSI escape len
            f"{DIM}{s.dep.description}{RESET}"
        )

    print()


def _enable_ansi():
    """Enable ANSI colour codes on Windows."""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass


if __name__ == "__main__":
    # Can be run standalone: python dependency_manager.py
    ok = check_and_install()
    sys.exit(0 if ok else 1)