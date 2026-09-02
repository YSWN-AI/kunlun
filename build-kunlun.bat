@echo off
chcp 65001 >nul
title 昆仑引擎 · 一键构建桌面安装包

setlocal enabledelayedexpansion

echo ============================
echo  昆仑引擎 · 桌面安装包构建
echo ============================
echo.

set PROJECT_DIR=%~dp0
set FRONTEND_DIR=%PROJECT_DIR%frontend
set RESOURCES_DIR=%FRONTEND_DIR%\src-tauri\resources\backend

:: ─── 检查 Rust ───
echo [1/7] 检查 Rust 环境...
rustc --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Rust 编译器！
    echo.
    echo 要构建桌面安装包，请先安装 Rust:
    echo   1. 访问 https://rustup.rs 下载 rustup-init.exe
    echo   2. 运行后选择默认安装即可
    echo.
    echo 或者直接使用一键启动脚本（无需 Rust）:
    echo   双击项目根目录的 start.bat
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('rustc --version') do echo   Rust %%i - OK

:: ─── 复制后端 ───
echo [2/7] 复制 Python 后端到资源目录...
if exist "%RESOURCES_DIR%" rmdir /s /q "%RESOURCES_DIR%"
xcopy /E /I /Y "%PROJECT_DIR%\kunlun" "%RESOURCES_DIR%" >nul
:: 排除 __pycache__
for /d /r "%RESOURCES_DIR%" %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d"
echo   后端已复制: %RESOURCES_DIR%

:: ─── 复制配置文件 ───
echo [3/7] 复制配置文件...
if exist "%PROJECT_DIR%\.env.example" copy /Y "%PROJECT_DIR%\.env.example" "%FRONTEND_DIR%\src-tauri\.env" >nul 2>&1
if exist "%PROJECT_DIR%\data" xcopy /E /I /Y "%PROJECT_DIR%\data" "%FRONTEND_DIR%\src-tauri\resources\data" >nul 2>&1
echo   配置文件已复制

:: ─── 安装前端依赖 ───
echo [4/7] 安装前端依赖...
cd /d "%FRONTEND_DIR%"
if not exist "node_modules" (
    call npm install
) else (
    echo   前端依赖已存在
)

:: ─── 构建前端 ───
echo [5/7] 构建前端...
call npm run build
if %errorlevel% neq 0 (
    echo [错误] 前端构建失败
    pause
    exit /b 1
)
echo   前端构建完成

:: ─── 构建 Tauri ───
echo [6/7] Tauri 打包中（第一次编译较慢，请耐心等待）...
echo   编译 Rust + 打包 NSIS 安装包...
call npm run tauri build
if %errorlevel% neq 0 (
    echo [错误] Tauri 打包失败
    pause
    exit /b 1
)

:: ─── 完成 ───
echo [7/7] 构建完成！
echo.
echo ============================
echo  安装包位置:
echo  %FRONTEND_DIR%\src-tauri\target\release\bundle\nsis\
echo.
echo  文件名: 昆仑引擎_1.0.0_x64-setup.exe
echo ============================
echo.
echo  提示: 也可以直接双击 start.bat 一键启动
echo.
pause
