# scripts/inspect_loader.py
import json
from Desktop_Assistant.brain.loader import CommandLoader

loader = CommandLoader(os_key='windows')
commands, alias_map = loader.load_all()

print('LOADER: discovered command count:', len(commands))
print('LOADER: sample command names:', list(commands.keys())[:200])
print('LOADER: alias_map sample (first 200):')
print(json.dumps({k: alias_map[k] for k in list(alias_map.keys())[:200]}, indent=2))
if 'open_app' in commands:
    adapter = commands['open_app']
    if isinstance(adapter, dict):
        print('LOADER: open_app metadata (adapter.metadata):', adapter.get('metadata'))
    else:
        print('LOADER: open_app metadata (adapter object):', getattr(adapter, 'metadata', None))
