"""
app_scanner.py — Windows app directory scanner.
On Mac/Linux, stubs are returned so imports never fail.
open_app.py uses UNIX_APP_MAP on non-Windows platforms.
"""

import sys as _platform_sys

# ── Non-Windows stub ──────────────────────────────────────────────────────────
if _platform_sys.platform != "win32":
    def build_cache(force=False): return {"app_count": 0, "apps": []}
    def get_cache():               return {"app_count": 0, "apps": []}
    def add_alias(name, alias):    return False
    def rescan():                  return {"app_count": 0, "apps": []}
else:
    # ── Full Windows implementation ───────────────────────────────────────────


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

    # Path fragments that indicate a non-user-facing binary — skip entirely
    SKIP_PATH_FRAGMENTS = [
        "\\system32\\", "\\syswow64\\", "\\windows\\",
        "\\common files\\", "\\microsoft shared\\",
        "\\windowsapps\\", "\\winsxs\\",
        "\\drivers\\", "\\driverstore\\",
        "\\diagnostics\\", "\\servicing\\",
        "\\assembly\\", "\\dotnet\\",
        "\\microsoft.net\\", "\\reference assemblies\\",
    ]

    # Filename fragments that indicate internal/helper executables — skip these
    SKIP_NAME_FRAGMENTS = [
        "uninstall", "setup", "install", "update", "updater", "helper",
        "crash", "report", "crashpad", "handler", "injector", "broker",
        "service", "daemon", "agent", "host", "server", "proxy",
        "register", "regsvr", "rundll", "dllhost", "svchost",
        "elevate", "cef", "renderer", "launcher_helper",
        "_fm2", "_gui", "hal_", "hal ",
    ]


    # ── Progress bar ──────────────────────────────────────────────────────────────

    class ProgressBar:
        """
        A simple inline terminal progress bar.

        Usage:
            bar = ProgressBar(total=10, label="Scanning")
            for i in range(10):
                bar.update(i + 1, suffix="file.exe")
            bar.finish()
        """
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
            # Truncate suffix so the line doesn't wrap
            max_suffix = 30
            suffix_display = suffix[:max_suffix].ljust(max_suffix)
            line = f"\r  {self.label} [{bar}] {pct_str}  {suffix_display}"
            sys.stdout.write(line)
            sys.stdout.flush()


    # ── Helpers ───────────────────────────────────────────────────────────────────

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
        # Replace underscores/hyphens with spaces
        name = name.replace("_", " ").replace("-", " ")
        # Remove noise suffixes
        for noise in [" - Shortcut", " - Desktop"]:
            name = name.replace(noise, "")
        # Remove parenthetical arch/version tags: (x64), (x86), (64-bit), (32-bit)
        name = re.sub(r"\s*\((x64|x86|64.bit|32.bit|\d+)\)", "", name, flags=re.IGNORECASE)
        # Remove trailing version strings: "7-Zip 22.01" -> "7-Zip"
        name = re.sub(r"\s+\d+[\d\.\-]+.*$", "", name).strip()
        # Collapse multiple spaces
        name = re.sub(r" {2,}", " ", name)
        return name.strip()


    def _is_admin_path(path: str) -> bool:
        p = path.lower().replace("/", "\\")
        return any(frag in p for frag in ADMIN_PATH_FRAGMENTS)


    def _get_scan_dirs() -> list[str]:
        """
        Only scan locations with user-facing shortcuts.
        Deliberately excludes Program Files to avoid indexing thousands of
        internal binaries. Add custom game/app folders via extra_scan_paths
        in apps_config.json.
        """
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
        """Return True if this file should be excluded from the app list."""
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


    # Registry entries whose display names contain these are skipped (drivers, SDKs, runtimes)
    REGISTRY_SKIP_TERMS = [
        # Drivers and hardware
        "driver", "drivers", "chipset", "firmware", "hal",
        "smbus", "gpio", "psp ", "pci ", "i2c ", "wvr", "dvr",
        "aura", "armou", "aio fan", "aiofan",
        # Runtimes and SDKs
        "redistributable", "runtime", "sdk", "ddk", "pdk", "wdk",
        "visual c++", "directx", "opengl", "vulkan", "physx", "havok",
        "microsoft edge webview", "windows sdk", "windows kits",
        ".net framework", "windows app certification",
        "application verifier", "msi development tools", "setup components",
        # System / Windows components
        "diagnostic", "diagnostics", "telemetry",
        "update for", "hotfix", "security update", "cumulative update",
        "definition update", "language pack", "language feature", "input method",
        # Background services and support tools
        "lite service", "service component", "support (32", "support (64",
        "install manager", "user experience program",
        "software update", "application support",
        "framework service", "update helper", "motherboard hal",
        "extension card", "onecoreuap", "desktopeditions",
        # Branding / OEM noise
        "branding", "motherboard", "oem ", "provisioning",
    ]


    def _is_registry_skippable(display_name: str) -> bool:
        n = display_name.lower()
        for term in REGISTRY_SKIP_TERMS:
            if term in n:
                return True
        # Skip entries that look like KB article numbers e.g. "Update for KB1234567"
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
                        # Clean up display name: strip version numbers and arch tags
                        import re as _re
                        dn = display_name.strip()
                        # Remove parenthetical suffixes: (x64), (x64 edition), (32-bit), (2.3)
                        dn = _re.sub(r"\s*\([^)]*\)", "", dn).strip()
                        # Remove trailing version strings: "App 22.01" or "App v2.3.4"
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


    # ── Public API ────────────────────────────────────────────────────────────────


    def _dedup_apps(apps: list[dict]) -> list[dict]:
        """
        Remove near-duplicate entries caused by the same app appearing in both
        the filesystem scan (shortcut) and registry (installed entry) with
        slightly different names e.g. "Alien Swarm Reactive Drop" vs
        "Alien Swarm: Reactive Drop". Keeps the filesystem entry when both exist.
        """
        from difflib import SequenceMatcher

        def similarity(a: str, b: str) -> float:
            # Strip punctuation for comparison
            import re
            a = re.sub(r"[^a-z0-9 ]", "", a)
            b = re.sub(r"[^a-z0-9 ]", "", b)
            return SequenceMatcher(None, a, b).ratio()

        kept: list[dict] = []
        for app in apps:
            duplicate = False
            for existing in kept:
                if similarity(app["name_lower"], existing["name_lower"]) >= 0.88:
                    # Prefer filesystem (shortcut) over registry
                    if app["source"] == "filesystem" and existing["source"] == "registry":
                        kept.remove(existing)
                        kept.append(app)
                    # Merge aliases
                    for alias in app.get("aliases", []):
                        if alias not in existing.get("aliases", []):
                            existing["aliases"].append(alias)
                    duplicate = True
                    break
            if not duplicate:
                kept.append(app)
        return kept

    def build_cache(force: bool = False) -> dict:
        """
        Scan the PC and build the app cache.
        Loads existing cache if force=False and cache exists.
        Always preserves existing aliases when refreshing.
        """
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

        # ── Phase 1: Filesystem ───────────────────────────────────────────────────
        scan_dirs   = [d for d in _get_scan_dirs() if os.path.isdir(d)]
        seen_names: set = set()
        all_apps:   list[dict] = []

        # Pre-count files for accurate progress (quick glob)
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

        # ── Phase 2: Registry ─────────────────────────────────────────────────────
        # Count registry entries first
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

        # ── Restore aliases + save ────────────────────────────────────────────────
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