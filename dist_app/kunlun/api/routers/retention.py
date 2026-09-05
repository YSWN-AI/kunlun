"""
昆仑创作引擎 — 追读力分析路由 (v2)
6类钩子 + 12类爽点 + 5平台适配

端点:
  POST /retention/analyze — 追读力分析
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import

router = APIRouter(prefix="/retention", tags=["追读力"])


class RetentionAnalyzeRequest(BaseModel):
    book_id: str = Field(...)
    chapter: int = Field(..., ge=1)
    content: str = Field(..., min_length=1)
    platform: str = Field(default="qidian")


@router.post("/analyze")
async def retention_analyze(req: RetentionAnalyzeRequest):
    """追读力分析 — Hook/爽点/兑现/债务"""
    retention = cached_import("kunlun.retention.engine", "RetentionEngine")
    result = retention.analyze(req.book_id, req.chapter, req.content, req.platform)
    return {"success": True, "data": result}
