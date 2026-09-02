@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Kunlun Engine - 一键启动服务

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
set "TOOLS_DIR=%ROOT_DIR%\tools"

echo ============================================================
echo   昆仑创作引擎 - 依赖服务一键启动脚本
echo ============================================================
echo.

:: 创建工具目录
if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"

:: ─── Redis ──────────────────────────────────────────────────
echo [1/3] 启动 Redis...
if exist "%TOOLS_DIR%\redis\redis-server.exe" (
    echo    已找到本地 Redis
    start "Redis" "%TOOLS_DIR%\redis\redis-server.exe" --daemonize no
) else (
    where redis-server >nul 2>&1
    if %errorlevel% equ 0 (
        echo    使用系统 Redis
        start "Redis" redis-server
    ) else (
        echo    [降级] Redis 未安装，使用进程内缓存
    )
)
timeout /t 2 /nobreak >nul

:: ─── NATS ──────────────────────────────────────────────────
echo [2/3] 启动 NATS Server...
if exist "%TOOLS_DIR%\nats\nats-server.exe" (
    echo    已找到本地 NATS
    start "NATS" "%TOOLS_DIR%\nats\nats-server.exe" -js
) else (
    where nats-server >nul 2>&1
    if %errorlevel% equ 0 (
        echo    使用系统 NATS
        start "NATS" nats-server -js
    ) else (
        echo    [降级] NATS 未安装，使用进程内消息总线
    )
)
timeout /t 2 /nobreak >nul

:: ─── Neo4j ─────────────────────────────────────────────────
echo [3/3] 检查 Neo4j...
where neo4j >nul 2>&1
if %errorlevel% equ 0 (
    echo    使用系统 Neo4j
    start "Neo4j" neo4j console
) else (
    echo    [降级] Neo4j 未安装，使用 SQLite 图模式
)
timeout /t 2 /nobreak >nul

:: ─── 等待服务启动 ──────────────────────────────────────────
echo.
echo 等待服务启动...
timeout /t 5 /nobreak >nul

:: ─── 检查端口 ──────────────────────────────────────────────
echo.
echo ============================================================
echo   服务状态检查
echo ============================================================
echo.
netstat -ano | findstr ":6379" >nul && echo [OK] Redis 已启动 (端口 6379) || echo [降级] Redis 未启动
netstat -ano | findstr ":4222" >nul && echo [OK] NATS 已启动 (端口 4222) || echo [降级] NATS 未启动
netstat -ano | findstr ":7687" >nul && echo [OK] Neo4j 已启动 (端口 7687) || echo [降级] Neo4j 未启动
netstat -ano | findstr ":6333" >nul && echo [OK] Qdrant 已启动 (端口 6333) || echo [信息] Qdrant 将在引擎启动时初始化

echo.
echo ============================================================
echo   服务启动完成！
echo ============================================================
echo.
echo 注意: 如果显示降级状态，部分功能可能受限。
echo 建议安装 Docker Desktop 以获得完整功能。
echo.
