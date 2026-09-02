"""
昆仑创作引擎 — AIGC 检测路由 (v2)
八维 AI 痕迹检测 + 跨章节趋势

端点:
  POST /aigc-detect/analyze — 单文本八维检测
  GET  /aigc-detect/trend   — 跨章节 AI 趋势
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import
from kunlun.api.security_middleware import validate_book_id

router = APIRouter(prefix="/aigc-detect", tags=["AIGC检测"])


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    chapter: int = Field(default=0, ge=0)
    book_id: str = Field(default="")


@router.post("/analyze")
async def aigc_analyze(req: AnalyzeRequest):
    """AI 痕迹八维检测"""
    detect = cached_import("kunlun.aigc_detect", "AIGCDetector")
    result = detect.analyze(req.text, req.chapter, req.book_id)
    return {"success": True, "data": result}


@router.get("/trend")
async def aigc_trend(book_id: str = Query(...), limit: int = Query(default=50, ge=1, le=200)):
    """AI 痕迹跨章节趋势"""
    validate_book_id(book_id)
    detect = cached_import("kunlun.aigc_detect", "AIGCDetector")
    data = detect.get_trend(book_id, limit)
    return {"success": True, "data": data}
