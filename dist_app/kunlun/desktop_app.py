"""
昆仑创作引擎 — 桌面 GUI 壳（tkinter 实现，零额外依赖）
启动 FastAPI 后端 + 打开浏览器，最小化到系统托盘。
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import queue
import signal
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

# ----------------------------------------------------------
# 检测 tkinter 可用性
# ----------------------------------------------------------
try:
    import tkinter as tk
    from tkinter import messagebox, ttk

    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

# ----------------------------------------------------------
# 常量和全局状态
# ----------------------------------------------------------
APP_TITLE = "昆仑创作引擎"
WINDOW_WIDTH = 420
WINDOW_HEIGHT = 320

_server_thread: threading.Thread | None = None
_uvicorn_server = None
_server_running = False
_should_stop = threading.Event()


def _get_host_port():
    """从配置读取 host/port，导入失败时用默认值。"""
    try:
        _project_root = str(Path(__file__).resolve().parent.parent)
        if _project_root not in sys.path:
            sys.path.insert(0, _project_root)
        from kunlun.config import settings

        return settings.app_host, settings.app_port
    except Exception:
        return "127.0.0.1", 8000


# ----------------------------------------------------------
# FastAPI 后台服务
# ----------------------------------------------------------
def _run_server_in_thread(host: str, port: int, status_queue: queue.Queue):
    """在后台线程启动 uvicorn，阻塞直到 _should_stop 被设置。"""
    global _server_running, _uvicorn_server  # noqa: PLW0603

    try:
        _project_root = str(Path(__file__).resolve().parent.parent)
        if _project_root not in sys.path:
            sys.path.insert(0, _project_root)

        import uvicorn

        from kunlun.api.main import app

        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
            loop="asyncio",
        )
        _uvicorn_server = uvicorn.Server(config)

        # 在后台线程运行 asyncio event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # 在 loop 中启动 server
        server_task = loop.create_task(_uvicorn_server.serve())

        # 告知主线程启动完成
        status_queue.put(("started", host, port))

        # 持续运行直到收到停止信号
        while not _should_stop.is_set():
            try:
                loop.run_until_complete(asyncio.sleep(0.25))
            except RuntimeError:
                break

        # 优雅停止
        _uvicorn_server.should_exit = True
        try:
            loop.run_until_complete(server_task)
        except Exception:
            pass
        finally:
            loop.close()

    except Exception as exc:
        status_queue.put(("error", str(exc)))
    finally:
        _server_running = False


def start_server(status_queue: queue.Queue):
    """启动 FastAPI 后台线程。"""
    global _server_thread, _server_running  # noqa: PLW0603
    if _server_running:
        return

    host, port = _get_host_port()
    _should_stop.clear()
    _server_running = True
    _server_thread = threading.Thread(
        target=_run_server_in_thread,
        args=(host, port, status_queue),
        daemon=True,
    )
    _server_thread.start()


def stop_server():
    """停止 FastAPI 后台线程。"""
    global _server_running  # noqa: PLW0603
    if not _server_running:
        return

    _should_stop.set()
    _server_running = False

    if _uvicorn_server is not None:
        _uvicorn_server.should_exit = True

    # 给线程一点时间清理
    time.sleep(0.5)


# ----------------------------------------------------------
# 系统托盘（可选 pystray）
# ----------------------------------------------------------
_HAS_TRAY = False
try:
    import pystray
    from PIL import Image, ImageDraw

    _HAS_TRAY = True
except ImportError:
    pass


def _make_tray_icon_image():
    """生成一个简单的 64x64 图标。"""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 深蓝色圆形背景
    draw.ellipse((4, 4, 60, 60), fill=(30, 60, 120, 255))
    # 白色 "K" 文字（简化：画两条竖线）
    draw.rectangle((22, 16, 28, 48), fill=(255, 255, 255, 255))
    draw.polygon(
        [(28, 16), (42, 16), (28, 32), (42, 48), (28, 48)],
        fill=(255, 255, 255, 255),
    )
    return img


def _setup_tray(_root: tk.Tk, on_show, on_exit):
    """创建系统托盘图标，返回 tray 对象或 None。"""
    if not _HAS_TRAY:
        return None

    icon_img = _make_tray_icon_image()
    menu = pystray.Menu(
        pystray.MenuItem("显示窗口", on_show, default=True),
        pystray.MenuItem("打开浏览器", _open_browser),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", on_exit),
    )
    return pystray.Icon("kunlun", icon_img, APP_TITLE, menu)


# ----------------------------------------------------------
# 浏览器打开
# ----------------------------------------------------------
def _open_browser(host=None, port=None):
    """打开浏览器到昆仑 Web UI。"""
    if host is None or port is None:
        host, port = _get_host_port()
    url = f"http://{host}:{port}"
    webbrowser.open(url)
    return url


# ----------------------------------------------------------
# 纯控制台模式（fallback）
# ----------------------------------------------------------
def _console_mode():
    """无 tkinter 时的控制台 fallback 模式。"""
    host, port = _get_host_port()
    url = f"http://{host}:{port}"

    print(f"\n  {APP_TITLE} — 控制台模式")
    print(f"  {'=' * 42}")
    print()
    print("  正在启动后端服务...")

    status_queue: queue.Queue[Any] = queue.Queue()
    start_server(status_queue)

    # 等待启动
    started = False
    for _ in range(60):  # 最多等待 30 秒
        try:
            msg = status_queue.get(timeout=0.5)
            if msg[0] == "started":
                _, h, p = msg
                url = f"http://{h}:{p}"
                print(f"  服务已启动: {url}")
                started = True
                break
            if msg[0] == "error":
                print(f"  启动失败: {msg[1]}")
                return
        except queue.Empty:
            pass

    if not started:
        print(f"  服务可能已启动: {url}")

    print("  正在打开浏览器...")
    _open_browser(host, port)
    print()
    print("  按 Ctrl+C 停止服务并退出...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print()
        print("  正在停止服务...")
        stop_server()
        print("  已退出。")


# ----------------------------------------------------------
# tkinter GUI 模式
# ----------------------------------------------------------
class DesktopApp:
    """昆仑创作引擎桌面应用"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 居中窗口
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - WINDOW_WIDTH) // 2
        y = (sh - WINDOW_HEIGHT) // 2
        self.root.geometry(f"+{x}+{y}")

        # 状态变量
        self._host: str = "127.0.0.1"
        self._port: int = 8000
        self._started = False
        self._tray = None
        self._tray_thread: threading.Thread | None = None

        # 构建 UI
        self._build_ui()

        # 启动后端
        self._start_backend()

    # ---- UI 构建 ----
    def _build_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(
            main_frame,
            text=APP_TITLE,
            font=("Microsoft YaHei", 16, "bold"),
        )
        title_label.pack(pady=(0, 10))

        # 副标题
        subtitle = ttk.Label(
            main_frame,
            text="Kunlun Creation Engine",
            font=("Microsoft YaHei", 9),
            foreground="gray",
        )
        subtitle.pack(pady=(0, 15))

        # 分隔线
        sep = ttk.Separator(main_frame, orient="horizontal")
        sep.pack(fill=tk.X, pady=(0, 10))

        # 状态信息区
        status_frame = ttk.LabelFrame(main_frame, text="服务状态", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self._status_text = tk.StringVar(value="正在启动昆仑创作引擎...")
        status_label = ttk.Label(
            status_frame,
            textvariable=self._status_text,
            font=("Microsoft YaHei", 10),
            wraplength=350,
        )
        status_label.pack(anchor=tk.W)

        # 进度条
        self._progress = ttk.Progressbar(
            status_frame,
            mode="indeterminate",
            length=350,
        )
        self._progress.pack(pady=(8, 0))
        self._progress.start()

        # 按钮区
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=(5, 0))

        self._btn_open = ttk.Button(
            btn_frame,
            text="打开浏览器",
            command=self._open_browser,
            state=tk.DISABLED,
        )
        self._btn_open.pack(side=tk.LEFT, padx=5)

        self._btn_stop = ttk.Button(
            btn_frame,
            text="停止服务",
            command=self._stop_service,
        )
        self._btn_stop.pack(side=tk.LEFT, padx=5)

        self._btn_log = ttk.Button(
            btn_frame,
            text="查看日志",
            command=self._view_log,
        )
        self._btn_log.pack(side=tk.LEFT, padx=5)

    # ---- 后端启动 ----
    def _start_backend(self):
        self._status_queue: queue.Queue[Any] = queue.Queue()
        self._host, self._port = _get_host_port()
        start_server(self._status_queue)
        # 轮询启动状态
        self.root.after(200, self._poll_startup)

    def _poll_startup(self):
        try:
            msg = self._status_queue.get_nowait()
            if msg[0] == "started":
                _, self._host, self._port = msg
                self._on_server_ready()
                return
            if msg[0] == "error":
                self._status_text.set(f"启动失败:\n{msg[1]}")
                self._progress.stop()
                self._progress.configure(mode="determinate", value=0)
                return
        except queue.Empty:
            pass

        # 继续轮询（最多 30 秒）
        if not self._started:
            self.root.after(200, self._poll_startup)

    def _on_server_ready(self):
        """服务启动完成后的 UI 更新。"""
        self._started = True
        self._progress.stop()
        self._progress.configure(mode="determinate", value=100)

        url = f"http://{self._host}:{self._port}"
        self._status_text.set(f"✓ 服务运行中\n  端口: {self._port}\n  地址: {url}")
        self._btn_open.configure(state=tk.NORMAL)

        # 自动打开浏览器
        _open_browser(self._host, self._port)

        # 设置系统托盘
        self._setup_system_tray()

    # ---- 系统托盘 ----
    def _setup_system_tray(self):
        if not _HAS_TRAY:
            return

        def _show_window(_icon=None, _item=None):
            self.root.after(0, self._restore_window)

        def _tray_exit(_icon=None, _item=None):
            self.root.after(0, self._do_exit)

        self._tray = _setup_tray(self.root, _show_window, _tray_exit)
        if self._tray:
            self._tray_thread = threading.Thread(target=self._tray.run, daemon=True)
            self._tray_thread.start()

    def _restore_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    # ---- 按钮事件 ----
    def _open_browser(self):
        _open_browser(self._host, self._port)

    def _stop_service(self):
        if not _server_running:
            messagebox.showinfo(APP_TITLE, "服务已停止。")
            return

        ok = messagebox.askyesno(
            APP_TITLE,
            "确定要停止后端服务吗？\n停止后需要重新启动程序才能使用 Web UI。",
        )
        if ok:
            stop_server()
            self._status_text.set("服务已停止")
            self._progress.configure(mode="determinate", value=0)
            self._btn_open.configure(state=tk.DISABLED)

    def _view_log(self):
        """打开日志目录。"""
        log_dirs = [
            Path("data/logs"),
            Path("logs"),
            Path.cwd() / "data" / "logs",
        ]
        for d in log_dirs:
            if d.is_dir():
                os.startfile(str(d))
                return
        messagebox.showinfo(APP_TITLE, "未找到日志目录。")

    # ---- 关闭窗口 ----
    def _on_close(self):
        if not _server_running:
            self._do_exit()
            return

        result = messagebox.askyesnocancel(
            APP_TITLE,
            "关闭窗口后，您希望：\n\n"
            "  [是] 停止服务并退出\n"
            "  [否] 最小化到托盘（后台运行）\n"
            "  [取消] 留在当前窗口",
        )
        if result is True:
            self._do_exit()
        elif result is False:
            self._minimize_to_tray()
        # 取消则什么都不做

    def _minimize_to_tray(self):
        if self._tray:
            # 已有系统托盘，直接隐藏
            self.root.withdraw()
            if not hasattr(self, "_tray_notified"):
                self._tray_notified = True
                self.root.after(500, self._show_tray_balloon)
        else:
            # 无系统托盘，仅最小化到任务栏
            self.root.iconify()

    def _show_tray_balloon(self):
        if self._tray and hasattr(self._tray, "notify"):
            with contextlib.suppress(Exception):
                self._tray.notify(
                    f"昆仑创作引擎正在后台运行\nhttp://{self._host}:{self._port}",
                    title=APP_TITLE,
                )

    def _do_exit(self):
        if _server_running:
            stop_server()
        if self._tray:
            with contextlib.suppress(Exception):
                self._tray.stop()
        self.root.destroy()


# ----------------------------------------------------------
# 入口
# ----------------------------------------------------------
def main():
    """启动桌面应用。无 tkinter 时 fallback 到控制台模式。"""
    if not HAS_TKINTER:
        print("[警告] tkinter 不可用，使用控制台模式")
        _console_mode()
        return

    # 处理 Ctrl+C 信号（Windows 上 tkinter 主循环中也能响应）
    signal.signal(signal.SIGINT, lambda _s, _f: sys.exit(0))

    root = tk.Tk()
    DesktopApp(root)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        if _server_running:
            stop_server()


if __name__ == "__main__":
    main()
