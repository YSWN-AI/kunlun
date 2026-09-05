"""
昆仑创作引擎 — 智能学习 API 路由

提供偏好提取、学习记录管理、统计和清空端点。

端点:
  POST   /smart-learn/extract            — 从反馈提取偏好
  POST   /smart-learn/extract-from-edit  — 从修改提取偏好
  POST   /smart-learn/record             — 添加学习记录
  GET    /smart-learn/history            — 学习历史列表
  GET    /smart-learn/stats              — 学习统计
  DELETE /smart-learn/clear              — 清空历史
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from loguru import logger
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import

router = APIRouter(prefix="/smart-learn", tags=["智能学习"])


# ─── 请求模型 ─────────────────────────────────────────────


class ExtractFeedbackRequest(BaseModel):
    feedback: str = Field(..., description="用户反馈文本")


class ExtractEditRequest(BaseModel):
    original: str = Field(..., description="原始文本")
    modified: str = Field(..., description="修改后的文本")


class AddRecordRequest(BaseModel):
    book_id: str = Field(..., description="作品ID")
    record: dict = Field(..., description="学习记录（通常来自 extract 接口返回）")


# ─── 路由端点 ─────────────────────────────────────────────


def _get_extractor():
    """获取偏好提取器（延迟导入）"""
    return cached_import("kunlun.smart_learn", "get_preference_extractor")()


def _get_history():
    """获取学习历史管理器（延迟导入）"""
    return cached_import("kunlun.smart_learn", "get_learning_history")()


@router.post("/extract", summary="从反馈提取偏好")
async def extract_from_feedback(req: ExtractFeedbackRequest) -> dict:
    """从自然语言反馈中自动提取写作偏好。

    支持常见反馈类型：对话/风格/节奏/人物/情节/结构。
    返回偏好字典，可直接传入 /record 接口保存。
    """
    extractor = _get_extractor()
    pref = extractor.extract_from_feedback(req.feedback)
    return {
        "success": True,
        "data": pref,
    }


@router.post("/extract-from-edit", summary="从修改提取偏好")
async def extract_from_edit(req: ExtractEditRequest) -> dict:
    """通过对比原文和修改后的文本，推断用户的写作偏好。

    分析修改幅度、修改类型（删减/增加/对话调整等），输出偏好。
    """
    extractor = _get_extractor()
    pref = extractor.extract_from_edit(req.original, req.modified)
    return {
        "success": True,
        "data": pref,
    }


@router.post("/record", summary="添加学习记录")
async def add_record(req: AddRecordRequest) -> dict:
    """添加一条学习记录到指定书籍。

    record 通常来自 /extract 或 /extract-from-edit 接口的返回值。
    """
    logger.info(f"[SmartLearn] 添加记录: book={req.book_id}")
    history = _get_history()
    ok = history.add_record(req.book_id, req.record)
    if not ok:
        return {"success": False, "error": "记录添加失败"}
    return {
        "success": True,
        "message": "学习记录已添加",
        "data": {"book_id": req.book_id},
    }


@router.get("/history", summary="学习历史列表")
async def get_history(
    book_id: str = Query(..., description="作品ID"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量"),
    category: str | None = Query(
        default=None,
        description="分类筛选: dialogue/style/pace/character/plot/structure",
    ),
) -> dict:
    """获取指定书籍的学习历史记录，按时间倒序排列。"""
    history = _get_history()
    records = history.list_records(book_id, limit=limit, category=category)
    return {
        "success": True,
        "data": records,
        "total": len(records),
    }


@router.get("/stats", summary="学习统计")
async def get_stats(
    book_id: str = Query(..., description="作品ID"),
) -> dict:
    """获取学习统计信息，包含总记录数、各分类数量、类型分布、趋势、Top偏好。"""
    history = _get_history()
    stats = history.get_stats(book_id)
    return {
        "success": True,
        "data": stats,
    }


@router.delete("/clear", summary="清空历史")
async def clear_history(
    book_id: str = Query(..., description="作品ID"),
) -> dict:
    """清空指定书籍的所有学习历史记录（不可恢复）。"""
    logger.warning(f"[SmartLearn] 清空历史: book={book_id}")
    history = _get_history()
    ok = history.clear_history(book_id)
    if not ok:
        return {"success": False, "error": "清空失败"}
    return {
        "success": True,
        "message": f"书籍 {book_id} 的学习历史已清空",
    }
