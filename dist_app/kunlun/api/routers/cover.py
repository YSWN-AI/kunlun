"""
昆仑创作引擎 — 封面生成路由 (v2)
AI 封面提示词生成 + 风格列表

端点:
  POST /cover/generate-prompt — 生成封面提示词
  GET  /cover/styles         — 获取封面风格列表
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import
from kunlun.api.security_middleware import validate_book_id

router = APIRouter(prefix="/cover", tags=["封面"])


class GeneratePromptRequest(BaseModel):
    book_id: str = Field(...)
    style: str = Field(default="xianxia", description="风格: xianxia/wuxia/xuanhuan/...")
    elements: list[str] = Field(default_factory=list, description="关键元素")
    color_scheme: str = Field(default="", description="配色方案")
    text: str = Field(default="", description="封面文字")


@router.post("/generate-prompt")
async def generate_cover_prompt(req: GeneratePromptRequest):
    """生成封面提示词"""
    validate_book_id(req.book_id)
    cover = cached_import("kunlun.cover", "CoverEngine")
    prompt = cover.generate_prompt(req.book_id, req.style, req.elements, req.color_scheme, req.text)
    return {"success": True, "data": {"prompt": prompt}}


@router.get("/styles")
async def cover_styles():
    """获取封面风格列表"""
    cover = cached_import("kunlun.cover", "CoverEngine")
    return {"success": True, "data": cover.get_styles()}
