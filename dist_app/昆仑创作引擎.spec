# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/Users/hhj/OneDrive/Desktop/昆仑最新版/dist_app/launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/Users/hhj/OneDrive/Desktop/昆仑最新版/dist_app/kunlun', 'kunlun'), ('C:/Users/hhj/OneDrive/Desktop/昆仑最新版/dist_app/static', 'static'), ('C:/Users/hhj/OneDrive/Desktop/昆仑最新版/dist_app/web', 'web'), ('C:/Users/hhj/OneDrive/Desktop/昆仑最新版/dist_app/skills', 'skills'), ('C:/Users/hhj/OneDrive/Desktop/昆仑最新版/dist_app/data', 'data')],
    hiddenimports=['uvicorn', 'fastapi', 'kunlun', 'kunlun.api', 'kunlun.api.main', 'kunlun.api.routes', 'kunlun.kg', 'kunlun.kg.client', 'kunlun.audit', 'kunlun.agents', 'kunlun.gacha', 'kunlun.style'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'torchgen', 'functorch', 'tensorflow', 'tensorboard', 'keras', 'transformers', 'tokenizers', 'safetensors', 'sentence_transformers', 'huggingface_hub', 'hf_xet', 'datasets', 'pyarrow', 'dill', 'multiprocess', 'xxhash', 'narwhals', 'modelscope', 'modelscope_hub', 'peft', 'trl', 'accelerate', 'bitsandbytes', 'triton', 'nvidia', 'cuda', 'cudnn', 'scipy', 'scikit-learn', 'sklearn', 'pandas', 'matplotlib', 'seaborn', 'plotly', 'sympy', 'mpmath', 'joblib', 'threadpoolctl', 'numexpr', 'numba', 'llvmlite', 'PIL', 'cv2', 'imageio', 'skimage', 'pytest', '_pytest', 'pytest_asyncio', 'pytest_cov', 'hypothesis', 'coverage', 'ruff', 'mypy', 'mypy_extensions', 'bandit', 'black', 'isort', 'flake8', 'pre_commit', 'identify', 'cfgv', 'virtualenv', 'distlib', 'sphinx', 'docutils', 'IPython', 'ipykernel', 'jupyter_client', 'jupyter_core', 'nbformat', 'nbconvert', 'notebook', 'jupyter', 'ipywidgets', 'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'wx', 'wxPython', 'kivy', 'pymysql', 'psycopg2', 'psycopg', 'cx_Oracle', 'oracledb', 'pymssql', 'pymongo', 'cassandra', 'django', 'flask', 'bottle', 'tornado', 'aiohttp', 'nats', 'pika', 'celery', 'rq', 'boto3', 'botocore', 's3transfer', 'azure', 'google.cloud', 'weasyprint', 'pydub', 'edge_tts', 'pystray', 'prometheus_client', 'prometheus_fastapi_instrumentator', 'opentelemetry', 'grpcio_tools', 'grpc_tools', 'setuptools', 'pip', 'wheel', 'distutils', 'pkg_resources'],
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
    name='昆仑创作引擎',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'vcruntime140_1.dll', 'vcruntime140_threads.dll', 'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll', 'msvcp140_atomic_wait.dll', 'msvcp140_codecvt_ids.dll', 'python311.dll', 'python312.dll', 'python3.dll', 'ucrtbase.dll', 'kernel32.dll', 'user32.dll', 'gdi32.dll', 'advapi32.dll', 'shell32.dll', 'ole32.dll', 'oleaut32.dll', 'comctl32.dll', 'comdlg32.dll', 'shlwapi.dll', 'ws2_32.dll', 'winmm.dll', 'version.dll', 'imm32.dll', 'win32u.dll', 'gdi32full.dll', 'msvcp_win.dll', 'ntdll.dll', 'kernelbase.dll', 'bcrypt.dll', 'bcryptprimitives.dll', 'cfgmgr32.dll', 'powrprof.dll', 'profapi.dll', 'rpcrt4.dll', 'sechost.dll', 'shcore.dll', 'uxtheme.dll', 'wintrust.dll', 'msasn1.dll', 'crypt32.dll', 'cryptbase.dll', 'sspicli.dll', 'clbcatq.dll', 'd3d11.dll', 'dxgi.dll', 'dcomp.dll', 'dwmapi.dll', 'wtsapi32.dll', 'netapi32.dll', 'userenv.dll', 'propsys.dll', 'clr.dll', 'mscorlib.dll', 'mscoree.dll', 'mscoreei.dll', 'System.Data.dll', 'System.dll', 'System.Drawing.dll', 'System.Windows.Forms.dll', 'System.Xml.dll', 'System.Core.dll', 'WebView2Loader.dll'],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
