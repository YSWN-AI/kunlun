<#
.SYNOPSIS
    昆仑创作引擎 — 启动器脚本
.DESCRIPTION
    自动检查并启动 Neo4j 服务，清理代码标记，启动 FastAPI，打开浏览器
#>

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "昆仑创作引擎"

# 获取项目根目录（scripts 的父目录）
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║      昆仑创作引擎 Kunlun Creation Engine         ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  项目路径: $ProjectRoot" -ForegroundColor DarkGray
Write-Host ""

# ─── 函数: 检查端口是否被占用 ──────────────────────
function Test-PortInUse {
    param([int]$Port)
    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    return [bool]$connections
}

# ─── 1. 检查 Python 环境 ──────────────────────────
Write-Host "[1/5] 检查 Python 环境..." -ForegroundColor Yellow
try {
    $pythonCmd = Get-Command python -ErrorAction Stop
    $pyVersion = & python --version 2>&1
    Write-Host "  [OK] $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] 未找到 Python，请先运行 scripts\setup.bat" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}

# ─── 2. 检查 Neo4j 服务 ──────────────────────────
Write-Host "[2/5] 检查 Neo4j 服务..." -ForegroundColor Yellow
$neo4jRunning = $false
try {
    $neo4jProcess = Get-Process -Name "java" -ErrorAction SilentlyContinue | 
        Where-Object { $_.CommandLine -like "*neo4j*" -or $_.MainWindowTitle -like "*neo4j*" }
    if ($neo4jProcess) {
        Write-Host "  [OK] Neo4j 服务正在运行" -ForegroundColor Green
        $neo4jRunning = $true
    }
} catch { }

if (-not $neo4jRunning) {
    # 尝试启动 Neo4j 服务
    $neo4jService = Get-Service -Name "neo4j" -ErrorAction SilentlyContinue
    if ($neo4jService) {
        if ($neo4jService.Status -ne "Running") {
            Write-Host "  正在启动 Neo4j 服务..." -ForegroundColor Gray
            Start-Service -Name "neo4j"
            Start-Sleep -Seconds 5
            Write-Host "  [OK] Neo4j 服务已启动" -ForegroundColor Green
        }
    } else {
        Write-Host "  [WARN] Neo4j 服务未安装或未找到" -ForegroundColor DarkYellow
        Write-Host "  引擎将降级使用 SQLite 模式运行" -ForegroundColor DarkGray
    }
}

# ─── 3. 清理代码标记 ──────────────────────────
Write-Host "[3/5] 清理文件标记..." -ForegroundColor Yellow
$venvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$cleanupScript = Join-Path $ProjectRoot "scripts\cleanup.py"

if (Test-Path $cleanupScript) {
    try {
        & $venvPython $cleanupScript 2>&1 | Out-Null
        Write-Host "  [OK] 文件标记清理完成" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] 清理脚本执行异常，跳过: $_" -ForegroundColor DarkYellow
    }
} else {
    Write-Host "  [SKIP] 清理脚本不存在" -ForegroundColor DarkGray
}

# ─── 4. 检查端口 ──────────────────────────
Write-Host "[4/5] 检查端口 8000..." -ForegroundColor Yellow
if (Test-PortInUse -Port 8000) {
    Write-Host "  [WARN] 端口 8000 已被占用，尝试关闭已有进程..." -ForegroundColor DarkYellow
    Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}
Write-Host "  [OK] 端口 8000 可用" -ForegroundColor Green

# ─── 5. 启动 FastAPI 服务 ──────────────────────────
Write-Host "[5/5] 启动昆仑创作引擎..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║  引擎正在启动，即将打开浏览器...                    ║" -ForegroundColor Green
Write-Host "  ║  访问地址: http://localhost:8000                    ║" -ForegroundColor Green
Write-Host "  ║  API文档:  http://localhost:8000/docs               ║" -ForegroundColor Green
Write-Host "  ║  关闭此窗口即可停止引擎                             ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# 进入项目目录
Set-Location $ProjectRoot

# 启动 API 服务（非阻塞方式打开浏览器）
$apiJob = Start-Job -ScriptBlock {
    param($Root)
    Set-Location $Root
    $env:PYTHONPATH = $Root
    & "$Root\venv\Scripts\python.exe" -m uvicorn kunlun.api.main:app --host 0.0.0.0 --port 8000 2>&1
} -ArgumentList $ProjectRoot

# 等待几秒让服务启动
Write-Host "  等待服务启动..." -ForegroundColor Gray
Start-Sleep -Seconds 4

# 6. 自动打开浏览器
try {
    Start-Process "http://localhost:8000"
    Write-Host "  浏览器已打开" -ForegroundColor Green
} catch {
    Write-Host "  请手动打开浏览器访问 http://localhost:8000" -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "  引擎运行中... 按 Ctrl+C 停止" -ForegroundColor DarkGray
Write-Host ""

# 等待并显示 Job 输出
try {
    Receive-Job -Job $apiJob -Wait
} finally {
    Remove-Job -Job $apiJob -Force -ErrorAction SilentlyContinue
}

Read-Host "按 Enter 退出"
