"""test/test_commands.py — Check all command files for run() function."""
import os, ast

commands_dir = os.path.join(os.path.dirname(__file__), "..", "commands")
for fname in sorted(os.listdir(commands_dir)):
    if not fname.endswith(".py") or fname.startswith("_"):
        continue
    path = os.path.join(commands_dir, fname)
    src  = open(path).read()
    tree = ast.parse(src)
    has_run   = any(isinstance(n, ast.FunctionDef) and n.name == "run" for n in ast.walk(tree))
    has_class = any(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
    status = "OK  run()" if has_run else ("BAD CLASS - needs replacing" if has_class else "BAD no run() found")
    print(f"  {status:35s} {fname}")