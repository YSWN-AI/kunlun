"""
昆仑创作引擎 — 平台合规路由 (v2)
5平台 AI 政策检测 + 洗稿定位

端点:
  POST /compliance/check              — 单平台合规检测
  POST /compliance/check-all          — 多平台批量合规检测
  GET  /compliance/platform-policies  — 获取各平台 AI 政策
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import

router = APIRouter(prefix="/compliance", tags=["合规"])


class ComplianceCheckRequest(BaseModel):
    content: str = Field(..., min_length=1, description="待检测文本")
    platform: str = Field(..., description="平台: qidian/feilu/fanqie/zongheng/qimao")
    chapter: int = Field(default=0, ge=0)
    book_id: str = Field(default="")


class BatchCheckRequest(BaseModel):
    content: str = Field(..., min_length=1)
    platforms: list[str] = Field(..., min_length=1)
    book_id: str = Field(default="")
    chapter: int = Field(default=0, ge=0)


@router.post("/check")
async def compliance_check(req: ComplianceCheckRequest):
    """单平台合规检测"""
    compliance = cached_import("kunlun.platform_compliance", "ComplianceChecker")
    result = compliance.check(req.content, req.platform, req.book_id, req.chapter)
    return {"success": True, "data": result}


@router.post("/check-all")
async def compliance_check_all(req: BatchCheckRequest):
    """多平台批量合规检测"""
    compliance = cached_import("kunlun.platform_compliance", "ComplianceChecker")
    results = {}
    for platform in req.platforms:
        results[platform] = compliance.check(req.content, platform, req.book_id, req.chapter)
    return {"success": True, "data": results}


@router.get("/platform-policies")
async def platform_policies():
    """获取各平台 AI 政策"""
    compliance = cached_import("kunlun.platform_compliance", "ComplianceChecker")
    return {"success": True, "data": compliance.get_policies()}
