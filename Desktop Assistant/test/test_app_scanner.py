"""test/test_app_scanner.py — Force a rescan and print results."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from commands.app_scanner import rescan

cache = rescan()
print(f"\nTotal apps found: {cache['app_count']}")
print("\nFirst 20:")
for app in cache["apps"][:20]:
    admin = " [ADMIN]" if app["requires_admin"] else ""
    alias = f"  aliases: {app['aliases']}" if app["aliases"] else ""
    print(f"  {app['name']:<40} {app['source']}{admin}{alias}")