"""
守护进程 + 通知推送 — 对应 inkos up 命令

后台循环自动写章，非关键问题全自动运行，关键问题暂停等人工审核。
通知: Telegram / 飞书 / 企业微信 / Webhook (HMAC-SHA256签名)
"""

from __future__ import annotations
from typing import Any

import asyncio
import contextlib
import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from loguru import logger

from kunlun.config import settings


class DaemonStatus(StrEnum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"  # 等待人工审核
    IDLE = "idle"  # 无待写章节


@dataclass
class DaemonConfig:
    book_id: str
    chapters_to_write: int = 10  # 可通过 settings.daemon_default_chapters 配置全局默认值
    mode: str = "gacha_parallel_3"
    auto_approve: bool = True  # 是否自动审批
    pause_on_fatal: bool = True  # 审计致命问题时暂停
    notify_on_complete: bool = True
    notify_on_error: bool = True


class NotificationChannel:
    """通知推送基类"""

    async def send(self, title: str, message: str, level: str = "info"):
        raise NotImplementedError


class WebhookNotifier(NotificationChannel):
    """Webhook通知（支持HMAC-SHA256签名）"""

    def __init__(self, url: str, secret: str = ""):
        self.url = url
        self.secret = secret

    async def send(self, title: str, message: str, level: str = "info"):
        import httpx

        payload = {
            "title": title,
            "message": message,
            "level": level,
            "timestamp": time.time(),
            "source": "kunlun-daemon",
        }
        headers = {"Content-Type": "application/json"}
        if self.secret:
            body = json.dumps(payload, ensure_ascii=False)
            signature = hmac.new(self.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers["X-Kunlun-Signature"] = signature
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(self.url, json=payload, headers=headers)
        except Exception as e:
            logger.warning(f"[Daemon] Webhook通知失败: {e}")


class TelegramNotifier(NotificationChannel):
    """Telegram Bot 通知"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def send(self, title: str, message: str, level: str = "info"):
        import httpx

        emoji = {"info": "ℹ️", "success": "✅", "error": "❌", "warning": "⚠️"}.get(level, "ℹ️")
        text = f"{emoji} *{title}*\n{message}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                    json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"},
                )
        except Exception as e:
            logger.warning(f"[Daemon] Telegram通知失败: {e}")


class LogWriter:
    """JSON Lines 日志写入器（对应 inkos.log）"""

    def __init__(self, log_path: Path | None = None):
        self.log_path = log_path or settings.DATA_DIR / "logs" / "daemon.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: str, data: dict):
        """写入日志（线程安全：追加模式天然安全）"""
        entry = {"time": time.time(), "event": event, **data}
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    async def awrite(self, event: str, data: dict):
        """异步写入（使用线程池避免阻塞事件循环）"""
        import asyncio

        entry = {"time": time.time(), "event": event, **data}
        line = json.dumps(entry, ensure_ascii=False) + "\n"

        def _write():
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(line)

        await asyncio.to_thread(_write)


class DaemonEngine:
    """
    守护进程引擎

    用法:
      engine = DaemonEngine(config)
      await engine.start()
    """

    def __init__(self, config: DaemonConfig):
        self.config = config
        self.status = DaemonStatus.STOPPED
        self.chapters_written = 0
        self.chapters_failed = 0
        self.notifiers: list[NotificationChannel] = []
        self._unified_notify_mgr: Any | None = None  # 统一通知管理器 (延迟加载)
        self.log_writer = LogWriter()
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # 初始非暂停
        self._stop_flag = False
        self._auto_configure_notifiers()

    def _auto_configure_notifiers(self):
        """自动从 settings + 统一通知模块配置通知器"""
        # 原有通知器 (daemon内置)
        webhook_url = getattr(settings, "webhook_url", "")
        webhook_secret = getattr(settings, "webhook_secret", "")
        if webhook_url:
            self.notifiers.append(WebhookNotifier(webhook_url, webhook_secret))

        bot_token = getattr(settings, "telegram_bot_token", "")
        chat_id = getattr(settings, "telegram_chat_id", "")
        if bot_token and chat_id:
            self.notifiers.append(TelegramNotifier(bot_token, chat_id))

        # 尝试加载新的统一通知系统
        try:
            from kunlun.notify import get_notify_manager

            self._unified_notify_mgr = get_notify_manager()
            if not self._unified_notify_mgr._notifiers:
                self._unified_notify_mgr = None
        except Exception as e:
            logger.debug(f"统一通知系统加载失败（降级到旧通知器）: {e}")

    def add_notifier(self, notifier: NotificationChannel):
        self.notifiers.append(notifier)

    async def _notify(self, title: str, message: str, level: str = "info"):
        # 先尝试统一通知系统
        if self._unified_notify_mgr:
            from kunlun.notify import NotifyLevel

            try:
                nl = NotifyLevel(level)
            except ValueError:
                nl = NotifyLevel.INFO
            with contextlib.suppress(Exception):
                await self._unified_notify_mgr.notify(
                    title=title,
                    content=message,
                    level=nl,
                    metadata={"book": self.config.book_id},
                )
        # 回退到内置通知器
        for n in self.notifiers:
            with contextlib.suppress(Exception):
                await n.send(title, message, level)

    @staticmethod
    def _classify_exception(e: Exception) -> str:
        """分类异常类型，返回: 'retry'（可重试）, 'backoff'（需退避）, 'fatal'（致命）"""
        import httpx

        # 网络相关 → 可重试
        if isinstance(
            e,
            (
                asyncio.TimeoutError,
                ConnectionError,
                TimeoutError,
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.RemoteProtocolError,
            ),
        ):
            return "retry"

        # API 限流 → 需退避
        msg = str(e).lower()
        rate_limit_keywords = ("429", "rate limit", "too many requests", "quota exceeded")
        if any(kw in msg for kw in rate_limit_keywords):
            return "backoff"

        # httpx HTTPStatusError 检查状态码
        if isinstance(e, httpx.HTTPStatusError):
            if e.response.status_code == 429:
                return "backoff"
            if 500 <= e.response.status_code < 600:
                return "retry"

        # 数据/参数错误 → 致命（重试无意义）
        if isinstance(e, (ValueError, TypeError, KeyError, AttributeError)):
            return "fatal"

        # 其他未知错误 → 默认可重试一次，连续失败则提升为致命
        return "retry"

    async def _write_chapter(self, editor, chapter: int) -> dict | None:
        """带重试的单章写入。返回 result dict 或 None（最终失败）。"""
        max_retries = getattr(settings, "daemon_max_retries", 3)
        backoff_base = getattr(settings, "daemon_retry_backoff_base", 5.0)
        consecutive_unknown = 0

        for attempt in range(1, max_retries + 1):
            if self._stop_flag:
                return None

            try:
                return await editor.chat(f"写第{chapter}章", {"chapter": chapter})
            except Exception as e:
                category = self._classify_exception(e)

                log_data = {
                    "chapter": chapter,
                    "attempt": attempt,
                    "category": category,
                    "exception": str(e),
                }

                if category == "fatal":
                    logger.error(f"[Daemon] 第{chapter}章致命错误(不可重试): {e}")
                    self.log_writer.write("chapter_fatal", log_data)
                    return None

                if category == "backoff":
                    wait = backoff_base * (2 ** (attempt - 1))
                    logger.warning(
                        f"[Daemon] 第{chapter}章触发限流，"
                        f"第{attempt}/{max_retries}次重试，退避{wait:.0f}s"
                    )
                    self.log_writer.write("chapter_retry_backoff", {**log_data, "wait": wait})
                    await self._pause_event.wait()  # 暂停时等待
                    await asyncio.sleep(wait)
                    continue

                # 未知异常：连续出现则提升为致命
                if category == "retry" and attempt == 1:
                    consecutive_unknown += 1
                else:
                    consecutive_unknown = 0

                if consecutive_unknown >= 3:
                    logger.error(f"[Daemon] 第{chapter}章连续未知异常，视为致命: {e}")
                    self.log_writer.write("chapter_fatal_escalated", log_data)
                    return None

                if attempt < max_retries:
                    wait = backoff_base * attempt
                    logger.warning(
                        f"[Daemon] 第{chapter}章异常，"
                        f"第{attempt}/{max_retries}次重试，等待{wait:.0f}s: {e}"
                    )
                    self.log_writer.write("chapter_retry", {**log_data, "wait": wait})
                    await self._pause_event.wait()
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"[Daemon] 第{chapter}章{max_retries}次重试后仍失败: {e}")
                    self.log_writer.write("chapter_retry_exhausted", log_data)

        return None

    async def start(self):
        """启动守护进程"""
        self.status = DaemonStatus.RUNNING
        self._stop_flag = False
        self.log_writer.write(
            "daemon_start",
            {"book_id": self.config.book_id, "chapters": self.config.chapters_to_write},
        )
        logger.info(f"[Daemon] 启动: {self.config.book_id}, {self.config.chapters_to_write}章")

        max_consecutive = getattr(settings, "daemon_max_consecutive_failures", 5)
        consecutive_failures = 0

        try:
            from kunlun.agents.editor import EditorInChief
            from kunlun.kg.snapshot import snapshot_manager

            editor = EditorInChief(self.config.book_id)
            snap = snapshot_manager.get_latest(self.config.book_id)
            start_chapter = (snap.chapter + 1) if snap else 1

            for i in range(self.config.chapters_to_write):
                if self._stop_flag:
                    break

                chapter = start_chapter + i

                # 等待暂停恢复
                await self._pause_event.wait()

                self.log_writer.write("chapter_start", {"chapter": chapter})
                logger.info(f"[Daemon] 开始写第{chapter}章...")

                # 带重试的章节写入
                result = await self._write_chapter(editor, chapter)

                if result is not None and result.get("success"):
                    consecutive_failures = 0  # 重置连续失败计数
                    self.chapters_written += 1
                    word_count = result.get("word_count", 0)
                    audit_passed = result.get("audit_passed", False)

                    self.log_writer.write(
                        "chapter_complete",
                        {
                            "chapter": chapter,
                            "word_count": word_count,
                            "audit_passed": audit_passed,
                        },
                    )

                    if self.config.notify_on_complete:
                        await self._notify(
                            f"第{chapter}章完成",
                            f"字数: {word_count}, 审计: {'通过' if audit_passed else '需修订'}",
                            "success" if audit_passed else "warning",
                        )

                    # 审计致命问题 → 暂停等待人工
                    if not audit_passed and self.config.pause_on_fatal:
                        self.status = DaemonStatus.PAUSED
                        self._pause_event.clear()
                        await self._notify(
                            f"⚠️ 第{chapter}章审计未通过",
                            "管线已暂停，等待人工审核。在Web UI中审批后可继续。",
                            "warning",
                        )
                        logger.warning(f"[Daemon] 第{chapter}章审计未通过，暂停等待人工")
                        # 等待人工操作（通过API恢复）
                        await self._pause_event.wait()
                        self.status = DaemonStatus.RUNNING
                else:
                    consecutive_failures += 1
                    self.chapters_failed += 1
                    error_msg = result.get("error", "未知") if result else "重试耗尽"
                    self.log_writer.write(
                        "chapter_error",
                        {
                            "chapter": chapter,
                            "error": error_msg,
                            "consecutive_failures": consecutive_failures,
                        },
                    )

                    if self.config.notify_on_error:
                        await self._notify(
                            f"❌ 第{chapter}章失败",
                            str(error_msg),
                            "error",
                        )

                    # 连续失败熔断
                    if max_consecutive > 0 and consecutive_failures >= max_consecutive:
                        logger.error(
                            f"[Daemon] 连续{consecutive_failures}章失败，"
                            f"触发熔断（阈值{max_consecutive}）"
                        )
                        self.log_writer.write(
                            "daemon_circuit_breaker",
                            {"consecutive_failures": consecutive_failures, "chapter": chapter},
                        )
                        await self._notify(
                            "🔌 守护进程熔断",
                            f"连续{consecutive_failures}章失败，守护进程已自动停止。"
                            f"请检查API配置或网络后重新启动。",
                            "error",
                        )
                        break

                # 章节间隔
                _interval = getattr(settings, "daemon_chapter_interval", 3)
                await asyncio.sleep(_interval)

        except Exception as e:
            logger.error(f"[Daemon] 致命错误: {e}")
            self.log_writer.write("daemon_fatal", {"error": str(e)})

        self.status = DaemonStatus.IDLE if not self._stop_flag else DaemonStatus.STOPPED
        self.log_writer.write(
            "daemon_stop",
            {"chapters_written": self.chapters_written, "chapters_failed": self.chapters_failed},
        )
        await self._notify(
            "守护进程结束", f"共写{self.chapters_written}章, 失败{self.chapters_failed}章", "info"
        )

    def pause(self):
        """暂停（等待人工审批）"""
        self._pause_event.clear()
        self.status = DaemonStatus.PAUSED
        logger.info("[Daemon] 已暂停")

    def resume(self):
        """恢复执行"""
        self._pause_event.set()
        self.status = DaemonStatus.RUNNING
        logger.info("[Daemon] 已恢复")

    def stop(self):
        """停止"""
        self._stop_flag = True
        self._pause_event.set()  # 解除阻塞
        self.status = DaemonStatus.STOPPED


# ─── 字数治理 ───


class WordCountGovernor:
    """保守型字数治理器"""

    # 目标字数对应允许区间
    WORD_TARGET_RANGES = {
        1000: (800, 1200),
        2000: (1600, 2400),
        3000: (2400, 3600),
        4000: (3200, 4800),
        5000: (4000, 6000),
        6000: (4800, 7200),
    }

    def __init__(self, count_method: str = "zh_chars"):
        self.count_method = count_method  # zh_chars / en_words

    def count(self, text: str) -> int:
        """统计字数"""
        if self.count_method == "en_words":
            return len(text.split())
        # 中文按字符数（去除标点和空白）
        # 涵盖中英文标点、特殊符号
        return len(
            re.sub(
                r"[\s\n\r"
                r"\u3000-\u303F"  # CJK 符号和标点
                r"\uFF00-\uFFEF"  # 全角字符（包括全角英文标点）
                r"\u2000-\u206F"  # 通用标点
                r"]+",
                "",
                text,
            )
        )

    def get_range(self, target: int) -> tuple[int, int]:
        """获取允许的字数区间（动态 ±20%，最少 200 字容差）"""
        margin = max(int(target * 0.2), 200)
        lo = max(100, target - margin)  # 不低于 100 字
        return (lo, target + margin)

    def is_in_range(self, word_count: int, target: int) -> bool:
        lo, hi = self.get_range(target)
        return lo <= word_count <= hi

    async def normalize(self, text: str, target: int) -> tuple[str, dict]:
        """
        纠偏归一化 — 仅1 pass压缩/补足

        Returns:
            (normalized_text, telemetry_dict)
        """
        current = self.count(text)
        lo, hi = self.get_range(target)
        telemetry = {"original_count": current, "target": target, "action": "none"}

        if lo <= current <= hi:
            return text, telemetry

        from kunlun.gacha.engine import gacha_engine

        if current < lo:
            # 需要补足
            needed = target - current
            prompt = f"""请将以下文本扩充约{needed}字，保持原有风格和情节连贯。\
只增加细节描写和心理活动，不要改变主线。

原文:
{text[:3000]}"""
            telemetry["action"] = "expand"
        else:
            # 需要压缩
            prompt = f"""请将以下文本精简至约{target}字，保留核心情节和爽点，删除冗余描写。

原文:
{text[:4000]}"""
            telemetry["action"] = "compress"

        try:
            result = await gacha_engine.generate(prompt, mode="single_fix")
            normalized = result.get("best_text", text)
            new_count = self.count(normalized)
            telemetry["normalized_count"] = new_count

            if self.is_in_range(new_count, target):
                telemetry["status"] = "corrected"
            else:
                telemetry["status"] = "still_out_of_range"
                logger.warning(f"[WordCount] 1次纠偏后仍超出区间: {new_count}")

            return normalized, telemetry
        except Exception as e:
            logger.error(f"[WordCount] 纠偏失败: {e}")
            telemetry["status"] = "correction_failed"
            return text, telemetry


# 全局单例
word_governor = WordCountGovernor()
