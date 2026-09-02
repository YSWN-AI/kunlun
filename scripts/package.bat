@echo off
chcp 65001 >nul
title Kunlun Engine - Package Builder v1.0

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

set "OUTPUT=%USERPROFILE%\Desktop\KunlunEngine"
set "ZIP_OUTPUT=%OUTPUT%.zip"

set "BUILD_ERROR=0"

cls
echo ========================================
echo    昆仑创作引擎 - 打包工具 v1.0
echo ========================================
echo.

:: 检查Node.js环境
echo [CHECK] 检测Node.js环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到Node.js，请先安装Node.js 18+
    echo         下载地址: https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('node --version 2^>^&1') do set "NODE_VERSION=%%v"
echo [OK] Node.js版本: %NODE_VERSION%

:: 清理旧输出
echo.
echo [CLEAN] 清理旧输出...
if exist "%OUTPUT%" (
    rd /s /q "%OUTPUT%"
    if errorlevel 1 (
        echo [WARN] 删除旧目录失败，可能正在使用
    )
)
if exist "%ZIP_OUTPUT%" (
    del "%ZIP_OUTPUT%"
)
echo [OK] 清理完成

:: 创建目录结构
echo.
echo [CREATE] 创建目录结构...
mkdir "%OUTPUT%\kunlun" 2>nul
mkdir "%OUTPUT%\frontend\dist" 2>nul
mkdir "%OUTPUT%\data\logs" 2>nul
mkdir "%OUTPUT%\data\memory" 2>nul
mkdir "%OUTPUT%\data\qdrant" 2>nul
echo [OK] 目录创建完成

:: 复制核心文件
echo.
echo [COPY] 复制核心文件...

echo        复制后端代码...
xcopy /E /I /Y /Q "%PROJECT_DIR%\kunlun" "%OUTPUT%\kunlun" >nul
if errorlevel 1 (
    echo [ERROR] 复制后端代码失败
    set "BUILD_ERROR=1"
)

:: 删除__pycache__目录
echo        清理缓存文件...
for /d /r "%OUTPUT%\kunlun" %%d in (__pycache__) do if exist "%%d" rd /s /q "%%d" 2>nul
for /d /r "%OUTPUT%\kunlun" %%d in (.pytest_cache) do if exist "%%d" rd /s /q "%%d" 2>nul
del /s /q "%OUTPUT%\kunlun\*.pyc" 2>nul

echo        复制前端资源...
if exist "%PROJECT_DIR%\frontend\dist" (
    xcopy /E /I /Y /Q "%PROJECT_DIR%\frontend\dist" "%OUTPUT%\frontend\dist" >nul
    if errorlevel 1 (
        echo [WARN] 复制前端资源失败，可能需要先构建前端
    )
) else (
    echo [WARN] 未找到前端构建目录: frontend\dist
    echo        请先运行: cd frontend && npm install && npm run build
)

echo        复制配置文件...
copy /Y "%PROJECT_DIR%\start.bat" "%OUTPUT%\start.bat" >nul
copy /Y "%PROJECT_DIR%\requirements.txt" "%OUTPUT%\requirements.txt" >nul
if exist "%PROJECT_DIR%\kunlun_icon.ico" (
    copy /Y "%PROJECT_DIR%\kunlun_icon.ico" "%OUTPUT%\kunlun_icon.ico" >nul
)

echo        复制README文件...
if exist "%PROJECT_DIR%\README.md" (
    copy /Y "%PROJECT_DIR%\README.md" "%OUTPUT%\README.md" >nul
)
echo [OK] 文件复制完成

:: 创建配置文件模板
echo.
echo [CONFIG] 创建配置文件...
set "CONFIG_FILE=%OUTPUT%\data\config.json"
echo { > "%CONFIG_FILE%"
echo   "api": { >> "%CONFIG_FILE%"
echo     "host": "127.0.0.1", >> "%CONFIG_FILE%"
echo     "port": 8000 >> "%CONFIG_FILE%"
echo   }, >> "%CONFIG_FILE%"
echo   "model": { >> "%CONFIG_FILE%"
echo     "provider": "openai_compat", >> "%CONFIG_FILE%"
echo     "api_base": "http://localhost:8000/v1", >> "%CONFIG_FILE%"
echo     "api_key": "your-api-key", >> "%CONFIG_FILE%"
echo     "default_model": "deepseek-chat" >> "%CONFIG_FILE%"
echo   }, >> "%CONFIG_FILE%"
echo   "logging": { >> "%CONFIG_FILE%"
echo     "level": "INFO", >> "%CONFIG_FILE%"
echo     "file": "data/logs/kunlun.log" >> "%CONFIG_FILE%"
echo   } >> "%CONFIG_FILE%"
echo } >> "%CONFIG_FILE%"
echo [OK] 配置文件创建完成

:: 生成版本信息
echo.
echo [INFO] 生成版本信息...
set "VERSION_FILE=%OUTPUT%\VERSION"
echo Kunlun Engine v0.1 > "%VERSION_FILE%"
echo Build: %date% %time% >> "%VERSION_FILE%"
echo [OK] 版本信息生成完成

:: 创建ZIP包
echo.
echo [ZIP] 创建压缩包...
powershell -NoProfile -Command "Compress-Archive -Path '%OUTPUT%' -DestinationPath '%ZIP_OUTPUT%' -Force" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 创建ZIP失败
    set "BUILD_ERROR=1"
) else (
    echo [OK] ZIP创建完成
)

:: 显示结果
echo.
if %BUILD_ERROR% equ 0 (
    echo ========================================
    echo              打包成功!
    echo ========================================
    echo.
    echo   输出文件: %ZIP_OUTPUT%
    echo.
    echo   目录结构:
    echo   ├── KunlunEngine/
    echo   │   ├── kunlun/          # 后端代码
    echo   │   ├── frontend/dist/   # 前端资源
    echo   │   ├── data/            # 数据目录
    echo   │   ├── start.bat        # 启动脚本
    echo   │   └── requirements.txt # 依赖列表
    echo.
    echo   使用方法:
    echo   1. 删除桌面上旧的 KunlunEngine 文件夹
    echo   2. 解压 KunlunEngine.zip 到桌面
    echo   3. 双击 start.bat 启动引擎
    echo   4. 浏览器将自动打开 http://localhost:8000
    echo.
    echo ========================================
) else (
    echo ========================================
    echo              打包完成(有警告)
    echo ========================================
    echo.
    echo   部分操作出现警告，请检查日志
    echo   输出文件: %ZIP_OUTPUT%
    echo.
)

pause
