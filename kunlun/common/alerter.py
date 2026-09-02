"""
昆仑创作引擎 — 告警器
基于滑动窗口的错误计数，触发阈值时写入告警日志
"""

from __future__ import annotations

import time
from collections import deque

from loguru import logger


class Alerter:
    """滑动窗口告警器：在时间窗口内错误数超过阈值时触发告警"""

    def __init__(
        self,
        window_seconds: int = 300,
        threshold: int = 3,
        cooldown_seconds: int = 600,
        webhook_url: str | None = None,
    ):
        self.window_seconds = window_seconds
        self.threshold = threshold
        self.cooldown_seconds = cooldown_seconds
        self.webhook_url = webhook_url
        self._errors: deque = deque()
        self._last_alert_at: float = 0.0

    def record_error(self, message: str = "") -> None:
        """记录一次错误事件"""
        now = time.time()
        self._errors.append(now)
        # 清理窗口外的旧记录
        while self._errors and self._errors[0] < now - self.window_seconds:
            self._errors.popleft()

        if len(self._errors) >= self.threshold:
            self._maybe_alert(message)

    def _maybe_alert(self, message: str) -> None:
        """检查冷却时间，触发告警"""
        now = time.time()
        if now - self._last_alert_at < self.cooldown_seconds:
            return
        self._last_alert_at = now

        alert_msg = (
            f"[ALERT] 滑动窗口({self.window_seconds}s)内发生 "
            f"{len(self._errors)} 次错误（阈值={self.threshold})"
        )
        if message:
            alert_msg += f" | 最近错误: {message}"

        logger.warning(alert_msg)

        if self.webhook_url:
            self._send_webhook(alert_msg)

    def _send_webhook(self, message: str) -> None:
        """异步发送 Webhook 通知（不阻塞主流程）"""
        try:
            import json
            import threading
            import urllib.request

            def _post():
                try:
                    data = json.dumps({"content": message}).encode()
                    req = urllib.request.Request(
                        self.webhook_url or "",
                        data=data,
                        headers={"Content-Type": "application/json"},
                    )
                    with urllib.request.urlopen(req, timeout=5) as _resp:
                        pass  # 仅发送，不关心响应内容
                except Exception:
                    logger.debug("[Alerter] Webhook POST 失败（已忽略）")

            threading.Thread(target=_post, daemon=True).start()
        except Exception:
            logger.debug("[Alerter] 启动 Webhook 线程失败（已忽略）")

    @property
    def error_count(self) -> int:
        """当前窗口内错误数"""
        now = time.time()
        while self._errors and self._errors[0] < now - self.window_seconds:
            self._errors.popleft()
        return len(self._errors)


# 全局单例
alerter = Alerter()
