"""
晋江文学城适配器 — 女性向原创文学平台

API 参考: https://www.jjwxc.net/ (作者后台)
需要配置: JINJIANG_COOKIE / JINJIANG_TOKEN

特性:
- 章节字数: 2000-15000
- 支持: 言情/耽美/百合/无CP/衍生/随笔
- 审核机制: 人工审核为主
- VIP 章节: 支持（按章付费）
- 积分系统: 支持
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from kunlun.publish_v2.platforms.base import (
    BasePlatformAdapter,
    ChapterData,
    PlatformInfo,
    PublishResult,
    PublishStatus,
)

logger = logging.getLogger(__name__)


class JinjiangAdapter(BasePlatformAdapter):
    """晋江文学城适配器"""

    PLATFORM_ID = "jinjiang"
    PLATFORM_NAME = "晋江文学城"
    PLATFORM_URL = "https://www.jjwxc.net"
    API_BASE = "https://api.jjwxc.net/api"

    SUPPORTED_GENRES = [
        "言情",
        "耽美",
        "百合",
        "无CP",
        "衍生",
        "随笔",
        "古代",
        "现代",
        "未来",
        "穿越",
        "重生",
        "系统",
        "玄幻",
        "奇幻",
        "武侠",
        "仙侠",
        "科幻",
        "悬疑",
    ]

    def __init__(self, cookie: str = "", token: str = ""):
        self._cookie = cookie
        self._token = token
        self._last_request = 0.0

    @property
    def platform_info(self) -> PlatformInfo:
        return PlatformInfo(
            platform_id=self.PLATFORM_ID,
            name=self.PLATFORM_NAME,
            url=self.PLATFORM_URL,
            description="晋江文学城 — 女性向原创文学平台",
            supported_genres=self.SUPPORTED_GENRES,
            max_chapter_length=15000,
            min_chapter_length=2000,
            requires_captcha=True,
            rate_limit_per_hour=15,
        )

    def _headers(self) -> dict[str, str]:
        h = {"User-Agent": "Kunlun/0.4.0", "Content-Type": "application/json"}
        if self._cookie:
            h["Cookie"] = self._cookie
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request
        min_interval = 3600 / self.platform_info.rate_limit_per_hour
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request = time.time()

    async def publish(self, chapter: ChapterData) -> PublishResult:
        """发布章节到晋江文学城（需要 Cookie 认证）"""
        issues = await self.validate_chapter(chapter)
        if issues:
            return PublishResult(
                success=False,
                platform_id=self.PLATFORM_ID,
                platform_name=self.PLATFORM_NAME,
                chapter_id=f"{chapter.book_id}:ch{chapter.chapter_num}",
                message=f"验证失败: {'; '.join(issues)}",
            )

        if not self._cookie:
            return PublishResult(
                success=False,
                platform_id=self.PLATFORM_ID,
                platform_name=self.PLATFORM_NAME,
                message="未配置晋江 Cookie，请设置 JINJIANG_COOKIE 环境变量",
                status=PublishStatus.FAILED,
                error="MISSING_AUTH",
            )

        await self._rate_limit()

        payload = {
            "bookId": chapter.book_id,
            "chapterNum": chapter.chapter_num,
            "title": chapter.title,
            "content": chapter.content,
            "wordCount": chapter.word_count or len(chapter.content),
            "volume": chapter.volume or "",
            "authorNotes": chapter.author_notes or "",
            "tags": chapter.tags,
            "timestamp": int(time.time()),
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.API_BASE}/chapter/add",
                    json=payload,
                    headers=self._headers(),
                )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    return PublishResult(
                        success=True,
                        platform_id=self.PLATFORM_ID,
                        platform_name=self.PLATFORM_NAME,
                        chapter_id=f"{chapter.book_id}:ch{chapter.chapter_num}",
                        external_id=str(data.get("data", {}).get("chapterId", "")),
                        status=PublishStatus.SUBMITTED,
                        message=f"章节「{chapter.title}」已提交到晋江文学城，等待审核",
                    )
                return PublishResult(
                    success=False,
                    platform_id=self.PLATFORM_ID,
                    platform_name=self.PLATFORM_NAME,
                    message=f"API 错误: {data.get('msg', '未知')}",
                    status=PublishStatus.FAILED,
                    error=f"API_{data.get('code')}",
                )
            if resp.status_code == 401:
                return PublishResult(
                    success=False,
                    platform_id=self.PLATFORM_ID,
                    platform_name=self.PLATFORM_NAME,
                    message="Cookie 已过期，请重新登录晋江文学城作者后台",
                    status=PublishStatus.FAILED,
                    error="AUTH_EXPIRED",
                )
            return PublishResult(
                success=False,
                platform_id=self.PLATFORM_ID,
                platform_name=self.PLATFORM_NAME,
                message=f"HTTP {resp.status_code}",
                status=PublishStatus.FAILED,
                error=f"HTTP_{resp.status_code}",
            )
        except httpx.ConnectError:
            return PublishResult(
                success=False,
                platform_id=self.PLATFORM_ID,
                platform_name=self.PLATFORM_NAME,
                message="无法连接晋江文学城 API",
                status=PublishStatus.FAILED,
                error="CONNECTION_FAILED",
            )
        except httpx.TimeoutException:
            return PublishResult(
                success=False,
                platform_id=self.PLATFORM_ID,
                platform_name=self.PLATFORM_NAME,
                message="请求超时",
                status=PublishStatus.FAILED,
                error="TIMEOUT",
            )

    async def get_status(self, external_id: str) -> PublishStatus:
        if not self._cookie:
            return PublishStatus.FAILED
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.API_BASE}/chapter/status/{external_id}",
                    headers=self._headers(),
                )
            if resp.status_code == 200:
                data = resp.json()
                status_map = {
                    0: PublishStatus.DRAFT,
                    1: PublishStatus.REVIEWING,
                    2: PublishStatus.PUBLISHED,
                    3: PublishStatus.REJECTED,
                }
                return status_map.get(
                    data.get("data", {}).get("status", 0),
                    PublishStatus.SUBMITTED,
                )
        except Exception:
            pass
        return PublishStatus.SUBMITTED

    async def validate_chapter(self, chapter: ChapterData) -> list[str]:
        issues = self._validate_required(chapter)
        issues.extend(self._validate_length(chapter))
        if chapter.genre and chapter.genre not in self.SUPPORTED_GENRES:
            issues.append(f"题材 '{chapter.genre}' 不在晋江支持的分类中")
        return issues

    async def get_publish_stats(self, _book_id: str) -> dict[str, Any]:
        return {
            "platform_id": self.PLATFORM_ID,
            "platform_name": self.PLATFORM_NAME,
            "total_chapters": 0,
            "total_views": 0,
            "total_collections": 0,
            "total_reviews": 0,
            "total_points": 0,
        }
