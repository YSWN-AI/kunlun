"""
昆仑创作引擎 — 守护进程路由
/daemon/start, /daemon/stop
"""

import asyncio
import time

from fastapi import APIRouter, Query
from loguru import logger

from kunlun.api.routers._shared import EditorChatRequest, generate_chapter_internal
from kunlun.config import settings

router = APIRouter(tags=["守护"])

# ─── 后台任务引用集合（防止 asyncio.create_task 被GC回收）───
_background_tasks: set[asyncio.Task] = set()

_daemon_tasks: dict[str, dict] = {}


@router.post("/daemon/start", summary="启动守护进程（后台自动写章）")
async def daemon_start(
    req: EditorChatRequest,
    chapters_to_write: int = Query(
        default=settings.daemon_default_chapters, description="生成章节数"
    ),
) -> dict:
    """后台启动守护进程，自动循环写章直到完成指定章节数"""
    if req.book_id in _daemon_tasks and _daemon_tasks[req.book_id].get("running"):
        return {
            "success": False,
            "error": f"作品 {req.book_id} 已有守护进程在运行",
        }

    _daemon_tasks[req.book_id] = {"running": True, "chapters_written": 0, "started_at": time.time()}

    async def _daemon_loop():
        try:
            for i in range(chapters_to_write):
                if not _daemon_tasks.get(req.book_id, {}).get("running"):
                    break
                await generate_chapter_internal(req.book_id, chapter=i + 1)
                _daemon_tasks[req.book_id]["chapters_written"] = i + 1
                await asyncio.sleep(settings.daemon_chapter_interval)
        except Exception as e:
            logger.error(f"守护进程异常: {e}")
        finally:
            _daemon_tasks[req.book_id] = {"running": False, "finished": True}

    task = asyncio.create_task(_daemon_loop())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return {
        "success": True,
        "message": f"守护进程已启动，将生成{chapters_to_write}章",
        "book_id": req.book_id,
    }


@router.post("/daemon/stop", summary="停止守护进程")
async def daemon_stop(book_id: str = Query(..., description="作品ID")) -> dict:
    """停止指定作品的守护进程"""
    if book_id not in _daemon_tasks or not _daemon_tasks[book_id].get("running"):
        return {"success": False, "error": f"作品 {book_id} 没有运行中的守护进程"}
    _daemon_tasks[book_id]["running"] = False
    return {"success": True, "message": f"作品 {book_id} 守护进程已停止"}
