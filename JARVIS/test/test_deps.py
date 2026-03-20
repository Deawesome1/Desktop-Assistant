"""test/test_deps.py — Run the dependency checker standalone."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dependency_manager import check_and_install

ok = check_and_install()
sys.exit(0 if ok else 1)