"""
昆仑创作引擎 — 章节路由 (v2)
/books/{book_id}/chapters/batch-generate: 批量生成
/books/{book_id}/chapters/{chapter}/generate: 单章生成
/books/batch-status/{task_id}: 查询批量进度
"""

import asyncio
import time

from fastapi import APIRouter, Query, Request
from loguru import logger
from pydantic import BaseModel, Field

from kunlun.api.rate_limit import get_limiter
from kunlun.api.routers._shared import (
    cached_import,
    ensure_batch_cleanup,
    get_batch_tasks,
)
from kunlun.api.security_middleware import validate_book_id, validate_chapter_number
from kunlun.config import settings

router = APIRouter(tags=["生成"])
_limiter = get_limiter()
_gen_rate_limit = (
    _limiter.limit(f"{settings.rate_limit_generate_per_minute}/minute") if _limiter else lambda f: f
)

# WS 步进映射（Makefile 同步流水线步骤 → WS 进度广播）
_SYNC_STEP_WS_MAP = {
    "snapshot_start": ("Step 0/7: KG 快照拍摄", 0.02, "正在保存当前知识图谱状态..."),
    "snapshot_done": ("Snapshot 完成", 0.05, ""),
    "blueprint_start": ("Step 1/7: Architect 蓝图生成", 0.10, "LLM生成章节蓝图..."),
    "blueprint_done": ("Blueprint 完成", 0.16, ""),
    "draft_start": ("Step 2/7: Writer 抽卡生成", 0.20, "多模型并行生成..."),
    "draft_done": ("Draft 完成", 0.30, ""),
    "audit_start": ("Step 3/7: Auditor 审计", 0.35, "8道门禁检查..."),
    "audit_done": ("Audit 完成", 0.45, ""),
    "revise_start": ("Step 4/7: 修订中", 0.50, "根据审计报告修订..."),
    "revise_done": ("Revise 完成", 0.58, ""),
    "polish_start": ("Step 5/7: StyleEngineer 润色", 0.62, "去AI味 + 语感优化..."),
    "polish_done": ("Polish 完成", 0.70, ""),
    "kg_update_start": ("Step 6/7: KG 更新", 0.75, "写回知识图谱..."),
    "kg_update_done": ("KG Update 完成", 0.85, ""),
    "publish_start": ("Step 7/7: 发布", 0.90, "保存到输出目录..."),
    "publish_done": ("Publish 完成", 0.98, ""),
    "error": ("Error", 0.0, ""),
}

# 后台任务引用集合
_background_tasks: set[asyncio.Task] = set()


def _build_generation_error(e: Exception, pipeline_id: str, chapter: int) -> dict:
    """构建生成失败时的错误响应（区分开发/生产环境）"""
    import traceback as _tb

    is_dev = settings.app_env == "development"
    return {
        "success": False,
        "pipeline_id": pipeline_id,
        "chapter": chapter,
        "error": str(e) if is_dev else "服务器内部错误，请稍后重试",
        "traceback": _tb.format_exc() if is_dev else None,
        "message": f"流水线执行异常: {e}" if is_dev else "流水线执行失败",
    }


def _build_step_hint(step: str, data: dict | None = None) -> str:
    """根据步骤和数据构建进度提示文案"""
    hint = ""
    if step == "draft_done" and data:
        hint = f"字数: {data.get('word_count', 0)}, 最优模型: {data.get('best_model', '')}"
    elif step == "audit_done" and data:
        ar = data.get("audit_result", {})
        hint = f"通过: {ar.get('passed', False)}, 致命: {ar.get('fatal_count', 0)}"
    elif step == "polish_done" and data:
        hint = f"变化: {data.get('changes', 0)} 处"
    return hint


class GenerateChapterRequest(BaseModel):
    """章节生成请求"""

    book_id: str = Field(..., description="书籍ID")
    chapter: int = Field(..., description="章节编号")
    mode: str = Field(default="gacha_parallel_3", description="抽卡模式")
    chapter_type: str = Field(default="normal", description="章节类型 (normal/battle/climax/intro)")


# ─── 单章生成 ───


