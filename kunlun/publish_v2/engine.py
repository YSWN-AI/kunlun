"""
发布管线 V2 引擎 — 多平台一键发布核心

支持:
- 5 大平台一键发布（起点/番茄/晋江/纵横/飞卢）
- 定时发布调度
- 格式自动适配
- SEO 优化
- 发布状态追踪
- 批量发布

用法:
    from kunlun.publish_v2 import PublishV2Engine

    engine = PublishV2Engine()
    results = await engine.publish_chapter(
        book_id="book_001",
        chapter_num=42,
        platforms=["qidian", "fanqie", "jinjiang"],
    )
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from kunlun.publish_v2.formatter import FormatAdapter
from kunlun.publish_v2.platforms.base import PublishResult
from kunlun.publish_v2.platforms.fanqie import FanqieAdapter
from kunlun.publish_v2.platforms.feilu import FeiluAdapter
from kunlun.publish_v2.platforms.jinjiang import JinjiangAdapter
from kunlun.publish_v2.platforms.qidian import QidianAdapter
from kunlun.publish_v2.platforms.zongheng import ZonghengAdapter
from kunlun.publish_v2.scheduler import PublishScheduler
from kunlun.publish_v2.seo_optimizer import SEOOptimizer

logger = logging.getLogger(__name__)


class PublishV2Engine:
    """发布管线 V2 引擎

    统一管理多平台发布，提供:
    - 平台适配器注册与管理
    - 一键发布到多平台
    - 定时发布调度
    - 格式转换与 SEO 优化
    - 发布状态追踪

    用法:
        engine = PublishV2Engine()
        await engine.publish_chapter("book_001", 42, ["qidian"])
    """

    def __init__(self):
        self._adapters: dict[str, Any] = {}
        self._scheduler = PublishScheduler(self)
        self._formatter = FormatAdapter()
        self._seo = SEOOptimizer()

        # 注册默认平台适配器
        self._register_default_adapters()

    @property
    def scheduler(self) -> PublishScheduler:
        return self._scheduler

    @property
    def formatter(self) -> FormatAdapter:
        return self._formatter

    @property
    def seo(self) -> SEOOptimizer:
        return self._seo

    @property
    def supported_platforms(self) -> list[str]:
        return list(self._adapters.keys())

    def _register_default_adapters(self) -> None:
        """注册默认平台适配器"""
        self._adapters["qidian"] = QidianAdapter()
        self._adapters["fanqie"] = FanqieAdapter()
        self._adapters["jinjiang"] = JinjiangAdapter()
        self._adapters["zongheng"] = ZonghengAdapter()
        self._adapters["feilu"] = FeiluAdapter()

    def register_adapter(self, platform_id: str, adapter) -> None:
        """注册自定义平台适配器"""
        self._adapters[platform_id] = adapter
        logger.info("Platform adapter registered: %s", platform_id)

    def get_adapter(self, platform_id: str):
        """获取平台适配器"""
        return self._adapters.get(platform_id)

    def get_platform_info(self, platform_id: str) -> dict[str, Any] | None:
        """获取平台信息"""
        adapter = self._adapters.get(platform_id)
        if not adapter:
            return None
        info = adapter.platform_info
        return {
            "platform_id": info.platform_id,
            "name": info.name,
            "url": info.url,
            "description": info.description,
            "supported_genres": info.supported_genres,
            "max_chapter_length": info.max_chapter_length,
            "min_chapter_length": info.min_chapter_length,
        }

    def list_all_platforms(self) -> list[dict[str, Any]]:
        """列出所有支持的平台"""
        return [
            self.get_platform_info(pid) for pid in self._adapters if self.get_platform_info(pid)
        ]

    async def publish_chapter(
        self,
        book_id: str,
        chapter_num: int,
        platforms: list[str],
        title: str = "",
        content: str = "",
        genre: str = "",
        tags: list[str] | None = None,
        optimize_seo: bool = True,
    ) -> list[PublishResult]:
        """发布章节到多个平台

        Args:
            book_id: 书籍 ID
            chapter_num: 章节编号
            platforms: 目标平台列表
            title: 章节标题
            content: 章节内容
            genre: 题材
            tags: 标签
            optimize_seo: 是否 SEO 优化

        Returns:
            list[PublishResult]: 每个平台的发布结果
        """
        if not platforms:
            return []

        # SEO 优化
        optimized_title = title
        optimized_tags = tags or []
        if optimize_seo and title and content:
            seo_result = self._seo.optimize(title, content, genre=genre)
            optimized_title = seo_result.optimized_title
            optimized_tags = list(set(optimized_tags + seo_result.suggested_tags))

        # 格式转换
        html_content = self._formatter.markdown_to_html(content)

        from kunlun.publish_v2.platforms.base import ChapterData

        chapter = ChapterData(
            book_id=book_id,
            chapter_num=chapter_num,
            title=optimized_title,
            content=html_content,
            word_count=self._formatter.estimate_word_count(content),
            tags=optimized_tags,
            genre=genre,
        )

        # 并发发布
        tasks = []
        platform_ids = []
        for pid in platforms:
            adapter = self._adapters.get(pid)
            if adapter:
                tasks.append(adapter.publish(chapter))
                platform_ids.append(pid)
            else:
                logger.warning("Unknown platform: %s", pid)

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)

        publish_results: list[PublishResult] = []
        for pid, result in zip(platform_ids, results, strict=False):
            if isinstance(result, Exception):
                publish_results.append(
                    PublishResult(
                        success=False,
                        platform_id=pid,
                        platform_name=pid,
                        message=f"发布异常: {result}",
                        error=str(result),
                    )
                )
            else:
                publish_results.append(result)

        return publish_results

    async def schedule_publish(
        self,
        book_id: str,
        chapter_num: int,
        platforms: list[str],
        chapter_title: str = "",
        publish_at: float = 0.0,
    ) -> str:
        """定时发布章节，返回 schedule_id"""
        return self._scheduler.schedule(
            book_id=book_id,
            chapter_num=chapter_num,
            platforms=platforms,
            chapter_title=chapter_title,
            publish_at=publish_at,
        )

    async def run_scheduled(self) -> list[PublishResult]:
        """执行所有到期发布计划"""
        schedules = await self._scheduler.run_pending()
        results: list[PublishResult] = []
        for s in schedules:
            for pid, status in s.results.items():
                results.append(
                    PublishResult(
                        success=status == "completed",
                        platform_id=pid,
                        chapter_id=f"{s.book_id}:ch{s.chapter_num}",
                    )
                )
        return results

    async def validate_chapter(
        self,
        book_id: str,
        chapter_num: int,
        platforms: list[str],
        title: str = "",
        content: str = "",
    ) -> dict[str, list[str]]:
        """验证章节在各平台的合规性"""
        from kunlun.publish_v2.platforms.base import ChapterData

        chapter = ChapterData(
            book_id=book_id,
            chapter_num=chapter_num,
            title=title,
            content=content,
            word_count=len(content),
        )

        issues: dict[str, list[str]] = {}
        for pid in platforms:
            adapter = self._adapters.get(pid)
            if adapter:
                platform_issues = await adapter.validate_chapter(chapter)
                if platform_issues:
                    issues[pid] = platform_issues

        return issues

    async def get_publish_status(
        self,
        platform_id: str,
        external_id: str,
    ):
        """查询发布状态"""
        adapter = self._adapters.get(platform_id)
        if not adapter:
            return None
        return await adapter.get_status(external_id)

    async def get_publish_stats(
        self,
        book_id: str,
        platforms: list[str] | None = None,
    ) -> dict[str, Any]:
        """获取发布统计"""
        target_platforms = platforms or list(self._adapters.keys())
        stats: dict[str, Any] = {}
        for pid in target_platforms:
            adapter = self._adapters.get(pid)
            if adapter:
                stats[pid] = await adapter.get_publish_stats(book_id)
        return stats

    def get_stats(self) -> dict[str, Any]:
        """获取引擎统计"""
        return {
            "supported_platforms": self.supported_platforms,
            "scheduler": self._scheduler.get_stats(),
        }


# 全局单例
publish_v2_engine = PublishV2Engine()
