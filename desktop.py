"""
昆仑创作引擎 — 桌面版启动器
真正的原生 Windows 窗口，无需浏览器。
支持 PyInstaller 打包（frozen 模式下同进程线程启动 uvicorn）。
"""

import os
import sys
import threading
import subprocess
import time
import socket
from pathlib import Path

import webview

# 项目根目录（frozen 模式下 __file__ 在 _internal/ 中，需用 sys.executable）
if getattr(sys, "frozen", False):
    PROJECT_ROOT = os.path.dirname(sys.executable)
else:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 后端进程（开发模式 subprocess）
_backend_process = None

# 当前使用的端口
_current_port = 8000


# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
def _setup_logging() -> None:
    """将启动日志输出到 data/logs/desktop.log。"""
    log_dir = os.path.join(PROJECT_ROOT, "data", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "desktop.log")
    try:
        log_file = open(log_path, "a", encoding="utf-8")
        # 重定向 stdout/stderr 到文件 + 控制台
        class _Tee:
            def __init__(self, *streams):
                self.streams = streams

            def write(self, data):
                for s in self.streams:
                    try:
                        s.write(data)
                        s.flush()
                    except Exception:
                        pass

            def flush(self):
                for s in self.streams:
                    try:
                        s.flush()
                    except Exception:
                        pass

        sys.stdout = _Tee(sys.__stdout__, log_file)
        sys.stderr = _Tee(sys.__stderr__, log_file)
        print(f"\n{'='*60}")
        print(f"[昆仑] 桌面版启动 {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[昆仑] 项目根目录: {PROJECT_ROOT}")
        print(f"[昆仑] Python: {sys.executable}")
        print(f"[昆仑] frozen: {getattr(sys, 'frozen', False)}")
    except Exception as e:
        print(f"[昆仑] 日志初始化失败: {e}")


# ---------------------------------------------------------------------------
# 端口检测
# ---------------------------------------------------------------------------
def _find_available_port(start: int = 8000, max_tries: int = 20) -> int:
    """从 start 开始查找可用端口，最多尝试 max_tries 个。"""
    for port in range(start, start + max_tries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                result = s.connect_ex(("127.0.0.1", port))
                if result != 0:
                    return port
        except Exception:
            continue
    return start  # 兜底返回起始端口


def _wait_for_backend(port: int, timeout: int = 45) -> bool:
    """等待后端就绪，最多 timeout 秒。"""
    import urllib.request

    for i in range(timeout):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


# ---------------------------------------------------------------------------
# 后端启动
# ---------------------------------------------------------------------------
def start_backend(port: int) -> bool:
    """启动 FastAPI 后端。frozen 模式用线程，开发模式用 subprocess。"""
    global _backend_process

    if getattr(sys, "frozen", False):
        # PyInstaller 打包模式：同进程内用 daemon 线程启动 uvicorn
        print(f"[昆仑] frozen 模式，同进程线程启动 uvicorn (port={port})")

        def run_server():
            try:
                import uvicorn

                uvicorn.run(
                    "kunlun.api.main:app",
                    host="127.0.0.1",
                    port=port,
                    log_level="warning",
                    log_config=None,
                )
            except Exception as e:
                print(f"[昆仑] uvicorn 线程异常: {e}")

        t = threading.Thread(target=run_server, daemon=True)
        t.start()
    else:
        # 开发模式：subprocess 启动
        print(f"[昆仑] 开发模式，subprocess 启动 uvicorn (port={port})")
        os.chdir(PROJECT_ROOT)
        _backend_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "kunlun.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

    # 等待后端就绪（45秒）
    ok = _wait_for_backend(port, timeout=45)
    if not ok:
        # 尝试用已有后端
        try:
            import urllib.request

            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
            ok = True
            print("[昆仑] 使用已有后端服务")
        except Exception:
            pass
    return ok


def stop_backend() -> None:
    """停止后端进程。frozen 模式下 daemon 线程随进程退出自动终止。"""
    global _backend_process
    if _backend_process:
        print("[昆仑] 停止后端进程...")
        _backend_process.terminate()
        try:
            _backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _backend_process.kill()
        _backend_process = None
        print("[昆仑] 后端已停止")
    else:
        print("[昆仑] frozen 模式，后端线程随进程退出")


# ---------------------------------------------------------------------------
# API 桥接（Python ↔ JS）
# ---------------------------------------------------------------------------
class API:
    """Python → JS 桥接。"""

    def __init__(self, port: int = 8000):
        self._port = port

    def status(self):
        from kunlun import __version__

        return {"version": __version__, "status": "running", "port": self._port}

    def get_version(self):
        """返回引擎版本号。"""
        try:
            from kunlun import __version__

            return __version__
        except Exception:
            return "0.4.0"

    def get_port(self):
        return self._port


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main():
    # 桌面端为本地单用户应用，禁用速率限制以规避 slowapi 中间件 bug
    os.environ["RATE_LIMIT_PER_MINUTE"] = "0"

    _setup_logging()

    # 1. 端口选择（两种模式共用）
    global _current_port
    _current_port = _find_available_port(8000)
    print(f"[昆仑] 使用端口: {_current_port}")

    # 2. 启动后端
    print("[昆仑] 启动后端服务...")
    ok = start_backend(_current_port)

    if not ok:
        print("[昆仑] 后端启动失败!")
        try:
            import tkinter.messagebox

            tkinter.messagebox.showerror(
                "昆仑引擎", "后端服务启动失败，请检查 Python 环境和依赖。"
            )
        except Exception:
            pass
        return

    print(f"[昆仑] 后端已启动: http://127.0.0.1:{_current_port}")
    print("[昆仑] 打开桌面窗口...")

    # 3. 创建原生桌面窗口
    _ = webview.create_window(
        title="昆仑创作引擎 v0.4.0 · 创作工作台",
        url=f"http://127.0.0.1:{_current_port}",
        width=1400,
        height=900,
        min_size=(1000, 700),
        resizable=True,
        fullscreen=False,
        js_api=API(port=_current_port),
    )

    webview.start(debug=False, http_server=False)

    # 4. 窗口关闭后清理
    print("[昆仑] 窗口已关闭，停止服务...")
    stop_backend()
    print("[昆仑] 退出完成")


if __name__ == "__main__":
    main()
