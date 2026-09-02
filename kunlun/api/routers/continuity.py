"""
昆仑创作引擎 — 连续性检查路由 (v2)
7项确定性检查 + 快照 diff

端点:
  POST /continuity/check     — 连续性检查
  GET  /continuity/snapshots — 快照列表
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import
from kunlun.api.security_middleware import validate_book_id

router = APIRouter(prefix="/continuity", tags=["连续性"])


class ContinuityCheckRequest(BaseModel):
    book_id: str = Field(...)
    chapter: int = Field(..., ge=1)
    content: str = Field(default="")


@router.post("/check")
async def continuity_check(req: ContinuityCheckRequest):
    """7项确定性连续性检查（零 LLM 成本）"""
    validate_book_id(req.book_id)
    engine = cached_import("kunlun.continuity", "ContinuityEngine")
    result = engine.check(req.book_id, req.chapter, req.content)
    return {"success": True, "data": result}


@router.get("/snapshots")
async def continuity_snapshots(
    book_id: str = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
):
    """获取连续性快照列表"""
    validate_book_id(book_id)
    engine = cached_import("kunlun.continuity", "ContinuityEngine")
    data = engine.list_snapshots(book_id, limit)
    return {"success": True, "data": data}
