@echo off
cd /d "%~dp0"
chcp 65001 >nul
echo 昆仑引擎启动中...
start "Kunlun-Server" /min venv\Scripts\python.exe -m uvicorn kunlun.api.main:app --host 127.0.0.1 --port 8000
timeout /t 8 /nobreak >nul
echo 启动完成，访问 http://127.0.0.1:8000/health 验证
start http://127.0.0.1:8000/health
