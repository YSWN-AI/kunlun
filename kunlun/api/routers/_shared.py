"""
昆仑创作引擎 — 路由共享模块

从 routes.py 提取的公共工具：延迟导入缓存、限流器、批量任务存储、公共请求模型。
所有子路由模块均可从此处导入共享组件。
"""

import asyncio
import time
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

# ─── 延迟导入缓存（热点模块，避免每个请求都触发import查找）───
_import_cache: dict[str, Any] = {}


def cached_import(module_path: str, attr: str | None = None) -> Any:
    """缓存式的懒加载导入，减少每个请求的import开销。

    热路径模块（如 gacha_engine、editor 等）在首次导入后缓存到字典，
    后续调用直接从字典获取，避免 importlib 重复查找。
    """
    cache_key = f"{module_path}:{attr}" if attr else module_path
    if cache_key not in _import_cache:
        import importlib

        mod = importlib.import_module(module_path)
        _import_cache[cache_key] = getattr(mod, attr) if attr else mod
    return _import_cache[cache_key]


# ─── 简单内存限流器（chat 热点端点专用）───
_chat_rate_limiter: dict[str, list[float]] = {}  # IP → [timestamp, ...]
_CHAT_RATE_WINDOW = 60  # 窗口60秒
_CHAT_RATE_MAX = 20  # 每窗口最大20次


def check_chat_rate(client_ip: str) -> bool:
    """滑动窗口限流检查，返回True表示允许"""
    now = time.time()
    window_start = now - _CHAT_RATE_WINDOW
    calls = _chat_rate_limiter.get(client_ip, [])
    # 清理过期记录
    calls = [t for t in calls if t > window_start]
    if len(calls) >= _CHAT_RATE_MAX:
        return False
    calls.append(now)
    _chat_rate_limiter[client_ip] = calls
    # 定期清理过期IP（每次清理时顺带）
    if len(_chat_rate_limiter) > 1000:
        _chat_rate_limiter.clear()
    return True


# ─── 公共请求模型 ───
class ChatRequest(BaseModel):
    messages: list[dict] = Field(..., description='消息列表 [{"role":"user","content":"..."}]')
    model: str = Field(default="deepseek-chat", description="模型名称")
    temperature: float = Field(default=0.7, description="温度")
    max_tokens: int = Field(default=2048, description="最大输出token")


class EditorChatRequest(BaseModel):
    book_id: str = Field(..., description="作品ID")
    message: str = Field(..., description="用户消息")
    context: dict | None = Field(default=None, description="附加上下文")


# ─── 批量任务共享存储（routes.py & routers/chapters.py 共用）───

_batch_tasks: dict[str, dict] = {}
_CLEANUP_TASK: asyncio.Task | None = None


def get_batch_tasks() -> dict[str, dict]:
    """获取批量任务存储（全局单例）"""
    return _batch_tasks


async def _cleanup_old_batch_tasks(ttl: int = 86400) -> None:
    """每小时清理超过 TTL 的批量任务，防止内存泄漏"""
    from kunlun.config import settings

    effective_ttl = settings.batch_task_ttl if ttl == 86400 else ttl
    while True:
        await asyncio.sleep(3600)
        now = time.time()
        expired = [
            tid
            for tid, t in _batch_tasks.items()
            if now - t.get("_created_at", now) > effective_ttl
        ]
        for tid in expired:
            _batch_tasks.pop(tid, None)
        if expired:
            logger.info(f"[BatchTasks] 已清理 {len(expired)} 个过期任务")


def ensure_batch_cleanup() -> None:
    """确保批量任务清理协程已启动（幂等）"""
    global _CLEANUP_TASK  # noqa: PLW0603
    if _CLEANUP_TASK is None:
        _CLEANUP_TASK = asyncio.create_task(_cleanup_old_batch_tasks())


# ─── 章节生成内部函数（daemon 和 chapters 路由共用）───


async def generate_chapter_internal(
    book_id: str,
    chapter: int,
    mode: str = "gacha_parallel_3",
) -> dict:
    """核心章节生成逻辑，不依赖 FastAPI Request。

    供 daemon 守护进程和 chapters 路由的 generate_chapter 端点共同调用。
    返回完整的生成结果 dict（含 success/draft/audit_passed 等字段）。
    """
    import time as _time
    import traceback

    from kunlun.config import settings

    makefile_cls = cached_import("kunlun.agents.makefile", "Makefile")

    pipeline_id = f"{book_id}_ch{chapter}"
    makefile_obj = makefile_cls()
    _gen_start = _time.perf_counter()

    try:
        result = await makefile_obj.execute(
            {
                "action": "generate_chapter_sync",
                "book_id": book_id,
                "chapter_number": chapter,
                "mode": mode,
            }
        )
        _gen_duration = _time.perf_counter() - _gen_start
        record_generation_step = cached_import("kunlun.observability", "record_generation_step")
        record_generation_step("total", _gen_duration)
        logger.info(f"[{pipeline_id}] 全流程耗时: {_gen_duration:.2f}s")
    except Exception as e:
        logger.error(f"[{pipeline_id}] Makefile 执行异常: {e}\n{traceback.format_exc()}")
        is_dev = settings.app_env == "development"
        return {
            "success": False,
            "pipeline_id": pipeline_id,
            "chapter": chapter,
            "error": str(e) if is_dev else "服务器内部错误，请稍后重试",
            "traceback": traceback.format_exc() if is_dev else None,
            "message": f"流水线执行异常: {e}" if is_dev else "流水线执行失败",
        }

    if not result.get("success"):
        is_dev = settings.app_env == "development"
        return {
            "success": False,
            "pipeline_id": result.get("pipeline_id", pipeline_id),
            "chapter": result.get("chapter", chapter),
            "error": result.get("error", "未知错误") if is_dev else "流水线执行失败",
            "traceback": result.get("traceback", "") if is_dev else None,
            "message": result.get("error", "未知错误"),
        }

    # 触发自动文件同步
    try:
        auto_sync = cached_import("kunlun.autosync", "AutoSync")
        await auto_sync.trigger(
            "chapter_generated",
            {
                "book_id": book_id,
                "chapter": chapter,
                "draft": result.get("draft", ""),
                "blueprint": result.get("blueprint", {}),
                "audit_result": {"passed": result.get("audit_passed", False)},
            },
        )
    except Exception as e:
        logger.warning(f"[AutoSync] 触发失败: {e}")

    return {
        "success": True,
        "pipeline_id": result.get("pipeline_id", pipeline_id),
        "chapter": result.get("chapter", chapter),
        "draft": result.get("draft", ""),
        "audit_passed": result.get("audit_passed", False),
        "revisions": result.get("revisions", 0),
        "style_changes": result.get("style_changes", 0),
        "gacha_best_model": result.get("gacha_best_model", ""),
        "kg_snapshot_id": result.get("kg_snapshot_id", ""),
        "message": "生成完成",
    }