@router.post("/books/{book_id}/chapters/{chapter}/generate", summary="章节生成（全流程）")
@_gen_rate_limit
async def generate_chapter(
    book_id: str, chapter: int, req: GenerateChapterRequest, request: Request = None  # type: ignore[assignment]
) -> dict:
    """触发完整的20步章节生成流水线，支持 WS 进度广播和 Learner 偏好学习"""
    import time as _time
    import traceback

    book_id = validate_book_id(book_id)
    chapter = validate_chapter_number(chapter)

    ws_manager = cached_import("kunlun.api.ws_manager", "ws_manager")
    get_learner = cached_import("kunlun.learn", "get_learner")
    makefile_cls = cached_import("kunlun.agents.makefile", "Makefile")

    if request is not None:
        request.state.sync_data = {"book_id": book_id, "chapter": chapter}

    pipeline_id = f"{book_id}_ch{chapter}"
    learner = get_learner(book_id)

    async def progress_cb(step: str, data: dict | None = None) -> None:
        try:
            mapping = _SYNC_STEP_WS_MAP.get(step)
            if mapping:
                msg, progress, default_hint = mapping
                hint = _build_step_hint(step, data) or default_hint
                task = asyncio.create_task(
                    ws_manager.broadcast_step(book_id, chapter, msg, progress, hint)
                )
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)
            if step == "publish_done":
                task = asyncio.create_task(
                    ws_manager.broadcast_complete(book_id, chapter, data or {})
                )
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)
            if step == "error":
                task = asyncio.create_task(
                    ws_manager.broadcast_error(
                        book_id,
                        chapter,
                        "error",
                        data.get("error", "未知错误") if data else "未知错误",
                    )
                )
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)
        except Exception as e:
            logger.warning(f"[{pipeline_id}] 广播进度失败: {step} — {e}")

    async def learner_cb(event_type: str, data: dict | None = None) -> None:
        try:
            learner.on_event(event_type, data or {})
            if event_type == "CHAPTER_COMPLETED":
                learner.save()
        except Exception as e:
            logger.warning(f"[{pipeline_id}] Learner 记录失败: {e}")

    makefile_obj = makefile_cls()
    _gen_start = _time.perf_counter()
    try:
        result = await makefile_obj.execute(
            {
                "action": "generate_chapter_sync",
                "book_id": book_id,
                "chapter_number": chapter,
                "mode": req.mode,
                "progress_callback": progress_cb,
                "learner_callback": learner_cb,
            }
        )
        _gen_duration = _time.perf_counter() - _gen_start
        record_generation_step = cached_import("kunlun.observability", "record_generation_step")
        record_generation_step("total", _gen_duration)
        logger.info(f"[{pipeline_id}] 全流程耗时: {_gen_duration:.2f}s")
    except Exception as e:
        logger.error(f"[{pipeline_id}] Makefile 执行异常: {e}\n{traceback.format_exc()}")
        return _build_generation_error(e, pipeline_id, chapter)

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
        "chapter_type": req.chapter_type,
        "draft": result.get("draft", ""),
        "audit_passed": result.get("audit_passed", False),
        "revisions": result.get("revisions", 0),
        "style_changes": result.get("style_changes", 0),
        "gacha_best_model": result.get("gacha_best_model", ""),
        "audit_summary": "",
        "kg_snapshot_id": result.get("kg_snapshot_id", ""),
        "message": "生成完成",
    }


@router.post("/books/{book_id}/chapters/batch-generate", summary="批量生成章节")
@_gen_rate_limit
async def batch_generate(
    book_id: str,
    request: Request,
    start: int = Query(default=1),
    end: int = Query(default=5),
    mode: str = Query(default="gacha_cascade"),
    chapter_type: str = Query(default="normal"),
) -> dict:
    """批量生成章节（推荐gacha_cascade模式控制成本）

    大范围生成使用后台任务模式：立即返回 task_id，前端通过
    GET /books/batch-status/{task_id} 轮询进度。
    """
    book_id = validate_book_id(book_id)
    start = validate_chapter_number(start)
    end = validate_chapter_number(end)
    if start > end:
        return {"success": False, "error": "start 不能大于 end"}
    if end - start > 50:
        return {"success": False, "error": "单次批量最多50章"}
    ensure_batch_cleanup()
    _batch_tasks = get_batch_tasks()

    task_id = f"batch_{book_id}_{start}_{end}_{int(time.time())}"
    _batch_tasks[task_id] = {
        "status": "running",
        "progress": 0,
        "total": end - start + 1,
        "results": [],
        "_created_at": time.time(),
    }

    batch_size = settings.batch_generate_size

    async def _run_batch():
        try:
            makefile_cls = cached_import("kunlun.agents.makefile", "Makefile")
            mf = makefile_cls()
            chapters = list(range(start, end + 1))
            for i in range(0, len(chapters), batch_size):
                batch = chapters[i : i + batch_size]
                tasks_list = [
                    mf.execute(
                        {
                            "action": "generate_chapter_sync",
                            "book_id": book_id,
                            "chapter_number": ch,
                            "mode": mode,
                            "chapter_type": chapter_type,
                        }
                    )
                    for ch in batch
                ]
                raw_results = await asyncio.gather(*tasks_list, return_exceptions=True)
                for ch, r in zip(batch, raw_results, strict=True):
                    if isinstance(r, Exception):
                        _batch_tasks[task_id]["results"].append(
                            {"chapter": ch, "success": False, "error": str(r)}
                        )
                    else:
                        assert isinstance(r, dict), f"Unexpected result type: {type(r)}"
                        _batch_tasks[task_id]["results"].append(
                            {
                                "chapter": ch,
                                "success": r.get("success", False),
                                "word_count": r.get("word_count", 0),
                                "audit_passed": r.get("audit_passed"),
                                "error": r.get("error") if not r.get("success") else None,
                            }
                        )
                _batch_tasks[task_id]["progress"] = min(i + batch_size, len(chapters))
            _batch_tasks[task_id]["status"] = "completed"
        except Exception as e:
            _batch_tasks[task_id]["status"] = "failed"
            _batch_tasks[task_id]["error"] = str(e)

    _asyncio_task = asyncio.create_task(_run_batch())  # noqa: RUF006
    return {"success": True, "task_id": task_id, "message": f"批量任务已启动 (章节 {start}-{end})"}


@router.get("/books/batch-status/{task_id}", summary="查询批量生成进度")
async def batch_status(task_id: str) -> dict:
    """查询批量生成任务的进度"""
    _batch_tasks = get_batch_tasks()
    task = _batch_tasks.get(task_id)
    if not task:
        return {"success": False, "error": "任务不存在"}
    return {
        "success": True,
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "total": task["total"],
        "results": task["results"],
        "error": task.get("error"),
    }
