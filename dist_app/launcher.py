#!/usr/bin/env python
"""昆仑创作引擎 — 应用程序入口"""
import sys
import os
import webbrowser
import threading
import time
from pathlib import Path

# Determine app root
if getattr(sys, 'frozen', False):
    APP_ROOT = Path(sys.executable).parent
else:
    APP_ROOT = Path(__file__).parent

os.chdir(APP_ROOT)

# Ensure data dirs
for d in ['data/logs', 'data/books', 'data/snapshots', 'data/qdrant']:
    (APP_ROOT / d).mkdir(parents=True, exist_ok=True)

def main():
    import uvicorn

    # Auto-open browser after server starts
    def open_browser():
        time.sleep(2)
        try:
            import urllib.request
            for _ in range(15):
                try:
                    urllib.request.urlopen("http://127.0.0.1:8000", timeout=1)
                    webbrowser.open("http://127.0.0.1:8000")
                    break
                except Exception:
                    time.sleep(1)
        except Exception:
            pass

    threading.Thread(target=open_browser, daemon=True).start()

    print("\\n  Kunlun Engine v0.3.0 starting...")
    print("  http://127.0.0.1:8000\\n")

    uvicorn.run(
        "kunlun.api.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )

if __name__ == "__main__":
    main()
