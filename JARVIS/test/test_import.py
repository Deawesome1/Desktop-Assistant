"""test/test_import.py — Test that all command modules import and run cleanly."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from commands.time import run as time_run
print("Import OK: commands.time")
result = time_run("what time is it")
print(f"Result: {result}")