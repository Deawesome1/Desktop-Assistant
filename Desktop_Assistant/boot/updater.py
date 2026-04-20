# boot/updater.py

def check_for_updates(old_version: str | None):
    """
    Stub: compares old_version with current.
    You can later hook this to GitHub or a remote JSON.
    """
    if old_version is None:
        print("\nNo previous version recorded. Fresh install.")
        return

    print(f"\nPrevious JARVIS version detected:\n  {old_version}")
    print("Update check: (stub) — hook to GitHub or remote metadata later.")
