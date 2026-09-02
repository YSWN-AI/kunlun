"""
昆仑创作引擎 — 三层规则系统路由 (v2)
通用→题材→书籍规则堆栈

端点:
  GET  /rules/stack  — 获取规则堆栈
  GET  /rules/export — 导出规则
"""

from fastapi import APIRouter, Query

from kunlun.api.routers._shared import cached_import
from kunlun.api.security_middleware import validate_book_id

router = APIRouter(prefix="/rules", tags=["规则"])


@router.get("/stack")
async def rules_stack(book_id: str = Query(...)):
    """获取三层规则堆栈（通用→题材→书籍）"""
    validate_book_id(book_id)
    rules = cached_import("kunlun.rules", "RulesEngine")
    return {"success": True, "data": rules.get_stack(book_id)}


@router.get("/export")
async def rules_export(book_id: str = Query(...)):
    """导出规则堆栈"""
    validate_book_id(book_id)
    rules = cached_import("kunlun.rules", "RulesEngine")
    return {"success": True, "data": rules.export_stack(book_id)}
