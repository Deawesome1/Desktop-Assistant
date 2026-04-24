# scripts/list_all_command_metadata.py
import pkgutil, importlib
pkg_path = "Desktop_Assistant/commands"
for finder, name, ispkg in pkgutil.walk_packages([pkg_path], prefix="Desktop_Assistant.commands."):
    try:
        m = importlib.import_module(name)
        meta = getattr(m, "get_metadata", lambda: None)()
        if meta:
            print(name, "->", meta)
    except Exception as e:
        print(name, "-> import failed:", type(e).__name__, str(e))
