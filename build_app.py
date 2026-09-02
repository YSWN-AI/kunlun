#!/usr/bin/env python
"""
昆仑创作引擎 — 应用程序打包构建脚本
一键构建：python build_app.py
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DIST_DIR = PROJECT_ROOT / "dist_app"
BUILD_DIR = PROJECT_ROOT / "build_app_temp"


def step(msg: str):
    print(f"\n  {'=' * 50}")
    print(f"  {msg}")
    print(f"  {'=' * 50}")


def build_frontend():
    """Build Vue frontend as static files."""
    step("Step 1/4: Building Vue Frontend...")

    if not (FRONTEND_DIR / "node_modules").exists():
        print("  Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=True)

    print("  Running vite build...")
    result = subprocess.run(
        ["npx", "vite", "build"],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    if result.returncode != 0:
        print(f"  Build failed:\n{result.stderr[:500]}")
        return False

    print("  Frontend built: frontend/dist/")
    return True


def copy_built_files():
    """Copy all necessary files to dist_app."""
    step("Step 2/4: Copying Files...")

    # Clean previous build
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    DIST_DIR.mkdir(parents=True)

    # Copy frontend dist
    frontend_dist = FRONTEND_DIR / "dist"
    if frontend_dist.exists():
        shutil.copytree(frontend_dist, DIST_DIR / "static")
        print("  Copied: frontend/dist → dist_app/static")

    # Copy web UI
    web_dir = PROJECT_ROOT / "web"
    if web_dir.exists():
        shutil.copytree(web_dir, DIST_DIR / "web")
        print("  Copied: web/ → dist_app/web")

    # Copy skills
    skills_dir = PROJECT_ROOT / "skills"
    if skills_dir.exists():
        shutil.copytree(skills_dir, DIST_DIR / "skills")
        print("  Copied: skills/ → dist_app/skills")

    # Copy Python source
    kunlun_dir = PROJECT_ROOT / "kunlun"
    shutil.copytree(
        kunlun_dir,
        DIST_DIR / "kunlun",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
    print("  Copied: kunlun/ → dist_app/kunlun")

    # Copy data directory structure
    data_dir = PROJECT_ROOT / "data"
    if data_dir.exists():
        shutil.copytree(
            data_dir,
            DIST_DIR / "data",
            ignore=shutil.ignore_patterns("*.db", "__pycache__", "*.pyc"),
        )
        print("  Copied: data/ → dist_app/data")
    else:
        (DIST_DIR / "data").mkdir(parents=True)
        (DIST_DIR / "data" / "logs").mkdir(parents=True)
        (DIST_DIR / "data" / "books").mkdir(parents=True)
        (DIST_DIR / "data" / "snapshots").mkdir(parents=True)
        print("  Created: dist_app/data/ (empty)")

    # Copy requirements
    req_file = PROJECT_ROOT / "requirements.txt"
    if req_file.exists():
        shutil.copy(req_file, DIST_DIR / "requirements.txt")

    # Copy config files
    for f in [".env.example", "kunlun.json"]:
        src = PROJECT_ROOT / f
        if src.exists():
            shutil.copy(src, DIST_DIR / f)

    # Copy .env if exists
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        shutil.copy(env_file, DIST_DIR / ".env")
        print("  Copied: .env → dist_app/.env")

    return True


def create_launcher():
    """Create the launcher script that will be bundled."""
    step("Step 3/4: Creating Launcher...")

    launcher = DIST_DIR / "launcher.py"
    launcher.write_text(
        """#!/usr/bin/env python
\"\"\"昆仑创作引擎 — 应用程序入口\"\"\"
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

    print("\\\\n  Kunlun Engine v0.3.0 starting...")
    print("  http://127.0.0.1:8000\\\\n")

    uvicorn.run(
        "kunlun.api.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )

if __name__ == "__main__":
    main()
""",
        encoding="utf-8",
    )

    print("  Created: dist_app/launcher.py")
    return True


def build_exe():
    """Build executable with PyInstaller."""
    step("Step 4/4: Building Executable with PyInstaller...")

    # PyInstaller command
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=昆仑创作引擎",
        "--onefile",
        "--console",
        "--clean",
        "--noconfirm",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={DIST_DIR}",
        "--add-data",
        f"{DIST_DIR / 'kunlun'};kunlun",
        "--add-data",
        f"{DIST_DIR / 'static'};static",
        "--add-data",
        f"{DIST_DIR / 'web'};web",
        "--add-data",
        f"{DIST_DIR / 'skills'};skills",
        "--add-data",
        f"{DIST_DIR / 'data'};data",
        "--hidden-import=uvicorn",
        "--hidden-import=fastapi",
        "--hidden-import=kunlun",
        "--hidden-import=kunlun.api",
        "--hidden-import=kunlun.api.main",
        "--hidden-import=kunlun.api.routes",
        "--hidden-import=kunlun.kg",
        "--hidden-import=kunlun.kg.client",
        "--hidden-import=kunlun.audit",
        "--hidden-import=kunlun.agents",
        "--hidden-import=kunlun.gacha",
        "--hidden-import=kunlun.style",
        str(DIST_DIR / "launcher.py"),
    ]

    print("  This may take 3-5 minutes...")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, timeout=600, check=False)

    if result.returncode == 0:
        exe_path = DIST_DIR / "昆仑创作引擎.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\\n  ✓ Build successful!")
            print(f"  📦 {exe_path}")
            print(f"  📏 Size: {size_mb:.1f} MB")

            # Copy to project root for easy access
            root_exe = PROJECT_ROOT / "昆仑创作引擎.exe"
            shutil.copy(exe_path, root_exe)
            print(f"  📋 Copied to: {root_exe}")
            return True

    print("  Build failed. See output above for errors.")
    return False


def main():
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║  昆仑创作引擎 — 应用程序打包构建            ║")
    print("  ║  Kunlun Engine App Builder                  ║")
    print("  ╚══════════════════════════════════════════════╝")

    # Step 1: Build frontend
    if not build_frontend():
        print("\\n  Frontend build failed. Aborting.")
        sys.exit(1)

    # Step 2: Copy files
    copy_built_files()

    # Step 3: Create launcher
    create_launcher()

    # Step 4: Build EXE
    if build_exe():
        print("\\n  ✅ All done! Double-click '昆仑创作引擎.exe' to launch.")
    else:
        print("\\n  ⚠️ EXE build failed, but files are ready in dist_app/")
        print("  You can run: python dist_app/launcher.py")


if __name__ == "__main__":
    main()
