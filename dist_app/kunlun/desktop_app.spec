# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — 打包昆仑创作引擎桌面 GUI 版
windowed 模式，无控制台窗口

用法:
  pyinstaller --clean kunlun/desktop_app.spec
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent  # 项目根目录
sys.path.insert(0, str(_project_root))

a = Analysis(
    [str(_project_root / "kunlun" / "desktop_app.py")],
    pathex=[str(_project_root)],
    binaries=[],
    datas=[
        # 前端 dist 目录
        (
            str(_project_root / "frontend" / "dist"),
            "frontend/dist",
        ),
        # web 静态目录（降级 UI）
        (
            str(_project_root / "web"),
            "web",
        ),
        # .env 配置文件
        (
            str(_project_root / ".env"),
            ".",
        ),
        # 数据目录（种子数据等）
        (
            str(_project_root / "data"),
            "data",
        ),
    ],
    hiddenimports=[
        "kunlun",
        "kunlun.config",
        "kunlun.api",
        "kunlun.api.main",
        "kunlun.api.routes",
        "kunlun.api.routes_health",
        "kunlun.api.routers",
        "kunlun.api.routers.stream",
        "kunlun.api.routers.admin",
        "kunlun.api.error_handlers",
        "kunlun.agents",
        "kunlun.agents.editor",
        "kunlun.kg",
        "kunlun.kg.client",
        "kunlun.kg.seed_data",
        "kunlun.recovery",
        "kunlun.recovery.rollback",
        "kunlun.audit",
        "kunlun.audit.audit33",
        "kunlun.audit.ai_features",
        "kunlun.audit.output_contract",
        "kunlun.audit.fanqie_gates",
        "kunlun.style",
        "kunlun.style.fingerprint",
        "kunlun.style.refiner",
        "kunlun.gacha",
        "kunlun.gacha.param_variator",
        "kunlun.observability",
        "kunlun.autosync",
        "kunlun.safety",
        "kunlun.safety.validators",
        "kunlun.skills",
        "kunlun.skills.skill_loader",
        "kunlun.token_tracker",
        "kunlun.model_router",
        "kunlun.import_engine",
        "kunlun.daemon",
        "kunlun.doctor",
        "kunlun.status_cmd",
        "kunlun.setup_local",
        "kunlun.quality",
        "kunlun.monetize",
        "kunlun.marketplace",
        "kunlun.finetune",
        "kunlun.analytics",
        "kunlun.writer_context",
        "kunlun.tts",
        "kunlun.image_gen",
        # 第三方依赖
        "fastapi",
        "uvicorn",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "starlette",
        "pydantic",
        "pydantic_settings",
        "loguru",
        "sqlalchemy",
        "alembic",
        "redis",
        "httpx",
        "aiohttp",
        "aiofiles",
        "python_multipart",
        "prometheus_fastapi_instrumentator",
        "slowapi",
        "PIL",
        "pystray",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter.test",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "torch",
        "tensorflow",
        "jupyter",
        "IPython",
        "notebook",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="昆仑创作引擎",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # windowed 模式，无控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(_project_root / "kunlun" / "desktop_app.py"),  # 临时，可替换为 .ico 文件
    uac_admin=False,
)