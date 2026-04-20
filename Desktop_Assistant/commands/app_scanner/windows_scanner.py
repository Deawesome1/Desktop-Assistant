"""
windows_impl.py — Windows app directory scanner for JARVIS.

This is your original implementation, extracted from the old app_scanner.py
and used only when OS == "Windows".
"""

import os
import json
import glob
import winreg
import sys
import time
from pathlib import Path

CACHE_PATH   = os.path.join(os.path.dirname(__file__), "..", "config", "app_cache.json")
CONFIG_PATH  = os.path.join(os.path.dirname(__file__), "..", "config", "apps_config.json")

ADMIN_PATH_FRAGMENTS = [
    "\\system32\\",
    "\\syswow64\\",
    "\\windows\\system\\",
    "\\program files\\common files\\",
    "\\program files (x86)\\common files\\",
]

LAUNCH_EXTENSIONS = {".lnk", ".exe", ".url"}

SKIP_PATH_FRAGMENTS = [
    "\\system32\\", "\\syswow64\\", "\\windows\\",
    "\\common files\\", "\\microsoft shared\\",
    "\\windowsapps\\", "\\winsxs\\",
    "\\drivers\\", "\\driverstore\\",
    "\\diagnostics\\", "\\servicing\\",
    "\\assembly\\", "\\dotnet\\",
    "\\microsoft.net\\", "\\reference assemblies\\",
]

SKIP_NAME_FRAGMENTS = [
    "uninstall", "setup", "install", "update", "updater", "helper",
    "crash", "report", "crashpad", "handler", "injector", "broker",
    "service", "daemon", "agent", "host", "server", "proxy",
    "register", "regsvr", "rundll", "dllhost", "svchost",
    "elevate", "cef", "renderer", "launcher_helper",
    "_fm2", "_gui", "hal_", "hal ",
]


class ProgressBar:
    WIDTH = 40

    def __init__(self, total: int, label: str = "Progress"):
        self.total   = max(total, 1)
        self.label   = label
        self.current = 0
        self._draw(0, "")

    def update(self, current: int, suffix: str = ""):
        self.current = min(current, self.total)
        self._draw(self.current, suffix)

    def increment(self, suffix: str = ""):
        self.update(self.current + 1, suffix)

    def finish(self, message: str = "Done"):
        self._draw(self.total, message)
        sys.stdout.write("\n")
        sys.stdout.flush()

    def _draw(self, current: int, suffix: str):
        pct      = current / self.total
        filled   = int(self.WIDTH * pct)
        bar      = "█" * filled + "░" * (self.WIDTH - filled)
        pct_str  = f"{int(pct * 100):3d}%"
        max_suffix = 30
        suffix_display = suffix[:max_suffix].ljust(max_suffix)
        line = f"\r  {self.label} [{bar}] {pct_str}  {suffix_display}"
        sys.stdout.write(line)
        sys.stdout.flush()


