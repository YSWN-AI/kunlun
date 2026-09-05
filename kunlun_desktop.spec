# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — 昆仑创作引擎 桌面版 (pywebview + FastAPI)
用法:
    venv\\Scripts\\python.exe -m PyInstaller --clean kunlun_desktop.spec
    输出: dist/昆仑创作引擎/

优化记录 (P2):
    - 启用 UPX 5.2.1 压缩
    - 扩展排除列表（ML框架/数据科学/开发工具/未使用库）
    - 配置 upx_exclude 避免系统DLL压缩失败
    - numpy 保留（kg/embedder 运行时依赖）
    - sentence_transformers 排除（延迟导入，有 hash 向量降级）
"""

import sys
import os
import shutil
from pathlib import Path

# ── 项目根目录 ──────────────────────────────────────
PROJECT_ROOT = Path(os.getcwd()).resolve()

# ── UPX 路径自动探测 ────────────────────────────────
UPX_DIR = None
# 1. 项目内置 tools/upx
_candidates = [
    PROJECT_ROOT / "tools" / "upx" / "upx-5.2.1-win64",
    PROJECT_ROOT / "tools" / "upx",
]
for _cand in _candidates:
    _upx_exe = _cand / "upx.exe"
    if _upx_exe.exists():
        UPX_DIR = str(_cand)
        break
# 2. 系统 PATH
if UPX_DIR is None:
    _which = shutil.which("upx")
    if _which:
        UPX_DIR = str(Path(_which).parent)

if UPX_DIR:
    print(f"[spec] UPX found: {UPX_DIR}")
else:
    print("[spec] WARNING: UPX not found, compression disabled")

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

# 第三方依赖（运行时必需）
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
    "pydantic_core",
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
    "limits",
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
    "clr_loader",
    # 数据库 / 图谱
    "sqlalchemy",
    "alembic",
    "neo4j",
    "redis",
    "qdrant_client",
    "grpc",
    "grpc_reflection",
    "protobuf",
    "google.protobuf",
    # LLM SDK
    "openai",
    "anthropic",
    "distro",
    # 导出
    "ebooklib",
    "lxml",
    "docx",
    "Jinja2",
    "markupsafe",
    # 工具
    "tzlocal",
    "colorama",
    "click",
    "typing_extensions",
    "annotated_types",
    "mdurl",
    "fs",
    "proxy_tools",
    "psutil",
    "tqdm",
    "requests",
    "urllib3",
    "certifi",
    "charset_normalizer",
    "idna",
    "sniffio",
    "h2",
    "hpack",
    "hyperframe",
    "wrapt",
    "deprecated",
    "portalocker",
    "pywin32",
    "win32_setctime",
    "six",
    "python_dateutil",
    "pytz",
    "tzdata",
    "packaging",
    "platformdirs",
    "filelock",
    "fsspec",
    "cryptography",
    "cffi",
    "pycparser",
    "Pygments",
    "markdown_it",
    "shellingham",
    "typer",
    "docstring_parser",
    "ast_serialize",
    "annotated_doc",
    "typing_inspection",
    "jiter",
    "propcache",
    "httptools",
    "uvloop",
    "watchfiles",
    "aiohappyeyeballs",
    "aiosignal",
    "frozenlist",
    "multidict",
    "yarl",
    "attrs",
    "iniconfig",
    "pluggy",
    "pathspec",
    "nodeenv",
    "stevedore",
    "pbr",
    "Mako",
    "librt",
    "networkx",
]

# ── 排除列表（按类别） ──────────────────────────────
# 注意：numpy 保留（kg/embedder 运行时依赖 np.zeros/np.random/np.linalg）
excluded_modules = [
    # === ML / 深度学习框架（仅 finetune/ 模块使用，桌面端用外部 LLM API）===
    "torch",
    "torchvision",
    "torchaudio",
    "torchgen",
    "functorch",
    "tensorflow",
    "tensorboard",
    "keras",
    # === HuggingFace 生态（sentence_transformers 延迟导入，有 hash 降级）===
    "transformers",
    "tokenizers",
    "safetensors",
    "sentence_transformers",
    "huggingface_hub",
    "hf_xet",
    "datasets",
    "pyarrow",
    "dill",
    "multiprocess",
    "xxhash",
    "narwhals",
    "modelscope",
    "modelscope_hub",
    # === PEFT / 微调工具 ===
    "peft",
    "trl",
    "accelerate",
    "bitsandbytes",
    "triton",
    # === NVIDIA CUDA 运行时（torch 附带，排除 torch 后无需）===
    "nvidia",
    "cuda",
    "cudnn",
    # === 数据科学（运行时不使用）===
    "scipy",
    "scikit-learn",
    "sklearn",
    "pandas",
    "matplotlib",
    "seaborn",
    "plotly",
    "sympy",
    "mpmath",
    "joblib",
    "threadpoolctl",
    "numexpr",
    "bottleneck",
    "numba",
    "llvmlite",
    # === 图像处理（仅 desktop_app.py 系统托盘使用，非主流程）===
    "PIL",
    "cv2",
    "imageio",
    "skimage",
    # === 测试框架 ===
    "pytest",
    "_pytest",
    "pytest_asyncio",
    "pytest_cov",
    "hypothesis",
    "coverage",
    "unittest.mock",
    # === 代码质量 / 开发工具 ===
    "ruff",
    "mypy",
    "mypy_extensions",
    "bandit",
    "black",
    "isort",
    "flake8",
    "pycodestyle",
    "pyflakes",
    "mccabe",
    "pre_commit",
    "identify",
    "cfgv",
    "virtualenv",
    "distlib",
    # === 文档工具 ===
    "sphinx",
    "docutils",
    "recommonmark",
    # === Jupyter / Notebook ===
    "IPython",
    "ipykernel",
    "jupyter_client",
    "jupyter_core",
    "nbformat",
    "nbconvert",
    "notebook",
    "jupyter",
    "ipywidgets",
    # === 未使用的 GUI 框架 ===
    "tkinter",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "wx",
    "wxPython",
    "kivy",
    # === 未使用的数据库驱动 ===
    "pymysql",
    "psycopg2",
    "psycopg",
    "cx_Oracle",
    "oracledb",
    "pymssql",
    "mongodb",
    "pymongo",
    "cassandra",
    # === 未使用的 Web 框架 ===
    "django",
    "flask",
    "bottle",
    "tornado",
    "aiohttp",
    # === 未使用的消息队列 ===
    "nats",
    "pika",
    "celery",
    "rq",
    # === 未使用的云 SDK ===
    "boto3",
    "botocore",
    "s3transfer",
    "azure",
    "google.cloud",
    # === 其他未使用 ===
    "weasyprint",
    "pydub",
    "edge_tts",
    "pystray",
    "prometheus_client",
    "prometheus_fastapi_instrumentator",
    "opentelemetry",
    "grpcio_tools",
    "grpc_tools",
    "setuptools",
    "pip",
    "wheel",
    "pkg_resources",
]

# ── UPX 排除列表（不能被 UPX 压缩的 DLL）────────────
upx_exclude = [
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "vcruntime140_threads.dll",
    "msvcp140.dll",
    "msvcp140_1.dll",
    "msvcp140_2.dll",
    "msvcp140_atomic_wait.dll",
    "msvcp140_codecvt_ids.dll",
    "python311.dll",
    "python312.dll",
    "python3.dll",
    "api-ms-win-core-libraryloader-l1-1-0.dll",
    "api-ms-win-core-processthreads-l1-1-0.dll",
    "api-ms-win-core-heap-l1-1-0.dll",
    "api-ms-win-core-memory-l1-1-0.dll",
    "api-ms-win-core-synch-l1-1-0.dll",
    "api-ms-win-core-synch-l1-2-0.dll",
    "api-ms-win-core-handle-l1-1-0.dll",
    "api-ms-win-core-file-l1-1-0.dll",
    "api-ms-win-core-file-l1-2-0.dll",
    "api-ms-win-core-io-l1-1-0.dll",
    "api-ms-win-core-realtime-l1-1-0.dll",
    "api-ms-win-core-sysinfo-l1-1-0.dll",
    "api-ms-win-core-timezone-l1-1-0.dll",
    "api-ms-win-core-localization-l1-2-0.dll",
    "api-ms-win-core-debug-l1-1-0.dll",
    "api-ms-win-core-errorhandling-l1-1-0.dll",
    "api-ms-win-core-profile-l1-1-0.dll",
    "api-ms-win-core-string-l1-1-0.dll",
    "api-ms-win-core-util-l1-1-0.dll",
    "api-ms-win-core-interlocked-l1-1-0.dll",
    "api-ms-win-core-delayload-l1-1-1.dll",
    "api-ms-win-core-winrt-l1-1-0.dll",
    "api-ms-win-core-winrt-string-l1-1-0.dll",
    "api-ms-win-core-com-l1-1-0.dll",
    "api-ms-win-core-registry-l1-1-0.dll",
    "api-ms-win-core-threadpool-l1-2-0.dll",
    "api-ms-win-core-libraryloader-l1-2-0.dll",
    "api-ms-win-core-kernel32-legacy-l1-1-0.dll",
    "api-ms-win-security-base-l1-1-0.dll",
    "api-ms-win-security-cryptoapi-l1-1-0.dll",
    "api-ms-win-crt-runtime-l1-1-0.dll",
    "api-ms-win-crt-string-l1-1-0.dll",
    "api-ms-win-crt-heap-l1-1-0.dll",
    "api-ms-win-crt-stdio-l1-1-0.dll",
    "api-ms-win-crt-filesystem-l1-1-0.dll",
    "api-ms-win-crt-time-l1-1-0.dll",
    "api-ms-win-crt-utility-l1-1-0.dll",
    "api-ms-win-crt-environment-l1-1-0.dll",
    "api-ms-win-crt-math-l1-1-0.dll",
    "api-ms-win-crt-multibyte-l1-1-0.dll",
    "api-ms-win-crt-locale-l1-1-0.dll",
    "api-ms-win-crt-convert-l1-1-0.dll",
    "api-ms-win-crt-process-l1-1-0.dll",
    "api-ms-win-crt-conio-l1-1-0.dll",
    "api-ms-win-crt-telemetry-l1-1-0.dll",
    "ucrtbase.dll",
    "kernel32.dll",
    "user32.dll",
    "gdi32.dll",
    "advapi32.dll",
    "shell32.dll",
    "ole32.dll",
    "oleaut32.dll",
    "comctl32.dll",
    "comdlg32.dll",
    "shlwapi.dll",
    "ws2_32.dll",
    "winmm.dll",
    "version.dll",
    "imm32.dll",
    "win32u.dll",
    "gdi32full.dll",
    "msvcp_win.dll",
    "ntdll.dll",
    "kernelbase.dll",
    "bcrypt.dll",
    "bcryptprimitives.dll",
    "cfgmgr32.dll",
    "powrprof.dll",
    "profapi.dll",
    "rpcrt4.dll",
    "sechost.dll",
    "shcore.dll",
    "uxtheme.dll",
    "wintrust.dll",
    "msasn1.dll",
    "crypt32.dll",
    "cryptbase.dll",
    "sspicli.dll",
    "clbcatq.dll",
    "resampledmo.dll",
    "mfplat.dll",
    "mf.dll",
    "mfreadwrite.dll",
    "d3d11.dll",
    "dxgi.dll",
    "dcomp.dll",
    "dwmapi.dll",
    "wtsapi32.dll",
    "netapi32.dll",
    "userenv.dll",
    "propsys.dll",
    "windows.storage.dll",
    "windows.ui.dll",
    "edgehtml.dll",
    "internetexplorerframe.dll",
    "iertutil.dll",
    "mshtml.dll",
    "jscript.dll",
    "vbscript.dll",
    "clr.dll",
    "mscorlib.dll",
    "mscoree.dll",
    "mscoreei.dll",
    "mscorrc.dll",
    "System.Data.dll",
    "System.dll",
    "System.Drawing.dll",
    "System.Windows.Forms.dll",
    "System.Xml.dll",
    "System.Core.dll",
    "System.Configuration.dll",
    "WebView2Loader.dll",
]

# ── 收集数据文件 ────────────────────────────────────
datas = []

# web UI（创作工作台前端）
web_dir = PROJECT_ROOT / "web"
if web_dir.is_dir():
    datas.append((str(web_dir), "web"))

# frontend dist（Vue 构建产物）
frontend_dist = PROJECT_ROOT / "frontend" / "dist"
if frontend_dist.is_dir():
    datas.append((str(frontend_dist), "static"))

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
    upx=UPX_DIR is not None,
    upx_exclude=upx_exclude,
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
    upx=UPX_DIR is not None,
    upx_exclude=upx_exclude,
    name="昆仑创作引擎",
)
