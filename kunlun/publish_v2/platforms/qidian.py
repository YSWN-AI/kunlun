"""
起点中文网适配器 — 阅文集团旗下最大原创文学平台

API 参考: https://writer.qidian.com/ (作家专区)
需要配置: QIDIAN_COOKIE / QIDIAN_TOKEN

特性:
- 章节字数: 1000-20000
- 支持: 玄幻/奇幻/武侠/仙侠/都市/现实/历史/军事/游戏/体育/科幻/悬疑
- 审核机制: 自动审核 + 人工复审
- 定时发布: 支持
- VIP 章节: 支持
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


class QidianAdapter(BasePlatformAdapter):
    """起点中文网适配器"""

    PLATFORM_ID = "qidian"
    PLATFORM_NAME = "起点中文网"
    PLATFORM_URL = "https://www.qidian.com"
    API_BASE = "https://writer.qidian.com/api"

    SUPPORTED_GENRES = [
        "玄幻",
        "奇幻",
        "武侠",
        "仙侠",
        "都市",
        "现实",
        "历史",
        "军事",
        "游戏",
        "体育",
        "科幻",
        "悬疑灵异",
        "轻小说",
        "短篇",
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
            description="起点中文网 — 阅文集团旗下最大原创文学平台",
            supported_genres=self.SUPPORTED_GENRES,
            max_chapter_length=20000,
            min_chapter_length=1000,
            requires_captcha=False,
            rate_limit_per_hour=30,
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
        """发布章节到起点（需要 Cookie 认证）"""
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
                message="未配置起点 Cookie，请设置 QIDIAN_COOKIE 环境变量",
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
                        message=f"章节「{chapter.title}」已提交，等待审核",
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
                    message="Cookie 已过期，请重新登录起点作家专区",
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
                message="无法连接起点 API",
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
            issues.append(f"题材 '{chapter.genre}' 不在起点支持的分类中")
        return issues

    async def get_publish_stats(self, book_id: str) -> dict[str, Any]:
        if not self._cookie:
            return super().get_publish_stats(book_id)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.API_BASE}/book/stats/{book_id}",
                    headers=self._headers(),
                )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                return {
                    "platform_id": self.PLATFORM_ID,
                    "platform_name": self.PLATFORM_NAME,
                    "total_chapters": data.get("totalChapters", 0),
                    "total_views": data.get("totalViews", 0),
                    "total_collections": data.get("totalCollections", 0),
                }
        except Exception:
            pass
        return super().get_publish_stats(book_id)
