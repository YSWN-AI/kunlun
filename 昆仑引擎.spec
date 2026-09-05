# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — 昆仑创作引擎 (launcher 版，窗口模式)
用法:
    venv\\Scripts\\python.exe -m PyInstaller --clean 昆仑引擎.spec
    输出: dist/昆仑引擎/

优化记录 (P2):
    - 补充全面排除列表（原 excludes=[]）
    - 配置 upx_exclude 避免系统DLL压缩失败
    - 补充 hidden_imports
    - data 目录不打包（运行时自动创建）
    - numpy 保留（kg/embedder 运行时依赖）
"""

import sys
import os
import shutil
from pathlib import Path

# ── 项目根目录 ──────────────────────────────────────
PROJECT_ROOT = Path(os.getcwd()).resolve()

# ── UPX 路径自动探测 ────────────────────────────────
UPX_DIR = None
_candidates = [
    PROJECT_ROOT / "tools" / "upx" / "upx-5.2.1-win64",
    PROJECT_ROOT / "tools" / "upx",
]
for _cand in _candidates:
    _upx_exe = _cand / "upx.exe"
    if _upx_exe.exists():
        UPX_DIR = str(_cand)
        break
if UPX_DIR is None:
    _which = shutil.which("upx")
    if _which:
        UPX_DIR = str(Path(_which).parent)

# ── 收集 kunlun 子包 ────────────────────────────────
kunlun_dir = PROJECT_ROOT / "kunlun"
hidden_imports = []
for py_file in sorted(kunlun_dir.rglob("*.py")):
    if py_file.name.startswith("_"):
        continue
    rel = py_file.relative_to(PROJECT_ROOT).with_suffix("")
    module_name = str(rel).replace("\\", ".").replace("/", ".")
    hidden_imports.append(module_name)

# 第三方运行时依赖
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
    "sqlalchemy",
    "alembic",
    "neo4j",
    "redis",
    "qdrant_client",
    "grpc",
    "protobuf",
    "google.protobuf",
    "openai",
    "anthropic",
    "distro",
    "ebooklib",
    "lxml",
    "docx",
    "Jinja2",
    "markupsafe",
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
    "stevedore",
    "Mako",
    "networkx",
    "webview",
    "webview.platforms",
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    "clr",
    "pythonnet",
    "clr_loader",
]

# ── 排除列表 ────────────────────────────────────────
excluded_modules = [
    # ML / 深度学习
    "torch", "torchvision", "torchaudio", "torchgen", "functorch",
    "tensorflow", "tensorboard", "keras",
    # HuggingFace 生态
    "transformers", "tokenizers", "safetensors", "sentence_transformers",
    "huggingface_hub", "hf_xet", "datasets", "pyarrow",
    "dill", "multiprocess", "xxhash", "narwhals",
    "modelscope", "modelscope_hub",
    # PEFT / 微调
    "peft", "trl", "accelerate", "bitsandbytes", "triton",
    # NVIDIA CUDA
    "nvidia", "cuda", "cudnn",
    # 数据科学
    "scipy", "scikit-learn", "sklearn", "pandas",
    "matplotlib", "seaborn", "plotly", "sympy", "mpmath",
    "joblib", "threadpoolctl", "numexpr", "numba", "llvmlite",
    # 图像处理
    "PIL", "cv2", "imageio", "skimage",
    # 测试框架
    "pytest", "_pytest", "pytest_asyncio", "pytest_cov",
    "hypothesis", "coverage",
    # 开发工具
    "ruff", "mypy", "mypy_extensions", "bandit",
    "black", "isort", "flake8", "pre_commit",
    "identify", "cfgv", "virtualenv", "distlib",
    # 文档
    "sphinx", "docutils",
    # Jupyter
    "IPython", "ipykernel", "jupyter_client", "jupyter_core",
    "nbformat", "nbconvert", "notebook", "jupyter", "ipywidgets",
    # GUI 框架
    "tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6",
    "wx", "wxPython", "kivy",
    # 数据库驱动
    "pymysql", "psycopg2", "psycopg", "cx_Oracle", "oracledb",
    "pymssql", "pymongo", "cassandra",
    # Web 框架
    "django", "flask", "bottle", "tornado", "aiohttp",
    # 消息队列
    "nats", "pika", "celery", "rq",
    # 云 SDK
    "boto3", "botocore", "s3transfer", "azure", "google.cloud",
    # 其他未使用
    "weasyprint", "pydub", "edge_tts", "pystray",
    "prometheus_client", "prometheus_fastapi_instrumentator",
    "opentelemetry", "grpcio_tools", "grpc_tools",
    "setuptools", "pip", "wheel", "distutils", "pkg_resources",
]

# ── UPX 排除列表 ────────────────────────────────────
upx_exclude = [
    "vcruntime140.dll", "vcruntime140_1.dll", "vcruntime140_threads.dll",
    "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll",
    "msvcp140_atomic_wait.dll", "msvcp140_codecvt_ids.dll",
    "python311.dll", "python312.dll", "python3.dll",
    "ucrtbase.dll", "kernel32.dll", "user32.dll", "gdi32.dll",
    "advapi32.dll", "shell32.dll", "ole32.dll", "oleaut32.dll",
    "comctl32.dll", "comdlg32.dll", "shlwapi.dll", "ws2_32.dll",
    "winmm.dll", "version.dll", "imm32.dll", "win32u.dll",
    "gdi32full.dll", "msvcp_win.dll", "ntdll.dll", "kernelbase.dll",
    "bcrypt.dll", "bcryptprimitives.dll", "cfgmgr32.dll",
    "powrprof.dll", "profapi.dll", "rpcrt4.dll", "sechost.dll",
    "shcore.dll", "uxtheme.dll", "wintrust.dll", "msasn1.dll",
    "crypt32.dll", "cryptbase.dll", "sspicli.dll", "clbcatq.dll",
    "d3d11.dll", "dxgi.dll", "dcomp.dll", "dwmapi.dll",
    "wtsapi32.dll", "netapi32.dll", "userenv.dll", "propsys.dll",
    "clr.dll", "mscorlib.dll", "mscoree.dll", "mscoreei.dll",
    "System.Data.dll", "System.dll", "System.Drawing.dll",
    "System.Windows.Forms.dll", "System.Xml.dll", "System.Core.dll",
    "WebView2Loader.dll",
]

# ── 数据文件 ────────────────────────────────────────
datas = []

# kunlun 包（作为数据文件，确保非 .py 资源也被打包）
datas.append((str(PROJECT_ROOT / "kunlun"), "kunlun"))

# web UI
web_dir = PROJECT_ROOT / "web"
if web_dir.is_dir():
    datas.append((str(web_dir), "web"))

# frontend dist
frontend_dist = PROJECT_ROOT / "frontend" / "dist"
if frontend_dist.is_dir():
    datas.append((str(frontend_dist), "frontend/dist"))

# skills
skills_dir = PROJECT_ROOT / "skills"
if skills_dir.is_dir():
    datas.append((str(skills_dir), "skills"))

# .env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    datas.append((str(env_file), "."))

# .env.example
env_example = PROJECT_ROOT / ".env.example"
if env_example.exists():
    datas.append((str(env_example), "."))

# data 目录不打包（运行时自动创建）

# ── Spec 定义 ────────────────────────────────────────
a = Analysis(
    [str(PROJECT_ROOT / "launcher.py")],
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
    name="昆仑引擎",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=UPX_DIR is not None,
    upx_exclude=upx_exclude,
    console=False,
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
    name="昆仑引擎",
)
