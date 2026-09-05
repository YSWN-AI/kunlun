"""
昆仑创作引擎 — 偏好学习路由 (v2)
/books/{book_id}/preferences: 获取/记录学习偏好
"""

from fastapi import APIRouter, Query
from loguru import logger

from kunlun.api.routers._shared import cached_import

router = APIRouter(prefix="/books", tags=["偏好学习"])


@router.get("/{book_id}/preferences", summary="获取偏好")
async def get_preferences(book_id: str) -> dict:
    """获取当前书籍的学习偏好向量，包含 Top20 关键词、风格/叙事/内容/结构/门禁分组，\
以及 LLM 偏好提示"""
    get_learner = cached_import("kunlun.learn", "get_learner")
    learner = get_learner(book_id)
    return {
        "success": True,
        "data": {
            "book_id": book_id,
            "top_preferences": learner.prefs.top_preferences(20),
            "groups": {
                "style": learner.prefs.get_group("style"),
                "narrative": learner.prefs.get_group("narrative"),
                "content": learner.prefs.get_group("content"),
                "structure": learner.prefs.get_group("structure"),
                "gates": learner.prefs.get_group("gates"),
            },
            "prompt_hints": learner.get_prompt_hints(),
        },
    }


@router.post("/{book_id}/preferences/feedback", summary="记录反馈")
async def record_feedback(
    book_id: str,
    feedback: str = Query(default="", description="反馈文本"),
    rating: int = Query(default=0, description="评分 (-2~+2)", ge=-2, le=2),
) -> dict:
    """记录作者主动反馈。rating 取值范围 -2（强烈不喜欢）到 +2（非常喜欢），0 为中性。"""
    get_learner = cached_import("kunlun.learn", "get_learner")
    learner = get_learner(book_id)
    learner.on_event("AUTHOR_FEEDBACK", {"feedback": feedback, "rating": rating})
    learner.save()
    try:
        auto_sync = cached_import("kunlun.autosync", "AutoSync")
        await auto_sync.trigger("feedback_given", {"book_id": book_id, "rating": rating})
    except Exception as e:
        logger.debug(f"Feedback 自动同步跳过: {e}")
    return {"success": True, "message": f"已记录反馈 (rating={rating})"}
