@echo off
chcp 65001 >nul
title 昆仑部署

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
cd /d "%PROJECT_DIR%"

echo.
echo ================================================
echo   昆仑创作引擎 - Docker 部署
echo ================================================
echo.

echo [1/2] 启动基础设施 (Neo4j + Redis + NATS + Qdrant)...
docker compose up -d neo4j redis nats qdrant
if errorlevel 1 (
    echo [ERROR] 基础设施启动失败
    pause
    exit /b 1
)
echo [OK] 基础设施已启动

echo.
echo [2/2] 构建并启动昆仑应用...
docker compose up -d kunlun
if errorlevel 1 (
    echo [ERROR] 应用构建失败
    pause
    exit /b 1
)

echo.
echo ================================================
echo   部署完成！
echo   访问: http://127.0.0.1:8000/health
echo ================================================
echo.

start http://127.0.0.1:8000/health
pause
