"""
昆仑创作引擎 — 审计路由
/audit/run
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import

router = APIRouter(tags=["审计"])


class AuditRequest(BaseModel):
    draft: str = Field(..., description="待审计文本")
    chapter: int = Field(default=1, description="章节号")
    chapter_type: str = Field(default="normal", description="章节类型")


class AuditResponse(BaseModel):
    success: bool
    data: dict | None = None


@router.post(
    "/audit/run",
    response_model=AuditResponse,
    summary="运行审计",
    description="对一段正文运行18道门禁审计（弧线/信息/压AI/爽点间隔/爽点多样性/情绪/对话/战斗），返回审计报告。",
)
async def run_audit(req: AuditRequest) -> dict:
    auditor_cls = cached_import("kunlun.agents.auditor", "Auditor")

    auditor = auditor_cls()
    result = await auditor.execute(
        {
            "draft": req.draft,
            "blueprint": {"chapter": req.chapter, "chapter_type": req.chapter_type},
            "kg_snapshot_id": "",
        }
    )
    return {"success": True, "data": result}
