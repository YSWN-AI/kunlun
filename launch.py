#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kunlun Creation Engine - One-Click Launcher
Double-click this file to start all services automatically.
"""

import subprocess
import sys
import time
import socket
import os
import webbrowser
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
os.chdir(PROJECT_ROOT)

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def banner():
    print()
    print(f"  {BOLD}============================================================{RESET}")
    print(f"  {BOLD}  Kunlun Creation Engine v0.1.0-alpha{RESET}")
    print(f"  {BOLD}  One-Click Launcher{RESET}")
    print(f"  {BOLD}============================================================{RESET}")
    print()


def check_docker() -> bool:
    """Check if Docker Desktop is running. Try to start it if not."""
    try:
        subprocess.run(["docker", "version"], capture_output=True, check=True, timeout=10)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    print(f"  {YELLOW}Docker Desktop not running. Trying to start...{RESET}")

    possible_paths = [
        r"C:\Program Files\Docker\Docker\Docker Desktop.exe",
        r"C:\Program Files (x86)\Docker\Docker\Docker Desktop.exe",
    ]
    local_app = os.getenv("LOCALAPPDATA", "")
    if local_app:
        possible_paths.append(os.path.join(local_app, "Docker", "Docker Desktop.exe"))

    docker_path = None
    for p in possible_paths:
        if os.path.exists(p):
            docker_path = p
            break

    if not docker_path:
        print(f"  {YELLOW}Docker Desktop not found. Using fallback mode.{RESET}")
        return False

    print(f"  Launching: {docker_path}")
    subprocess.Popen([docker_path])  # 传递列表，不使用 shell=True（避免安全风险）

    # Wait up to 90s for Docker engine
    print(f"  Waiting for Docker engine (max 90s)...", end="", flush=True)
    for _ in range(30):
        try:
            subprocess.run(["docker", "version"], capture_output=True, check=True, timeout=5)
            print(f" {GREEN}ready!{RESET}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            time.sleep(3)
            print(".", end="", flush=True)

    print(f" {YELLOW}timeout{RESET}")
    return False


def start_containers() -> bool:
    """Start docker compose services."""
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        print(f"  {YELLOW}docker-compose.yml not found, skipping containers{RESET}")
        return False

    print(f"  Starting containers: Neo4j + Redis + NATS + Qdrant...")
    result = subprocess.run(
        ["docker", "compose", "up", "-d"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        print(f"  {YELLOW}Container startup failed. Using fallback mode.{RESET}")
        print(f"  {result.stderr.strip()[:200]}")
        return False

    # Wait for Neo4j
    print(f"  Waiting for Neo4j on port 7687 (max 60s)...", end="", flush=True)
    for _ in range(20):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            if s.connect_ex(("127.0.0.1", 7687)) == 0:
                s.close()
                print(f" {GREEN}OK{RESET}")
                break
            s.close()
        except Exception:
            pass
        time.sleep(3)
        print(".", end="", flush=True)
    else:
        print(f" {YELLOW}timeout{RESET}")
        return False

    # Quick check other ports
    for name, port in [("Redis", 6379), ("NATS", 4222), ("Qdrant", 6333)]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            ok = s.connect_ex(("127.0.0.1", port)) == 0
            s.close()
            status = f"{GREEN}OK{RESET}" if ok else f"{YELLOW}OFF{RESET}"
            print(f"  {name} ({port}): {status}")
        except Exception:
            pass

    print(f"  {GREEN}All containers ready!{RESET}")
    return True


def check_venv() -> bool:
    """Check that venv exists with required deps."""
    python_exe = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        print(f"  {RED}[ERROR] venv\\Scripts\\python.exe not found{RESET}")
        print(f"  Please run: scripts\\setup.bat")
        return False

    # Check fastapi
    result = subprocess.run(
        [str(python_exe), "-c", "import fastapi; import uvicorn"],
        capture_output=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        print(f"  {RED}[ERROR] Dependencies not installed{RESET}")
        print(f"  Please run: scripts\\setup.bat")
        return False

    # Show version
    ver = subprocess.run(
        [str(python_exe), "--version"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    print(f"  {ver.stderr.strip() or ver.stdout.strip()}")
    return True


def start_backend():
    """Start FastAPI uvicorn server and auto-open browser."""
    python_exe = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"

    # Ensure data dirs exist
    (PROJECT_ROOT / "data" / "logs").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "data" / "qdrant").mkdir(parents=True, exist_ok=True)

    print(f"  {GREEN}Python environment: OK{RESET}")
    print(f"  Working dir: {PROJECT_ROOT}")
    print()
    print(f"  {CYAN}API:     http://localhost:8000{RESET}")
    print(f"  {CYAN}Docs:    http://localhost:8000/docs{RESET}")
    print(f"  {CYAN}Health:  http://localhost:8000/api/v1/health{RESET}")
    print()
    print(f"  {BOLD}============================================================{RESET}")
    print()

    # Launch uvicorn in background thread
    process = subprocess.Popen(
        [
            str(python_exe),
            "-m",
            "uvicorn",
            "kunlun.api.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--reload",
        ],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    # Start a thread to print uvicorn output
    def print_output():
        for line in process.stdout:
            print(line, end="")

    output_thread = threading.Thread(target=print_output, daemon=True)
    output_thread.start()

    # Wait for server to be ready, then open browser
    url = "http://localhost:8000"
    print(f"  Waiting for server to be ready...", end="", flush=True)
    for _ in range(30):
        try:
            import urllib.request

            resp = urllib.request.urlopen(url, timeout=2)
            if resp.status < 500:
                print(f" {GREEN}ready!{RESET}")
                print(f"  Opening browser: {url}")
                webbrowser.open(url)
                break
        except Exception:
            pass
        time.sleep(2)
        print(".", end="", flush=True)
    else:
        print(f" {YELLOW}timeout, opening anyway{RESET}")
        webbrowser.open(url)

    print(f"  Press Ctrl+C to stop")
    print()

    # Wait for process to finish
    process.wait()


def main():
    banner()

    # Phase 1: Docker
    print(f"  [{BOLD}Phase 1{RESET}] Docker Services")
    print(f"  ------------------------------------------------------------")
    docker_ok = check_docker()
    print()

    # Phase 2: Containers
    if docker_ok:
        print(f"  [{BOLD}Phase 2{RESET}] Dependency Containers")
        print(f"  ------------------------------------------------------------")
        containers_ok = start_containers()  # noqa: F841
        print()

    # Fallback notice
    if not docker_ok:
        print(f"  [{BOLD}Fallback Mode{RESET}] No Docker containers")
        print(f"    Neo4j -> SQLite graph (built-in)")
        print(f"    Redis -> Cache disabled")
        print(f"    NATS  -> In-process bus (built-in)")
        print(f"    Qdrant -> Python embedded mode")
        print()

    # Phase 3: Backend
    print(f"  [{BOLD}Phase 3{RESET}] Python Backend")
    print(f"  ------------------------------------------------------------")
    if not check_venv():
        input(f"\n  Press Enter to exit...")
        sys.exit(1)

    start_backend()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n  {YELLOW}Server stopped.{RESET}")
    except Exception as e:
        print(f"\n  {RED}[FATAL] {e}{RESET}")
        input(f"  Press Enter to exit...")
        sys.exit(1)
