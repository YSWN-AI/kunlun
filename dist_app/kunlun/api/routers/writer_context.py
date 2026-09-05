"""
昆仑创作引擎 — Writer 上下文压缩路由 (v2)
对标 StoryWriter ReIO，3级保留优先级

端点:
  POST /writer-context/{book_id}/register         — 注册章节到上下文记忆
  GET  /writer-context/{book_id}/build/{chapter}  — 构建压缩上下文
  GET  /writer-context/{book_id}/statistics       — 上下文记忆统计
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import
from kunlun.api.security_middleware import validate_book_id

router = APIRouter(prefix="/writer-context", tags=["上下文压缩"])


class RegisterChapterRequest(BaseModel):
    book_id: str = Field(...)
    chapter: int = Field(..., ge=1)
    content: str = Field(..., min_length=1)
    summary: str = Field(default="")


@router.post("/{book_id}/register")
async def register_context(book_id: str, req: RegisterChapterRequest):
    """注册章节到上下文记忆"""
    validate_book_id(book_id)
    ctx = cached_import("kunlun.writer_context", "WriterContext")
    mgr = ctx.get_factory(book_id)
    mgr.register(req.chapter, req.content, req.summary)
    return {"success": True, "message": f"第{req.chapter}章已注册"}


@router.get("/{book_id}/build/{target_chapter}")
async def build_context(book_id: str, target_chapter: int):
    """构建压缩上下文"""
    validate_book_id(book_id)
    ctx = cached_import("kunlun.writer_context", "WriterContext")
    mgr = ctx.get_factory(book_id)
    data = mgr.build(target_chapter)
    return {"success": True, "data": data}


@router.get("/{book_id}/statistics")
async def context_statistics(book_id: str):
    """上下文记忆统计"""
    validate_book_id(book_id)
    ctx = cached_import("kunlun.writer_context", "WriterContext")
    mgr = ctx.get_factory(book_id)
    return {"success": True, "data": mgr.get_statistics()}
