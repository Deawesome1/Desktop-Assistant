# scripts/inspect_brain_registry.py
import json, importlib
I = importlib.import_module('Desktop_Assistant.imports')
brain = None
if hasattr(I, 'get_brain'):
    brain = I.get_brain()
elif hasattr(I, 'Brain'):
    BrainClass = getattr(I, 'Brain')
    try:
        brain = BrainClass()
    except Exception as e:
        print('Could not instantiate Brain:', e)
        raise

if not brain:
    print('No Brain instance available')
else:
    print('BRAIN: commands_loaded attribute:', getattr(brain, 'commands_loaded', None))
    cmds = getattr(brain, 'commands', None) or getattr(brain, 'command_registry', None)
    print('BRAIN: commands dict present:', isinstance(cmds, dict))
    if isinstance(cmds, dict):
        print('BRAIN: registered names (sample 200):', list(cmds.keys())[:200])
        alias_map = {}
        for name, adapter in cmds.items():
            meta = adapter.get('metadata') if isinstance(adapter, dict) else getattr(adapter, 'metadata', None)
            aliases = (meta or {}).get('aliases') if isinstance(meta, dict) else getattr(adapter, 'aliases', None)
            if aliases:
                for a in aliases:
                    alias_map.setdefault(a, []).append(name)
        print('BRAIN: alias collisions (alias -> commands):')
        print(json.dumps({k:v for k,v in alias_map.items() if len(v)>1}, indent=2))
