"""
发布平台适配器基类

所有平台适配器必须继承 BasePlatformAdapter 并实现:
- publish(chapter) -> PublishResult
- get_status(platform_id) -> PublishStatus
- validate_chapter(chapter) -> list[str]  (验证问题)
- get_platform_info() -> PlatformInfo
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PublishStatus(StrEnum):
    """发布状态"""

    DRAFT = "draft"  # 草稿
    SUBMITTED = "submitted"  # 已提交
    PUBLISHED = "published"  # 已发布
    REVIEWING = "reviewing"  # 审核中
    REJECTED = "rejected"  # 审核不通过
    FAILED = "failed"  # 发布失败
    SCHEDULED = "scheduled"  # 定时发布


@dataclass
class PlatformInfo:
    """平台信息"""

    platform_id: str = ""
    name: str = ""
    url: str = ""
    description: str = ""
    supported_genres: list[str] = field(default_factory=list)
    max_chapter_length: int = 20000
    min_chapter_length: int = 500
    requires_captcha: bool = False
    rate_limit_per_hour: int = 60


@dataclass
class PublishResult:
    """发布结果"""

    success: bool = False
    platform_id: str = ""
    platform_name: str = ""
    chapter_id: str = ""
    url: str = ""
    status: PublishStatus = PublishStatus.FAILED
    message: str = ""
    external_id: str = ""  # 平台侧 ID
    published_at: float = field(default_factory=time.time)
    error: str = ""


@dataclass
class ChapterData:
    """章节数据"""

    book_id: str = ""
    chapter_num: int = 0
    title: str = ""
    content: str = ""
    word_count: int = 0
    volume: str = ""
    author_notes: str = ""
    tags: list[str] = field(default_factory=list)
    genre: str = ""


class BasePlatformAdapter(ABC):
    """平台适配器基类"""

    @property
    @abstractmethod
    def platform_info(self) -> PlatformInfo:
        """返回平台信息"""

    @abstractmethod
    async def publish(self, chapter: ChapterData) -> PublishResult:
        """发布章节到平台"""

    @abstractmethod
    async def get_status(self, external_id: str) -> PublishStatus:
        """查询发布状态"""

    @abstractmethod
    async def validate_chapter(self, chapter: ChapterData) -> list[str]:
        """验证章节是否符合平台要求，返回问题列表"""

    async def update(self, _external_id: str, _chapter: ChapterData) -> PublishResult:
        """更新已发布章节（默认实现）"""
        return PublishResult(
            success=False,
            platform_id=self.platform_info.platform_id,
            platform_name=self.platform_info.name,
            message=f"平台 {self.platform_info.name} 不支持在线更新章节",
        )

    async def delete(self, _external_id: str) -> PublishResult:
        """删除已发布章节（默认实现）"""
        return PublishResult(
            success=False,
            platform_id=self.platform_info.platform_id,
            platform_name=self.platform_info.name,
            message=f"平台 {self.platform_info.name} 不支持在线删除章节",
        )

    async def get_publish_stats(self, _book_id: str) -> dict[str, Any]:
        """获取发布统计（默认实现）"""
        return {
            "platform_id": self.platform_info.platform_id,
            "platform_name": self.platform_info.name,
            "total_chapters": 0,
            "total_views": 0,
            "total_collections": 0,
        }

    def _validate_length(self, chapter: ChapterData) -> list[str]:
        """验证章节长度"""
        issues: list[str] = []
        info = self.platform_info
        wc = chapter.word_count or len(chapter.content)
        if wc < info.min_chapter_length:
            issues.append(f"章节字数 ({wc}) 低于平台最低要求 ({info.min_chapter_length})")
        if wc > info.max_chapter_length:
            issues.append(f"章节字数 ({wc}) 超过平台上限 ({info.max_chapter_length})")
        return issues

    def _validate_required(self, chapter: ChapterData) -> list[str]:
        """验证必填字段"""
        issues: list[str] = []
        if not chapter.title.strip():
            issues.append("章节标题不能为空")
        if not chapter.content.strip():
            issues.append("章节内容不能为空")
        return issues
