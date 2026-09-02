@echo off
chcp 65001 >nul
title Kunlun Engine - Setup & Run

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

set "VENV_DIR=%PROJECT_DIR%\venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"
set "UVICORN_EXE=%VENV_DIR%\Scripts\uvicorn.exe"
set "REQUIREMENTS_FILE=%PROJECT_DIR%\requirements.txt"

set "SERVER_HOST=127.0.0.1"
set "SERVER_PORT=8000"
set "SERVER_URL=http://%SERVER_HOST%:%SERVER_PORT%"

cls
echo ========================================
echo    昆仑创作引擎 - 启动器 v1.0
echo ========================================
echo.

:: 检查Python安装
echo [CHECK] 检测Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到Python，请先安装Python 3.11+
    echo         下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 获取Python版本
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%v"
echo [OK] Python版本: %PYTHON_VERSION%

:: 检查虚拟环境
echo.
echo [CHECK] 检查虚拟环境...
if not exist "%VENV_DIR%" (
    echo [CREATE] 创建虚拟环境...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo [OK] 虚拟环境创建成功
) else (
    echo [OK] 虚拟环境已存在
)

:: 升级pip
echo.
echo [UPGRADE] 升级pip...
"%PYTHON_EXE%" -m pip install --upgrade pip >nul 2>&1
echo [OK] pip已升级

:: 安装依赖
echo.
echo [INSTALL] 安装依赖包...
if not exist "%REQUIREMENTS_FILE%" (
    echo [ERROR] 未找到requirements.txt
    pause
    exit /b 1
)

"%PIP_EXE%" install -r "%REQUIREMENTS_FILE%"
if errorlevel 1 (
    echo.
    echo [WARN] 部分依赖安装失败，尝试使用镜像源...
    "%PIP_EXE%" install -r "%REQUIREMENTS_FILE%" -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [ERROR] 依赖安装失败
        echo        请手动运行: pip install -r requirements.txt
        pause
        exit /b 1
    )
)
echo [OK] 依赖安装完成

:: 检查端口占用
echo.
echo [CHECK] 检查端口 %SERVER_PORT%...
netstat -ano | findstr ":%SERVER_PORT%" >nul
if not errorlevel 1 (
    echo [WARN] 端口 %SERVER_PORT% 已被占用，尝试终止占用进程...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%SERVER_PORT%"') do (
        taskkill /f /pid %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
)
echo [OK] 端口可用

:: 启动后端服务
echo.
echo [START] 启动昆仑引擎后端服务...
echo         服务地址: %SERVER_URL%
start /b "%UVICORN_EXE%" kunlun.api.main:app --host %SERVER_HOST% --port %SERVER_PORT% --workers 1

:: 等待服务启动
echo.
echo [WAIT] 等待服务启动...
set "MAX_WAIT=30"
set "WAIT_COUNT=0"
:WAIT_LOOP
timeout /t 1 /nobreak >nul
curl -s "%SERVER_URL%/health" >nul 2>&1
if not errorlevel 1 (
    goto SERVICE_STARTED
)
set /a WAIT_COUNT+=1
if %WAIT_COUNT% lss %MAX_WAIT% (
    set /a REMAINING=MAX_WAIT-WAIT_COUNT
    echo       等待中 (%REMAINING%s)...
    goto WAIT_LOOP
)
echo [WARN] 服务启动超时，继续尝试打开浏览器...
goto OPEN_BROWSER

:SERVICE_STARTED
echo [OK] 服务启动成功

:OPEN_BROWSER
:: 打开浏览器
echo.
echo [OPEN] 打开浏览器...
start "%SERVER_URL%"

:: 显示成功信息
echo.
echo ========================================
echo           昆仑引擎启动成功!
echo ========================================
echo.
echo   服务地址: %SERVER_URL%
echo.
echo   关闭此窗口将停止服务
echo ========================================
echo.

:: 保持窗口打开并监控服务
:MONITOR
timeout /t 5 /nobreak >nul
tasklist | findstr "uvicorn.exe" >nul
if errorlevel 1 (
    echo.
    echo [INFO] 服务已停止
    pause
    exit /b 0
)
goto MONITOR
