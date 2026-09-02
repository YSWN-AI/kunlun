@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo   ╔══════════════════════════════════════════════╗
echo   ║  昆仑创作引擎 - 一键打包 (Windows)           ║
echo   ╚══════════════════════════════════════════════╝
echo.

:: ── 检查 Python ──
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo   [错误] 未检测到 Python，请先安装 Python 3.11+
    echo   下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo   [检查] Python 已安装

:: ── 检查 PyInstaller ──
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo   [安装] 正在安装 PyInstaller...
    python -m pip install pyinstaller
    if %errorlevel% neq 0 (
        echo   [错误] PyInstaller 安装失败
        pause
        exit /b 1
    )
)
echo   [检查] PyInstaller 已安装

:: ── 转到项目根目录 ──
cd /d "%~dp0\.."

:: ── 清理旧的构建 ──
if exist "dist" (
    echo   [清理] 删除旧的 dist\
    rmdir /s /q "dist"
)
if exist "build" (
    echo   [清理] 删除旧的 build\
    rmdir /s /q "build"
)

:: ── 打包 CLI 版 ──
echo.
echo   ==============================================
echo    打包 CLI 版: kunlun.exe
echo   ==============================================
echo.

pyinstaller --clean --noconfirm kunlun.spec
if %errorlevel% neq 0 (
    echo.
    echo   [失败] CLI 版打包失败
    pause
    exit /b 1
)

:: ── 检查输出 ──
if exist "dist\kunlun.exe" (
    echo.
    echo   ==============================================
    echo    打包完成!
    echo   ==============================================
    echo.
    echo    CLI 版: dist\kunlun.exe
    for %%f in (dist\kunlun.exe) do (
        set /a size=%%~zf / 1048576
        echo    文件大小: !size! MB
    )
    echo.
    echo   使用方法: kunlun.exe setup
    echo              kunlun.exe doctor
    echo              kunlun.exe desktop
) else (
    echo.
    echo   [失败] 未找到 dist\kunlun.exe
    pause
    exit /b 1
)

:: ── 询问是否打包 GUI 版 ──
echo.
set /p BUILD_GUI="  是否同时打包 GUI 桌面版？(y/n，默认 n): "
if /i "%BUILD_GUI%"=="y" (
    echo.
    echo   ==============================================
    echo    打包 GUI 版: kunlun-desktop.exe
    echo   ==============================================
    echo.
    pyinstaller --clean --noconfirm kunlun\desktop_app.spec
    if %errorlevel% equ 0 (
        echo   [完成] GUI 版打包成功: dist\kunlun-desktop.exe
    ) else (
        echo   [警告] GUI 版打包失败（可能需要额外依赖）
    )
)

echo.
echo   🎉 打包流程结束!
pause