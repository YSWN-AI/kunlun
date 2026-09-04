# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — 昆仑创作引擎 桌面版 (pywebview + FastAPI)
用法:
    venv\\Scripts\\python.exe -m PyInstaller --clean kunlun_desktop.spec
    输出: dist/昆仑创作引擎/
"""

import sys
import os
from pathlib import Path

# ── 项目根目录 ──────────────────────────────────────
PROJECT_ROOT = Path(os.getcwd()).resolve()

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

# 第三方依赖
hidden_imports += [
    "fastapi",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "pydantic",
    "pydantic_settings",
    "pydantic.deprecated.decorator",
    "loguru",
    "httpx",
    "jieba",
    "aiofiles",
    "yaml",
    "dotenv",
    "rich",
    "starlette",
    "starlette.middleware",
    "starlette.middleware.cors",
    "starlette.staticfiles",
    "websockets",
    "anyio",
    "anyio._backends._asyncio",
    "httpcore",
    "h11",
    "multipart",
    "python_multipart",
    "slowapi",
    # pywebview
    "webview",
    "webview.platforms",
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    "webview.platforms.mshtml",
    "webview.js",
    "webview.util",
    "webview.event",
    "webview.http",
    "webview.ws",
    "clr",
    "pythonnet",
    # 其他
    "tzlocal",
    "colorama",
    "click",
    "typing_extensions",
    "annotated_types",
    "mdurl",
    "fs",
    "proxy_tools",
]

# 排除大型非必要库（桌面端只用外部LLM API，不需要本地ML库）
# 注意：numpy 保留（kg/embedder等模块间接依赖）
excluded_modules = [
    "matplotlib", "scipy", "pandas", "PIL", "cv2",
    "tensorflow", "torch", "torchvision", "torchaudio",
    "sklearn", "scikit-learn",
    "sentence_transformers", "transformers", "tokenizers", "safetensors",
    "huggingface_hub", "hf_xet", "datasets", "pyarrow",
    "bitsandbytes", "triton", "nvidia", "cuda",
    "neo4j", "redis", "qdrant_client",
    "pytest", "IPython", "notebook", "jupyter",
    "fsspec",
]

# ── 收集数据文件 ────────────────────────────────────
datas = []

# web UI（创作工作台前端）
web_dir = PROJECT_ROOT / "web"
if web_dir.is_dir():
    datas.append((str(web_dir), "web"))

# skills
skills_dir = PROJECT_ROOT / "skills"
if skills_dir.is_dir():
    datas.append((str(skills_dir), "skills"))

# .env（含API Key，已gitignore但打包需要）
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    datas.append((str(env_file), "."))

# .env.example
env_example = PROJECT_ROOT / ".env.example"
if env_example.exists():
    datas.append((str(env_example), "."))

# data 目录不打包（含用户数据库/缓存，体积巨大）
# desktop.py 启动时自动创建所需的 data/ 子目录

# ── Spec 定义 ────────────────────────────────────────
a = Analysis(
    [str(PROJECT_ROOT / "desktop.py")],
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
    [],
    exclude_binaries=True,
    name="昆仑创作引擎",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="昆仑创作引擎",
)