def _load_config() -> dict:
    defaults = {
        "allow_admin": False,
        "scan_on_startup": True,
        "extra_scan_paths": [],
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                loaded = json.load(f)
            defaults.update(loaded)
        except Exception:
            pass
    return defaults


def _normalize_name(raw: str) -> str:
    import re
    name = Path(raw).stem
    name = name.replace("_", " ").replace("-", " ")
    for noise in [" - Shortcut", " - Desktop"]:
        name = name.replace(noise, "")
    name = re.sub(r"\s*\((x64|x86|64.bit|32.bit|\d+)\)", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+\d+[\d\.\-]+.*$", "", name).strip()
    name = re.sub(r" {2,}", " ", name)
    return name.strip()


def _is_admin_path(path: str) -> bool:
    p = path.lower().replace("/", "\\")
    return any(frag in p for frag in ADMIN_PATH_FRAGMENTS)


def _get_scan_dirs() -> list[str]:
    user   = os.path.expanduser("~")
    config = _load_config()
    dirs = [
        os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        os.path.join(user, "Desktop"),
        os.path.join(user, "OneDrive", "Desktop"),
        r"C:\Users\Public\Desktop",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
    ]
    dirs += config.get("extra_scan_paths", [])
    return [d for d in dirs if d]


def _is_skippable(filepath: str, name: str) -> bool:
    p    = filepath.lower().replace("/", "\\")
    nlow = name.lower()
    if any(frag in p for frag in SKIP_PATH_FRAGMENTS):
        return True
    if any(frag in nlow for frag in SKIP_NAME_FRAGMENTS):
        return True
    return False


def _scan_directory(directory: str, seen_names: set, bar: ProgressBar) -> list[dict]:
    apps = []
    if not os.path.isdir(directory):
        return apps
    for ext in LAUNCH_EXTENSIONS:
        for filepath in glob.glob(os.path.join(directory, "**", f"*{ext}"), recursive=True):
            name = _normalize_name(os.path.basename(filepath))
            if not name or len(name) < 2:
                continue
            if _is_skippable(filepath, name):
                continue
            key = name.lower()
            if key in seen_names:
                continue
            seen_names.add(key)
            apps.append({
                "name":           name,
                "name_lower":     key,
                "path":           filepath,
                "requires_admin": _is_admin_path(filepath),
                "aliases":        [],
                "source":         "filesystem",
            })
            bar.increment(suffix=name)
    return apps


REGISTRY_SKIP_TERMS = [
    "driver", "drivers", "chipset", "firmware", "hal",
    "smbus", "gpio", "psp ", "pci ", "i2c ", "wvr", "dvr",
    "aura", "armou", "aio fan", "aiofan",
    "redistributable", "runtime", "sdk", "ddk", "pdk", "wdk",
    "visual c++", "directx", "opengl", "vulkan", "physx", "havok",
    "microsoft edge webview", "windows sdk", "windows kits",
    ".net framework", "windows app certification",
    "application verifier", "msi development tools", "setup components",
    "diagnostic", "diagnostics", "telemetry",
    "update for", "hotfix", "security update", "cumulative update",
    "definition update", "language pack", "language feature", "input method",
    "lite service", "service component", "support (32", "support (64",
    "install manager", "user experience program",
    "software update", "application support",
    "framework service", "update helper", "motherboard hal",
    "extension card", "onecoreuap", "desktopeditions",
    "branding", "motherboard", "oem ", "provisioning",
]


def _is_registry_skippable(display_name: str) -> bool:
    n = display_name.lower()
    for term in REGISTRY_SKIP_TERMS:
        if term in n:
            return True
    import re
    if re.search(r"\bkb\d{6,}", n):
        return True
    return False


def _scan_registry(bar: ProgressBar) -> list[dict]:
    apps = []
    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    seen = set()
    for hive, path in reg_paths:
        try:
            key   = winreg.OpenKey(hive, path)
            count = winreg.QueryInfoKey(key)[0]
            for i in range(count):
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey      = winreg.OpenKey(key, subkey_name)
                    display_name = None
                    install_loc  = None
                    no_modify    = 0
                    try:
                        display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                        try:
                            install_loc, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                        except FileNotFoundError:
                            pass
                        try:
                            no_modify, _ = winreg.QueryValueEx(subkey, "NoModify")
                        except FileNotFoundError:
                            pass
                    except FileNotFoundError:
                        pass
                    winreg.CloseKey(subkey)

                    if not display_name:
                        continue
                    import re as _re
                    dn = display_name.strip()
                    dn = _re.sub(r"\s*\([^)]*\)", "", dn).strip()
                    dn = _re.sub(r"\s+(v|version\s+)?\d[\d\.\-_]*$", "", dn, flags=_re.IGNORECASE).strip()
                    display_name = dn if dn else display_name.strip()
                    name_lower = display_name.lower().strip()
                    if name_lower in seen or len(name_lower) < 2:
                        continue
                    if _is_registry_skippable(display_name):
                        continue
                    seen.add(name_lower)

                    exe_path = ""
                    if install_loc and os.path.isdir(install_loc):
                        exes = glob.glob(os.path.join(install_loc, "*.exe"))
                        if exes:
                            exe_path = exes[0]

                    apps.append({
                        "name":           display_name.strip(),
                        "name_lower":     name_lower,
                        "path":           exe_path,
                        "requires_admin": _is_admin_path(exe_path) if exe_path else False,
                        "aliases":        [],
                        "source":         "registry",
                    })
                    bar.increment(suffix=display_name.strip())
                except Exception:
                    continue
            winreg.CloseKey(key)
        except Exception:
            continue
    return apps


def _dedup_apps(apps: list[dict]) -> list[dict]:
    from difflib import SequenceMatcher
    import re

    def similarity(a: str, b: str) -> float:
        a = re.sub(r"[^a-z0-9 ]", "", a)
        b = re.sub(r"[^a-z0-9 ]", "", b)
        return SequenceMatcher(None, a, b).ratio()

    kept: list[dict] = []
    for app in apps:
        duplicate = False
        for existing in kept:
            if similarity(app["name_lower"], existing["name_lower"]) >= 0.88:
                if app["source"] == "filesystem" and existing["source"] == "registry":
                    kept.remove(existing)
                    kept.append(app)
                for alias in app.get("aliases", []):
                    if alias not in existing.get("aliases", []):
                        existing["aliases"].append(alias)
                duplicate = True
                break
        if not duplicate:
            kept.append(app)
    return kept


def build_cache(force: bool = False) -> dict:
    existing_aliases: dict[str, list] = {}

    if os.path.exists(CACHE_PATH) and not force:
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
            for app in existing.get("apps", []):
                if app.get("aliases"):
                    existing_aliases[app["name_lower"]] = app["aliases"]
            count = len(existing.get("apps", []))
            print(f"  Loaded app cache: {count} apps.\n")
            return existing
        except Exception:
            pass

    print("\n  Scanning for installed applications...\n")

    scan_dirs   = [d for d in _get_scan_dirs() if os.path.isdir(d)]
    seen_names: set = set()
    all_apps:   list[dict] = []

    print("  Counting files...")
    total_files = 0
    for d in scan_dirs:
        for ext in LAUNCH_EXTENSIONS:
            total_files += len(glob.glob(os.path.join(d, "**", f"*{ext}"), recursive=True))
    total_files = max(total_files, 1)

    fs_bar = ProgressBar(total=total_files, label="Filesystem")
    for directory in scan_dirs:
        found = _scan_directory(directory, seen_names, fs_bar)
        all_apps.extend(found)
    fs_bar.finish(f"{len(all_apps)} apps found")

    reg_count = 0
    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, path in reg_paths:
        try:
            k = winreg.OpenKey(hive, path)
            reg_count += winreg.QueryInfoKey(k)[0]
            winreg.CloseKey(k)
        except Exception:
            pass
    reg_count = max(reg_count, 1)

    reg_bar  = ProgressBar(total=reg_count, label="Registry  ")
    reg_apps = _scan_registry(reg_bar)
    for app in reg_apps:
        if app["name_lower"] not in seen_names:
            seen_names.add(app["name_lower"])
            all_apps.append(app)
    reg_bar.finish(f"{len(reg_apps)} registry entries read")

    for app in all_apps:
        if app["name_lower"] in existing_aliases:
            app["aliases"] = existing_aliases[app["name_lower"]]

    all_apps = _dedup_apps(all_apps)
    all_apps.sort(key=lambda a: a["name_lower"])

    cache = {"app_count": len(all_apps), "apps": all_apps}
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    print(f"\n  App directory complete: {len(all_apps)} apps indexed.\n")
    return cache


def get_cache() -> dict:
    if not os.path.exists(CACHE_PATH):
        return build_cache(force=True)
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return build_cache(force=True)


def add_alias(app_name_lower: str, alias: str) -> bool:
    cache = get_cache()
    alias_lower = alias.lower().strip()
    for app in cache["apps"]:
        if app["name_lower"] == app_name_lower:
            if alias_lower not in [a.lower() for a in app["aliases"]]:
                app["aliases"].append(alias)
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
            return True
    return False


def rescan() -> dict:
    return build_cache(force=True)
