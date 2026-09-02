"""
昆仑创作引擎 — 统一通知推送系统核心引擎

整合多渠道通知：Telegram / 飞书 / 企业微信 / 通用 Webhook。
支持 HMAC-SHA256 签名、飞书卡片消息、企微 Markdown 消息。
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx
from loguru import logger

from kunlun.config import settings

# ─── 枚举 ──────────────────────────────────────────


class NotifyLevel(Enum):
    """通知等级"""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotifyChannel(Enum):
    """通知渠道"""

    TELEGRAM = "telegram"
    FEISHU = "feishu"
    WECOM = "wecom"
    WEBHOOK = "webhook"
    LOG = "log"


# ─── 数据模型 ────────────────────────────────────────


@dataclass
class NotifyMessage:
    """通知消息"""

    title: str
    content: str
    level: NotifyLevel = NotifyLevel.INFO
    source: str = "kunlun"
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


# ─── 通知器基类 ──────────────────────────────────────


class BaseNotifier:
    """通知器基类"""

    channel: NotifyChannel

    async def send(self, msg: NotifyMessage) -> bool:
        raise NotImplementedError

    def _emoji(self, level: NotifyLevel) -> str:
        return {
            NotifyLevel.INFO: "ℹ️",
            NotifyLevel.SUCCESS: "✅",
            NotifyLevel.WARNING: "⚠️",
            NotifyLevel.ERROR: "❌",
            NotifyLevel.CRITICAL: "🚨",
        }.get(level, "ℹ️")


# ── 共享 HTTP 客户端 (连接池复用) ──────────────────────

_httpx_client: httpx.AsyncClient | None = None


def _get_httpx_client() -> httpx.AsyncClient:
    global _httpx_client  # noqa: PLW0603
    if _httpx_client is None:
        _httpx_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    return _httpx_client


# ── Telegram 通知器 ─────────────────────────────────


class TelegramNotifier(BaseNotifier):
    """Telegram Bot 通知"""

    channel = NotifyChannel.TELEGRAM

    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.bot_token = bot_token or getattr(settings, "telegram_bot_token", "")
        self.chat_id = chat_id or getattr(settings, "telegram_chat_id", "")

    async def send(self, msg: NotifyMessage) -> bool:
        if not self.bot_token or not self.chat_id:
            return False

        emoji = self._emoji(msg.level)
        text = f"{emoji} *{msg.title}*\n\n{msg.content}"

        if msg.metadata:
            meta_lines = "\n".join(f"• _{k}_: `{v}`" for k, v in list(msg.metadata.items())[:5])
            text += f"\n\n{meta_lines}"

        try:
            client = _get_httpx_client()
            resp = await client.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
            )
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"[Notify] Telegram 发送失败: {e}")
            return False


# ── 飞书通知器 ──────────────────────────────


class FeishuNotifier(BaseNotifier):
    """飞书机器人通知 (支持卡片消息)"""

    channel = NotifyChannel.FEISHU

    def __init__(self, webhook_url: str = "", secret: str = ""):
        self.webhook_url = webhook_url or getattr(settings, "feishu_webhook_url", "")
        self.secret = secret or getattr(settings, "feishu_webhook_secret", "")

    async def send(self, msg: NotifyMessage) -> bool:
        if not self.webhook_url:
            return False

        color_map = {
            NotifyLevel.INFO: "blue",
            NotifyLevel.SUCCESS: "green",
            NotifyLevel.WARNING: "yellow",
            NotifyLevel.ERROR: "red",
            NotifyLevel.CRITICAL: "purple",
        }

        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"{self._emoji(msg.level)} {msg.title}",
                    },
                    "template": color_map.get(msg.level, "blue"),
                },
                "elements": [
                    {"tag": "markdown", "content": msg.content},
                ],
            },
        }

        url = self.webhook_url
        if self.secret:
            timestamp = str(int(time.time()))
            sign_string = f"{timestamp}\n{self.secret}"
            sign = hmac.new(self.secret.encode(), sign_string.encode(), hashlib.sha256).digest()
            import base64

            url = f"{self.webhook_url}&timestamp={timestamp}&sign={base64.b64encode(sign).decode()}"

        try:
            client = _get_httpx_client()
            resp = await client.post(url, json=card)
            result = resp.json()
            return result.get("code") == 0
        except Exception as e:
            logger.warning(f"[Notify] 飞书 发送失败: {e}")
            return False


# ── 企业微信通知器 ────────────────────────────────────


class WecomNotifier(BaseNotifier):
    """企业微信机器人通知 (支持 Markdown)"""

    channel = NotifyChannel.WECOM

    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url or getattr(settings, "wecom_webhook_url", "")

    async def send(self, msg: NotifyMessage) -> bool:
        if not self.webhook_url:
            return False

        emoji = self._emoji(msg.level)
        color = {
            NotifyLevel.INFO: "info",
            NotifyLevel.SUCCESS: "info",
            NotifyLevel.WARNING: "warning",
            NotifyLevel.ERROR: "warning",
            NotifyLevel.CRITICAL: "warning",
        }.get(msg.level, "info")

        markdown_content = f"## {emoji} {msg.title}\n{msg.content}"

        if msg.metadata:
            meta_lines = "\n".join(f"> {k}: {v}" for k, v in list(msg.metadata.items())[:5])
            markdown_content += f"\n{meta_lines}"

        payload = {
            "msgtype": "markdown",
            "markdown": {"content": markdown_content},
        }

        try:
            client = _get_httpx_client()
            resp = await client.post(self.webhook_url, json=payload)
            result = resp.json()
            return result.get("errcode") == 0
        except Exception as e:
            logger.warning(f"[Notify] 企微 发送失败: {e}")
            return False


# ── 通用 Webhook 通知器 ──────────────────────────────


class WebhookNotifier(BaseNotifier):
    """通用 Webhook (HMAC-SHA256 签名)"""

    channel = NotifyChannel.WEBHOOK

    def __init__(self, url: str = "", secret: str = ""):
        self.url = url or getattr(settings, "webhook_url", "")
        self.secret = secret or getattr(settings, "webhook_secret", "")

    async def send(self, msg: NotifyMessage) -> bool:
        if not self.url:
            return False

        payload = {
            "title": msg.title,
            "message": msg.content,
            "level": msg.level.value,
            "timestamp": msg.timestamp,
            "source": msg.source,
            "metadata": msg.metadata,
        }

        headers = {"Content-Type": "application/json"}
        if self.secret:
            body = json.dumps(payload, ensure_ascii=False)
            sig = hmac.new(self.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers["X-Kunlun-Signature"] = sig

        try:
            client = _get_httpx_client()
            await client.post(self.url, json=payload, headers=headers)
            return True
        except Exception as e:
            logger.warning(f"[Notify] Webhook 发送失败: {e}")
            return False


# ─── 通知管理器 ──────────────────────────────────────


class NotifyManager:
    """统一通知管理器 — 多通道并行发送

    用法:
        mgr = NotifyManager()
        mgr.add(TelegramNotifier(bot_token="...", chat_id="..."))
        mgr.add(FeishuNotifier(webhook_url="..."))
        await mgr.notify(
            title="第42章 完成",
            content="字数: 2850, 审计通过, 爽点: 3个",
            level=NotifyLevel.SUCCESS,
        )
    """

    def __init__(self):
        self._notifiers: list[BaseNotifier] = []

    def add(self, notifier: BaseNotifier) -> None:
        self._notifiers.append(notifier)

    def remove(self, channel: NotifyChannel) -> None:
        self._notifiers = [n for n in self._notifiers if n.channel != channel]

    async def notify(
        self,
        title: str,
        content: str,
        level: NotifyLevel = NotifyLevel.INFO,
        metadata: dict | None = None,
        channels: list[NotifyChannel] | None = None,
    ) -> dict[str, bool]:
        msg = NotifyMessage(
            title=title,
            content=content,
            level=level,
            metadata=metadata or {},
        )

        targets = [n for n in self._notifiers if channels is None or n.channel in channels]

        results = await asyncio.gather(
            *[n.send(msg) for n in targets],
            return_exceptions=True,
        )

        return {n.channel.value: (r is True) for n, r in zip(targets, results, strict=False)}

    async def notify_chapter_done(
        self, chapter: int, word_count: int, audit_passed: bool, book_id: str = ""
    ) -> dict[str, bool]:
        status = "✅ 通过" if audit_passed else "⚠️ 未通过"
        return await self.notify(
            title=f"第{chapter}章 完成",
            content=f"字数: {word_count}\n审计: {status}",
            level=NotifyLevel.SUCCESS if audit_passed else NotifyLevel.WARNING,
            metadata={"book": book_id, "chapter": str(chapter), "words": str(word_count)},
        )

    async def notify_error(
        self, error_type: str, detail: str, book_id: str = ""
    ) -> dict[str, bool]:
        return await self.notify(
            title=f"错误: {error_type}",
            content=detail,
            level=NotifyLevel.ERROR,
            metadata={"book": book_id, "error": error_type},
        )

    # ─── 新增模板方法 ──────────────────────────

    async def notify_chapter_completion(
        self,
        book_id: str,
        chapter: int,
        word_count: int,
        draft_preview: str = "",
        audit_score: float = 0.0,
        pleasure_count: int = 0,
        conflict_count: int = 0,
        duration_seconds: float = 0.0,
    ) -> dict[str, bool]:
        """章节完成通知 — 包含完整创作统计"""
        status = "✅ 通过" if audit_score >= 0.6 else "⚠️ 需修订"
        level = NotifyLevel.SUCCESS if audit_score >= 0.6 else NotifyLevel.WARNING

        content_lines = [
            f"📖 **{book_id}** 第{chapter}章 创作完成",
            "",
            f"📝 字数: **{word_count}**",
            f"📊 审计评分: **{audit_score:.2f}** ({status})",
            f"⚡ 爽点: {pleasure_count}个 | 🔥 冲突线: {conflict_count}条",
            f"⏱ 耗时: {duration_seconds:.1f}秒",
        ]
        if draft_preview:
            preview = draft_preview[:80].replace("\n", " ")
            content_lines.append("")
            content_lines.append(f"📄 预览: {preview}...")

        return await self.notify(
            title=f"第{chapter}章 完成",
            content="\n".join(content_lines),
            level=level,
            metadata={
                "book": book_id,
                "chapter": str(chapter),
                "words": str(word_count),
                "audit_score": f"{audit_score:.2f}",
                "pleasure": str(pleasure_count),
                "conflicts": str(conflict_count),
                "duration": f"{duration_seconds:.1f}s",
            },
        )

    async def notify_quality_alert(
        self,
        book_id: str,
        chapter: int,
        audit_score: float,
        threshold: float = 0.6,
        failing_gates: list[str] | None = None,
        suggestions: list[str] | None = None,
    ) -> dict[str, bool]:
        """质量告警通知 — 审计分数低于阈值时触发"""
        level = NotifyLevel.WARNING
        if audit_score < 0.3:
            level = NotifyLevel.CRITICAL
        elif audit_score < 0.5:
            level = NotifyLevel.ERROR

        content_lines = [
            f"🚨 **质量告警** — {book_id} 第{chapter}章",
            "",
            f"📊 审计评分: **{audit_score:.2f}** (阈值: {threshold:.2f})",
        ]

        if failing_gates:
            content_lines.append("")
            content_lines.append("❌ 未通过的门禁:")
            content_lines.extend(f"  • {gate}" for gate in failing_gates)

        if suggestions:
            content_lines.append("")
            content_lines.append("💡 改进建议:")
            content_lines.extend(f"  • {sug}" for sug in suggestions[:3])

        return await self.notify(
            title=f"质量告警 — 第{chapter}章",
            content="\n".join(content_lines),
            level=level,
            metadata={
                "book": book_id,
                "chapter": str(chapter),
                "audit_score": f"{audit_score:.2f}",
                "threshold": f"{threshold:.2f}",
                "failing_gates": ",".join(failing_gates or []),
            },
        )

    async def notify_schedule_reminder(
        self,
        book_id: str,
        week_progress: int = 0,
        week_goal: int = 7,
        chapters_written_this_week: int = 0,
        words_written_this_week: int = 0,
        days_remaining: int = 0,
    ) -> dict[str, bool]:
        """写作进度提醒通知"""
        progress_pct = (chapters_written_this_week / max(week_goal, 1)) * 100

        if progress_pct >= 100:
            level = NotifyLevel.SUCCESS
            emoji = "🎉"
            status = "目标已达成！"
        elif progress_pct >= 70:
            level = NotifyLevel.INFO
            emoji = "📝"
            status = f"即将完成，剩余{week_goal - chapters_written_this_week}章"
        elif progress_pct >= 30:
            level = NotifyLevel.WARNING
            emoji = "⏰"
            status = f"进度过半，还剩{days_remaining}天"
        else:
            level = NotifyLevel.WARNING
            emoji = "⚠️"
            status = f"进度偏慢，还剩{days_remaining}天"

        content_lines = [
            f"{emoji} **每周写作进度** — {book_id}",
            "",
            f"📊 本周进度: {chapters_written_this_week}/{week_goal} 章 ({progress_pct:.0f}%)",
            f"📝 本周字数: {words_written_this_week}",
            f"📅 剩余天数: {days_remaining}天",
            "",
            f"状态: {status}",
        ]

        return await self.notify(
            title=f"写作进度 {chapters_written_this_week}/{week_goal}",
            content="\n".join(content_lines),
            level=level,
            metadata={
                "book": book_id,
                "week_progress": str(week_progress),
                "week_goal": str(week_goal),
                "chapters": str(chapters_written_this_week),
                "words": str(words_written_this_week),
                "days_remaining": str(days_remaining),
            },
        )

    async def notify_batch(
        self,
        messages: list[dict],
        channels: list[NotifyChannel] | None = None,
    ) -> dict[str, dict[str, bool]]:
        """批量通知 — 多条消息并行推送到多个通道"""
        results: dict[str, dict[str, bool]] = {}

        async def send_one(msg_data: dict) -> tuple[str, dict[str, bool]]:
            msg_id = msg_data.get("id", str(time.time()))
            result = await self.notify(
                title=msg_data["title"],
                content=msg_data["content"],
                level=NotifyLevel(msg_data.get("level", "info")),
                metadata=msg_data.get("metadata", {}),
                channels=channels,
            )
            return msg_id, result

        tasks = [send_one(msg) for msg in messages]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, r in enumerate(all_results):
            msg_id = messages[i].get("id", str(i))
            if isinstance(r, Exception):
                results[msg_id] = {"error": str(r)}
            else:
                results[msg_id] = r[1]

        return results

    @classmethod
    def auto_configure(cls) -> NotifyManager:
        mgr = cls()

        bot_token = getattr(settings, "telegram_bot_token", "")
        chat_id = getattr(settings, "telegram_chat_id", "")
        if bot_token and chat_id:
            mgr.add(TelegramNotifier(bot_token, chat_id))

        feishu_url = getattr(settings, "feishu_webhook_url", "")
        if feishu_url:
            mgr.add(FeishuNotifier(feishu_url, getattr(settings, "feishu_webhook_secret", "")))

        wecom_url = getattr(settings, "wecom_webhook_url", "")
        if wecom_url:
            mgr.add(WecomNotifier(wecom_url))

        webhook_url = getattr(settings, "webhook_url", "")
        if webhook_url:
            mgr.add(WebhookNotifier(webhook_url, getattr(settings, "webhook_secret", "")))

        return mgr


# ─── 工厂函数 ────────────────────────────────────────

_notify_manager: NotifyManager | None = None


def get_notify_manager() -> NotifyManager:
    global _notify_manager  # noqa: PLW0603
    if _notify_manager is None:
        _notify_manager = NotifyManager.auto_configure()
    return _notify_manager
