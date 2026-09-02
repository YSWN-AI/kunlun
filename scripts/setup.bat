@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

:: ============================================================
::  昆仑创作引擎 — 一键安装部署脚本
::  用法: 双击运行，自动完成环境安装和配置
:: ============================================================

set "INSTALL_DIR=%~dp0.."
set "APP_NAME=昆仑创作引擎"
set "DESKTOP_DIR=%USERPROFILE%\Desktop"

echo.
echo   ╔══════════════════════════════════════════════════════╗
echo   ║      昆仑创作引擎 Kunlun Creation Engine            ║
echo   ║      一键安装脚本                                    ║
echo   ╚══════════════════════════════════════════════════════╝
echo.

:: ─── 1. 检查 Python 3.10+ ──────────────────────────
echo  [1/7] 检查 Python 环境...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [X] 未检测到 Python，请安装 Python 3.10+
    echo  下载地址: https://www.python.org/downloads/
    echo  安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [X] Python 版本过低 ^(!PYVER!^)，需要 3.10+
    pause
    exit /b 1
)
echo  [√] Python !PYVER!

:: ─── 2. 检查 Java (Neo4j 依赖) ──────────────────────────
echo  [2/7] 检查 Java 环境...
where java >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] 未检测到 Java Runtime，Neo4j 需要 Java 11+
    echo  下载地址: https://adoptium.net/download/
    set JAVA_WARN=1
) else (
    for /f "tokens=3" %%j in ('java -version 2^>^&1 ^| findstr /i "version"') do set JVER=%%j
    echo  [√] Java !JVER!
)

:: ─── 3. 创建虚拟环境 ──────────────────────────
echo  [3/7] 创建 Python 虚拟环境...
cd /d "!INSTALL_DIR!"
if not exist "venv" (
    python -m venv venv
    echo  [√] 虚拟环境已创建
) else (
    echo  [√] 虚拟环境已存在，跳过
)

:: ─── 4. 安装 Python 依赖 ──────────────────────────
echo  [4/7] 安装 Python 依赖包...
call venv\Scripts\activate.bat
echo  正在安装，这可能需要几分钟...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
if %errorlevel% neq 0 (
    echo  [!] 国内镜像安装失败，尝试默认源...
    pip install -r requirements.txt
)
echo  [√] Python 依赖安装完成

:: ─── 5. 配置文件 ──────────────────────────
echo  [5/7] 初始化配置文件...
if not exist ".env" (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
        echo  [√] 已从 .env.example 创建 .env
        echo  请用文本编辑器打开 .env 填入你的 API Key
    ) else (
        echo  [!] .env.example 不存在，请手动创建 .env
    )
) else (
    echo  [√] .env 已存在，保留现有配置
)

:: ─── 6. 数据目录 ──────────────────────────
echo  [6/7] 初始化数据目录...
if not exist "data" mkdir data
if not exist "data\qdrant" mkdir data\qdrant
if not exist "data\logs" mkdir data\logs
if not exist "data\export" mkdir data\export
if not exist "data\published" mkdir data\published
if not exist "data\learn" mkdir data\learn
if not exist "data\snapshots" mkdir data\snapshots
echo  [√] 数据目录就绪

:: ─── 7. 可选服务检查 ──────────────────────────
echo  [7/7] 检查可选服务...
where redis-server >nul 2>&1 && echo  [√] Redis 可用 || echo  [!] Redis 未安装 ^(可选，引擎内置降级^)
where nats-server >nul 2>&1 && echo  [√] NATS 可用 || echo  [!] NATS 未安装 ^(可选，引擎内置降级^)

:: ─── 创建桌面快捷方式 ──────────────────────────
echo.
echo  创建桌面快捷方式...
set "SHORTCUT=!DESKTOP_DIR!\!APP_NAME!.lnk"
set "BATCH_FILE=!INSTALL_DIR!\start.bat"
set "ICON_FILE=!INSTALL_DIR!\kunlun_icon.ico"

powershell -NoProfile -Command ^
"$ws = New-Object -ComObject WScript.Shell; ^
$sc = $ws.CreateShortcut('%SHORTCUT%'); ^
$sc.TargetPath = '%BATCH_FILE%'; ^
$sc.WorkingDirectory = '%INSTALL_DIR%'; ^
$sc.Description = '昆仑创作引擎 - AI辅助网文创作'; ^
$sc.WindowStyle = 7; ^
if (Test-Path '%ICON_FILE%') { $sc.IconLocation = '%ICON_FILE%' }; ^
$sc.Save()"
if %errorlevel% equ 0 (
    echo  [√] 桌面快捷方式已创建
) else (
    echo  [!] 快捷方式创建失败，可运行 scripts\shortcut.bat 手动创建
)

:: ─── Neo4j 提示 ──────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║              重要: Neo4j 数据库                     ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  昆仑引擎需要 Neo4j 图数据库来存储知识图谱。
echo  下载地址: https://neo4j.com/download-center/#community
echo.
echo  安装后设置:
echo   1. 创建本地数据库，默认密码设为: kunlun2024
echo   2. 确保 Neo4j 服务运行在 bolt://localhost:7687
echo   3. 在 .env 中检查 NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD
echo.
if defined JAVA_WARN (
    echo  [!] 提醒: 你还需要安装 Java 11+ 才能运行 Neo4j
    echo.
)
echo  如果无法安装 Neo4j，引擎会自动降级为 SQLite 模式运行。
echo.
echo  可选服务 (非必须，引擎内置降级):
echo   - Docker Desktop: 一键启动所有服务 ^(scripts\start-services.bat^)
echo   - Redis: https://github.com/tporadowski/redis/releases
echo   - NATS:  https://github.com/nats-io/nats-server/releases
echo.

echo  ╔══════════════════════════════════════════════════════╗
echo  ║              安装完成!                              ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  启动方式:
echo   1. 双击桌面上的 "昆仑创作引擎" 快捷方式
echo   2. 或运行根目录的 start.bat
echo   3. 启动后浏览器会自动打开 http://localhost:8000
echo.
pause
