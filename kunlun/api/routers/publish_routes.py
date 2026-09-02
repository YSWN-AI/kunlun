"""
昆仑创作引擎 — 发布引擎路由 (v2)
多平台章节格式化 + 发布计划 + 历史 + 统计

端点:
  POST /publish/{book_id}/register-platform — 注册平台配置
  POST /publish/{book_id}/format            — 格式化单章
  POST /publish/{book_id}/schedule          — 创建发布计划
  GET  /publish/{book_id}/history           — 发布历史
  GET  /publish/{book_id}/stats             — 发布统计
  GET  /publish/platform-specs              — 各平台格式规格
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import
from kunlun.api.security_middleware import validate_book_id

router = APIRouter(prefix="/publish", tags=["发布"])


class PlatformConfig(BaseModel):
    platform: str = Field(..., description="平台ID: qidian/feilu/fanqie/zongheng/qimao/other")
    pen_name: str = Field(default="", description="笔名")
    schedule_enabled: bool = Field(default=False)
    auto_publish: bool = Field(default=False)
    extra_params: dict = Field(default_factory=dict)


class FormatRequest(BaseModel):
    chapter: int = Field(..., ge=1)
    content: str = Field(..., min_length=1)
    platform: str = Field(default="qidian")


class ScheduleRequest(BaseModel):
    platform: str = Field(..., description="目标平台")
    start_chapter: int = Field(..., ge=1)
    end_chapter: int = Field(default=0, description="0=全部")
    interval_hours: float = Field(default=12.0, description="发布间隔（小时）")
    start_time: str = Field(default="", description="首章发布时间 (ISO 8601)")


@router.post("/{book_id}/register-platform")
async def register_platform(book_id: str, req: PlatformConfig):
    """注册平台配置"""
    validate_book_id(book_id)
    pub = cached_import("kunlun.publish.engine", "PublishEngine")
    engine = pub.get_factory(book_id)
    engine.register_platform(req.platform, req.dict())
    return {"success": True, "message": f"平台 '{req.platform}' 已注册"}


@router.post("/{book_id}/format")
async def format_chapter(book_id: str, req: FormatRequest):
    """格式化单章为平台格式"""
    validate_book_id(book_id)
    pub = cached_import("kunlun.publish.engine", "PublishEngine")
    engine = pub.get_factory(book_id)
    result = engine.format_chapter(req.chapter, req.content, req.platform)
    return {"success": True, "data": result}


@router.post("/{book_id}/schedule")
async def create_schedule(book_id: str, req: ScheduleRequest):
    """创建发布计划"""
    validate_book_id(book_id)
    pub = cached_import("kunlun.publish.engine", "PublishEngine")
    engine = pub.get_factory(book_id)
    plan = engine.create_schedule(
        req.platform,
        req.start_chapter,
        req.end_chapter,
        req.interval_hours,
        req.start_time,
    )
    return {"success": True, "data": plan}


@router.get("/{book_id}/history")
async def publish_history(book_id: str):
    """发布历史"""
    validate_book_id(book_id)
    pub = cached_import("kunlun.publish.engine", "PublishEngine")
    engine = pub.get_factory(book_id)
    return {"success": True, "data": engine.get_history()}


@router.get("/{book_id}/stats")
async def publish_stats(book_id: str):
    """发布统计"""
    validate_book_id(book_id)
    pub = cached_import("kunlun.publish.engine", "PublishEngine")
    engine = pub.get_factory(book_id)
    return {"success": True, "data": engine.get_stats()}


@router.get("/platform-specs")
async def platform_specs():
    """各平台格式规格"""
    pub = cached_import("kunlun.publish.engine", "PublishEngine")
    return {"success": True, "data": pub.get_platform_specs()}
