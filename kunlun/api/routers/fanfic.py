"""
昆仑创作引擎 — 同人创作路由 (v2)
正典导入 + OOC 检测 + 上下文

端点:
  POST /fanfic/import-canon — 导入正典数据
  POST /fanfic/ooc-check   — OOC 检测
  GET  /fanfic/context     — 获取同人创作上下文
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import
from kunlun.api.security_middleware import validate_book_id

router = APIRouter(prefix="/fanfic", tags=["同人"])


class ImportCanonRequest(BaseModel):
    book_id: str = Field(...)
    source: str = Field(default="upload", description="来源: upload/url/title")
    data: dict = Field(default_factory=dict)
    title: str = Field(default="")


class OOCCheckRequest(BaseModel):
    book_id: str = Field(...)
    chapter: int = Field(default=0, ge=0)
    content: str = Field(..., min_length=1)
    character: str = Field(default="", description="指定角色名（空=检查全部）")


@router.post("/import-canon")
async def import_canon(req: ImportCanonRequest):
    """导入正典数据"""
    validate_book_id(req.book_id)
    fanfic = cached_import("kunlun.fanfic", "FanficEngine")
    engine = fanfic.get_factory(req.book_id)
    result = engine.import_canon(req.source, req.data, req.title)
    return {"success": True, "data": result}


@router.post("/ooc-check")
async def ooc_check(req: OOCCheckRequest):
    """OOC 检测"""
    validate_book_id(req.book_id)
    fanfic = cached_import("kunlun.fanfic", "FanficEngine")
    engine = fanfic.get_factory(req.book_id)
    result = engine.check_ooc(req.chapter, req.content, req.character)
    return {"success": True, "data": result}


@router.get("/context")
async def fanfic_context(book_id: str = Query(...)):
    """获取同人创作上下文"""
    validate_book_id(book_id)
    fanfic = cached_import("kunlun.fanfic", "FanficEngine")
    engine = fanfic.get_factory(book_id)
    return {"success": True, "data": engine.get_context()}
