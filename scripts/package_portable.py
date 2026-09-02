#!/usr/bin/env python
"""
昆仑创作引擎 — 便携版打包
生成可在任意 Windows 电脑上直接运行的文件夹
双击「昆仑创作引擎.bat」即可启动
"""

import subprocess
import sys
import os
import shutil
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST = PROJECT_ROOT / "昆仑引擎_便携版"


def run(cmd, **kw):
    print(f"  > {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    return subprocess.run(cmd, shell=isinstance(cmd, str), check=True, **kw)


def main():
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║  昆仑创作引擎 — 便携版打包                      ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()

    # Clean
    if DIST.exists():
        shutil.rmtree(DIST)
        print("  [1] Cleaned previous build")

    # Create structure
    (DIST / "backend").mkdir(parents=True)
    (DIST / "data").mkdir()
    (DIST / "data" / "logs").mkdir()
    (DIST / "data" / "books").mkdir()
    (DIST / "data" / "snapshots").mkdir()

    # Copy frontend build
    print("  [2] Building frontend...")
    run(["npm", "run", "build"], cwd=PROJECT_ROOT / "frontend", capture_output=True, text=True)
    shutil.copytree(PROJECT_ROOT / "frontend" / "dist", DIST / "static")
    print("     frontend/dist → static/")

    # Copy web UI
    shutil.copytree(PROJECT_ROOT / "web", DIST / "web")
    print("     web/ → web/")

    # Copy Python backend
    shutil.copytree(
        PROJECT_ROOT / "kunlun",
        DIST / "backend" / "kunlun",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    print("     kunlun/ → backend/kunlun/")

    # Copy skills
    shutil.copytree(PROJECT_ROOT / "skills", DIST / "backend" / "skills")
    print("     skills/ → backend/skills/")

    # Copy config
    for f in [".env", ".env.example", "kunlun.json", "requirements.txt"]:
        src = PROJECT_ROOT / f
        if src.exists():
            shutil.copy(src, DIST / "backend" / f)
    print("     config files → backend/")

    # Copy data
    data_src = PROJECT_ROOT / "data"
    if data_src.exists():
        for item in data_src.iterdir():
            if item.is_dir() and item.name not in ("logs", "books", "snapshots"):
                shutil.copytree(
                    item, DIST / "data" / item.name, ignore=shutil.ignore_patterns("*.db")
                )
        # Copy SQLite DBs
        for db in data_src.glob("*.db"):
            shutil.copy(db, DIST / "data" / db.name)

    # Create launcher script
    launcher = DIST / "启动.bat"
    launcher.write_text(
        """@echo off
chcp 65001 >nul 2>&1
title 昆仑创作引擎
cd /d "%~dp0"

echo.
echo   ============================================================
echo     昆仑创作引擎 v0.3.0
echo     Kunlun Creation Engine
echo   ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [ERROR] Python not found. Please install Python 3.11+
    echo   https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Install deps if needed
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo   Installing dependencies...
    python -m pip install -r backend\\requirements.txt -q
)

:: Start server
echo   Starting server...
echo   http://localhost:8000
echo.
start http://localhost:8000

cd backend
python -m uvicorn kunlun.api.main:app --host 0.0.0.0 --port 8000

pause
""",
        encoding="ascii",
    )

    print("  [3] Created 启动.bat")

    # Create README
    (DIST / "说明.txt").write_text(
        """昆仑创作引擎 v0.3.0 — 便携版
================================

使用方法:
  1. 双击「启动.bat」
  2. 首次运行会自动安装 Python 依赖
  3. 浏览器自动打开 http://localhost:8000

需要:
  - Python 3.11+ (https://www.python.org/downloads/)
  - Docker Desktop (可选，用于 KG/缓存/消息总线)
    - 不装 Docker 也可以使用降级模式

目录结构:
  backend/  — 后端 Python 代码
  static/   — Vue 桌面版前端
  web/      — Web 界面
  data/     — 本地数据

问题反馈: 查看 backend/.env 配置 API Key
""",
        encoding="utf-8",
    )

    print("  [4] Created 说明.txt")

    # Create ZIP
    zip_path = PROJECT_ROOT / "昆仑引擎_v0.3.0_便携版.zip"
    print(f"  [5] Creating ZIP: {zip_path.name} ...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(DIST):
            for fn in files:
                fp = Path(root) / fn
                arcname = fp.relative_to(DIST.parent)
                zf.write(fp, arcname)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"\n  ✅ 打包完成!")
    print(f"     📦 {zip_path}")
    print(f"     📏 {size_mb:.1f} MB")
    print(f"     📂 {DIST}")
    print(f"\n  使用方法: 解压 ZIP，双击「启动.bat」")


if __name__ == "__main__":
    main()
