"""
发布管线 V2 模块 — 多平台一键发布

支持 5 大主流平台:
- 起点中文网 (qidian)
- 番茄小说 (fanqie)
- 晋江文学城 (jinjiang)
- 纵横中文网 (zongheng)
- 飞卢小说网 (feilu)

功能:
- 一键多平台发布
- 定时发布调度
- 格式自动适配
- SEO 标题/标签优化
- 发布状态追踪

用法:
    from kunlun.publish_v2 import PublishV2Engine, publish_v2_engine

    results = await publish_v2_engine.publish_chapter(
        book_id="book_001",
        chapter_num=42,
        platforms=["qidian", "fanqie"],
    )
"""

from __future__ import annotations

from kunlun.publish_v2.engine import PublishV2Engine, publish_v2_engine
from kunlun.publish_v2.formatter import FormatAdapter, TextStats
from kunlun.publish_v2.platforms.base import (
    ChapterData,
    PlatformInfo,
    PublishResult,
    PublishStatus,
)
from kunlun.publish_v2.scheduler import PublishSchedule, PublishScheduler, ScheduleStatus
from kunlun.publish_v2.seo_optimizer import SEOOptimizer, SEOOptimizeResult

__all__ = [
    "ChapterData",
    "FormatAdapter",
    "PlatformInfo",
    "PublishResult",
    "PublishSchedule",
    "PublishScheduler",
    "PublishStatus",
    "PublishV2Engine",
    "SEOOptimizeResult",
    "SEOOptimizer",
    "ScheduleStatus",
    "TextStats",
    "publish_v2_engine",
]
