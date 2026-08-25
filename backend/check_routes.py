"""诊断：检查路由注册情况"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from app.main import app

print("=== 已注册路由 ===")
for route in app.routes:
    if hasattr(route, "path") and hasattr(route, "methods"):
        methods = ", ".join(sorted(route.methods - {"HEAD", "OPTIONS"}))
        if methods:
            print(f"  {methods:10s} {route.path}")
