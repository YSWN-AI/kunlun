"""
昆仑创作引擎 — 桌面版启动器
真正的原生 Windows 窗口，无需浏览器
"""

import os
import sys
import threading
import subprocess
import time
import webview

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 后端进程
_backend_process = None


def start_backend():
    """启动 FastAPI 后端"""
    global _backend_process
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
            "8000",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,  # 保留 stderr 以便调试
        text=True,
    )
    # 等待后端就绪
    import urllib.request

    for i in range(30):
        try:
            urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


class API:
    """Python → JS 桥接"""

    def status(self):
        from kunlun import __version__

        return {"version": __version__, "status": "running"}

    def get_port(self):
        return 8000


def main():
    # 启动后端
    print("[昆仑] 启动后端服务...")
    ok = start_backend()
    if not ok:
        print("[昆仑] 后端启动失败!")
        # 尝试用已有后端
        try:
            import urllib.request

            urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2)
            ok = True
            print("[昆仑] 使用已有后端服务")
        except Exception:
            pass

    if not ok:
        import tkinter.messagebox

        tkinter.messagebox.showerror("昆仑引擎", "后端服务启动失败，请检查 Python 环境和依赖。")
        return

    print(f"[昆仑] 后端已启动: http://127.0.0.1:8000")
    print("[昆仑] 打开桌面窗口...")

    # 创建原生桌面窗口
    _ = webview.create_window(
        title="昆仑创作引擎 · 万山之主",
        url="http://127.0.0.1:8000",
        width=1280,
        height=860,
        min_size=(900, 600),
        resizable=True,
        fullscreen=False,
        js_api=API(),
    )

    webview.start(debug=False, http_server=False)

    # 窗口关闭后清理
    print("[昆仑] 窗口已关闭，停止服务...")
    global _backend_process
    if _backend_process:
        _backend_process.terminate()  # 优雅终止，避免僵尸进程
        try:
            _backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _backend_process.kill()
        print("[昆仑] 后端已停止")


if __name__ == "__main__":
    main()
