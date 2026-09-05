"""
昆仑创作引擎 — 书架作品管理 数据模型

Pydantic v2 模型，定义书架书籍卡片、分组等结构。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BookCard(BaseModel):
    """书架书籍卡片信息。"""

    id: str = Field(default="", description="书籍ID")
    title: str = Field(default="未命名", description="作品名称")
    cover: str = Field(default="", description="封面图片路径或URL")
    genre: str = Field(default="", description="题材")
    word_count: int = Field(default=0, ge=0, description="总字数")
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="写作进度百分比")
    last_modified: str = Field(default="", description="最后修改时间")
    group: str = Field(default="default", description="所属分组ID")
    tags: list[str] = Field(default_factory=list, description="标签")
    status: str = Field(default="创作中", description="状态（创作中/已完成/已暂停）")
    chapter_count: int = Field(default=0, ge=0, description="章节数量")
    target_chapters: int = Field(default=100, ge=0, description="目标章节数")
    current_chapter: int = Field(default=0, ge=0, description="当前章节序号")
    quality_score: float = Field(default=0.0, ge=0.0, le=100.0, description="质量评分")
    outline_ready: bool = Field(default=False, description="大纲是否就绪")
    world_ready: bool = Field(default=False, description="世界观是否就绪")
    characters_ready: bool = Field(default=False, description="人物是否就绪")
    in_recycle: bool = Field(default=False, description="是否在回收站中")


class GroupInfo(BaseModel):
    """书架分组信息。"""

    id: str = Field(default="", description="分组ID")
    name: str = Field(default="", description="分组名称")
    book_count: int = Field(default=0, ge=0, description="分组内书籍数量")
    created_at: str = Field(default="", description="创建时间")


class CreateGroupRequest(BaseModel):
    """创建分组请求。"""

    name: str = Field(..., min_length=1, max_length=50, description="分组名称")


class MoveToGroupRequest(BaseModel):
    """移动书籍到分组请求。"""

    group_id: str = Field(..., description="目标分组ID")


class QuickActions(BaseModel):
    """书籍快速操作信息。"""

    book_id: str = Field(default="", description="书籍ID")
    continue_writing: dict = Field(default_factory=dict, description="继续写作信息")
    view_outline: dict = Field(default_factory=dict, description="查看大纲信息")
    quality_report: dict = Field(default_factory=dict, description="质量报告信息")
    export: dict = Field(default_factory=dict, description="导出信息")
