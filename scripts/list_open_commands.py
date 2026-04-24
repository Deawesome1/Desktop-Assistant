# scripts/list_open_commands.py
import pkgutil, importlib
pkg_path = 'Desktop_Assistant/commands'
for finder, name, ispkg in pkgutil.walk_packages([pkg_path], prefix='Desktop_Assistant.commands.'):
    try:
        m = importlib.import_module(name)
        meta = getattr(m, 'get_metadata', lambda: None)()
        if meta:
            name_meta = (meta.get('name') or '').lower()
            aliases = [a.lower() for a in (meta.get('aliases') or [])]
            if 'open' in name_meta or any('open' in a for a in aliases):
                print(name, '->', meta)
    except Exception:
        pass
