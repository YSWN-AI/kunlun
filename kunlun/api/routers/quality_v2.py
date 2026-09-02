"""
昆仑创作引擎 — 质量 v2 路由
8维零LLM质量评估 + 趋势 + 雷达

端点:
  POST /quality-v2/evaluate       — 8维质量评估
  GET  /quality-v2/trend/{book_id} — 全书质量趋势
  GET  /quality-v2/radar/{book_id} — 质量雷达图
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import
from kunlun.api.security_middleware import validate_book_id

router = APIRouter(prefix="/quality-v2", tags=["质量"])


class EvaluateRequest(BaseModel):
    book_id: str = Field(...)
    chapter: int = Field(..., ge=1)
    content: str = Field(..., min_length=1)


@router.post("/evaluate")
async def quality_evaluate(req: EvaluateRequest):
    """8维质量评估（零 LLM 成本）"""
    validate_book_id(req.book_id)
    quality = cached_import("kunlun.quality.engine", "QualityEngine")
    result = quality.evaluate(req.book_id, req.chapter, req.content)
    return {"success": True, "data": result}


@router.get("/trend/{book_id}")
async def quality_trend(book_id: str):
    """全书质量趋势"""
    validate_book_id(book_id)
    quality = cached_import("kunlun.quality.engine", "QualityEngine")
    return {"success": True, "data": quality.get_trend(book_id)}


@router.get("/radar/{book_id}")
async def quality_radar(book_id: str):
    """质量雷达图数据"""
    validate_book_id(book_id)
    quality = cached_import("kunlun.quality.engine", "QualityEngine")
    return {"success": True, "data": quality.get_radar(book_id)}
