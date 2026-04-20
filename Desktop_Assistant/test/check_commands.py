import os, ast

commands_dir = r"c:\Users\miche\OneDrive\Documents\GitHub\Desktop-Assistant\JARVIS\commands"
for fname in os.listdir(commands_dir):
    if not fname.endswith(".py") or fname.startswith("_"):
        continue
    path = os.path.join(commands_dir, fname)
    src = open(path).read()
    tree = ast.parse(src)
    has_run_func = any(isinstance(n, ast.FunctionDef) and n.name == "run" for n in ast.walk(tree))
    has_class    = any(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
    status = "OK  run()" if has_run_func else ("BAD CLASS — needs replacing" if has_class else "BAD no run() found")
    print(f"  {status:35s} {fname}")