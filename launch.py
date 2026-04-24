# launch.py (project root)
import runpy
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(prog="launch.py", description="Launch JARVIS")
    parser.add_argument(
        "-f", "--force-deps",
        action="store_true",
        help="Force reinstall dependencies from requirements files without recreating the venv"
    )
    # Keep this flexible for future flags
    args, remaining = parser.parse_known_args()

    # Expose the flag to the boot.run module via an environment variable
    # (simple and avoids import-time side effects)
    if args.force_deps:
        import os
        os.environ["JARVIS_FORCE_DEPS"] = "1"

    # Run the boot.run module as __main__ (same behavior as before)
    runpy.run_module("Desktop_Assistant.boot.run", run_name="__main__")

if __name__ == "__main__":
    main()
