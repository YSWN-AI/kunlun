# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — 昆仑创作引擎 CLI 版打包
对标 AI_NovelGenerator 的 PyInstaller 打包方案

用法:
    pyinstaller --clean kunlun.spec
    输出: dist/kunlun.exe
"""

import sys
from pathlib import Path

# ── 项目根目录 ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent

# ── 收集 kunlun 子包 ────────────────────────────────
kunlun_dir = PROJECT_ROOT / "kunlun"
hidden_imports = []

# 自动收集所有 kunlun 子模块
for py_file in sorted(kunlun_dir.rglob("*.py")):
    if py_file.name.startswith("_"):
        continue
    rel = py_file.relative_to(PROJECT_ROOT).with_suffix("")
    module_name = str(rel).replace("\\", ".").replace("/", ".")
    hidden_imports.append(module_name)

# 添加第三方依赖
hidden_imports += [
    "fastapi",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "pydantic",
    "pydantic_settings",
    "loguru",
    "httpx",
    "jieba",
    "aiofiles",
    "yaml",
    "dotenv",
    "rich",
    "starlette",
    "websockets",
    "anyio",
    "httpcore",
    "h11",
    "multipart",
]

# 排除大型非必要库（昆仑自用场景不需要）
excluded_modules = [
    "matplotlib",
    "numpy",
    "scipy",
    "pandas",
    "PIL",
    "cv2",
    "tensorflow",
    "torch",
    "torchvision",
    "sklearn",
    "sentence_transformers",
    "transformers",
    "tokenizers",
    "neo4j",
    "redis",
    "qdrant_client",
    "slowapi",
]

# ── 收集数据文件 ────────────────────────────────────
datas = []

# .env 模板
env_example = PROJECT_ROOT / ".env.example"
if env_example.exists():
    datas.append((str(env_example), "."))

# data 目录
data_dir = PROJECT_ROOT / "data"
if data_dir.exists():
    datas.append((str(data_dir), "data"))

# ── Spec 定义 ────────────────────────────────────────
a = Analysis(
    [str(PROJECT_ROOT / "kunlun_cli.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="kunlun",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # CLI 工具需要控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / "icon.ico") if (PROJECT_ROOT / "icon.ico").exists() else None,
)