"""
昆仑 Status — 项目状态概览（参考 inkos status）
用法: python kunlun_cli.py status
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class ProjectStatus:
    """项目状态"""

    name: str = "昆仑创作引擎"
    version: str = "0.2.0"
    python: str = ""
    docker: bool = False
    api_running: bool = False
    books: list = field(default_factory=list)
    token_usage: dict = field(default_factory=dict)
    last_write: str = ""


def get_status() -> ProjectStatus:
    """获取项目状态"""
    import socket
    import subprocess
    import sys

    status = ProjectStatus()
    status.python = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    # Docker
    try:
        subprocess.run(["docker", "version"], capture_output=True, timeout=5, check=True)
        status.docker = True
    except Exception:
        logger.debug("Docker 状态检查失败")

    # API
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        status.api_running = s.connect_ex(("127.0.0.1", 8000)) == 0
        s.close()
    except Exception:
        logger.debug("API 端口检查失败")

    books_dir = PROJECT_ROOT / "data" / "books"
    if books_dir.exists():
        for d in sorted(books_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if d.is_dir():
                chapters = list(d.glob("**/chapters/*.md")) if (d / "chapters").exists() else []
                book = {
                    "id": d.name,
                    "chapters": len(chapters),
                    "updated": datetime.fromtimestamp(d.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                }
                status.books.append(book)

    # Token usage
    try:
        from kunlun.token_tracker import token_tracker

        for book_info in status.books:
            summary = token_tracker.get_summary(book_info["id"])
            total = summary.get("_total", {})
            if total:
                status.token_usage[book_info["id"]] = {
                    "tokens": total.get("total_tokens", 0),
                    "cost": total.get("total_cost", 0.0),
                }
    except Exception:
        logger.debug("Token 用量统计加载失败")

    return status


def print_status(_book_id: str | None = None):
    """打印项目状态"""
    s = get_status()

    print()
    print(f"  昆仑创作引擎 v{s.version}")
    print("  " + "=" * 50)
    print()

    # 环境
    status_icon = "●" if s.api_running else "○"
    docker_icon = "●" if s.docker else "○"
    print(f"  Python {s.python}  |  API {status_icon}  |  Docker {docker_icon}")
    print()

    # 书籍
    if s.books:
        print(f"  {'书籍':<30} {'章节':>6}  {'最后更新':>16}  {'Token用量':>12}")
        print(f"  {'-' * 70}")
        for b in s.books[:10]:
            usage = s.token_usage.get(b["id"], {})
            tokens_str = f"{usage.get('tokens', 0):,}" if usage else "-"

            # 限制显示长度
            title = b["id"][:28] + (".." if len(b["id"]) > 28 else "")

            print(f"  {title:<30} {b['chapters']:>6}  {b['updated']:>16}  {tokens_str:>12}")
    else:
        print("  暂无书籍。运行 'kunlun book create' 创建第一本书。")

    print()
    print("  API: http://localhost:8000" if s.api_running else "  API 未运行，执行 kunlun up 启动")
    print("  Docs: http://localhost:8000/docs")
    print()
