"""
MockNATS — 进程内 NATS 模拟

在 NATS 服务器不可用时提供兼容的进程内消息传递，
模拟 nats-py 的 connect / publish / subscribe 接口。
采用同步分发模式（publish 时立即调用订阅回调），避免后台事件循环任务。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger


class MockNATS:
    """模拟 nats-py 客户端。publish 时同步分发到匹配的订阅回调。"""

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[Callable[[dict[str, Any]], Awaitable[None]]]] = {}
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self, _servers: str | list[str] | None = None, **_kwargs: Any) -> None:
        """模拟连接。"""
        self._connected = True
        logger.info("MockNATS: 已连接（进程内模式）")

    async def close(self) -> None:
        """模拟断开连接。"""
        self._connected = False
        self._subscriptions.clear()
        logger.info("MockNATS: 已断开")

    async def publish(self, subject: str, payload: dict[str, Any]) -> None:
        """发布消息并立即同步分发给所有匹配的订阅者。"""
        if not self._connected:
            logger.warning(f"MockNATS: 未连接，丢弃消息 subject={subject}")
            return

        callbacks: list[Callable[[dict[str, Any]], Awaitable[None]]] = []
        callbacks.extend(self._subscriptions.get(subject, []))
        for pattern, cbs in self._subscriptions.items():
            if pattern != subject and self._match_wildcard(pattern, subject):
                callbacks.extend(cbs)

        for cb in set(callbacks):
            try:
                await cb(payload)
            except Exception:
                logger.exception(f"MockNATS: 回调异常 subject={subject}")

    async def subscribe(
        self, subject: str, cb: Callable[[dict[str, Any]], Awaitable[None]]
    ) -> None:
        """订阅 subject。"""
        if subject not in self._subscriptions:
            self._subscriptions[subject] = []
        self._subscriptions[subject].append(cb)
        logger.debug(f"MockNATS: 订阅 subject={subject}")

    @staticmethod
    def _match_wildcard(pattern: str, subject: str) -> bool:
        """简单的通配符匹配：* 匹配单段。"""
        p_parts = pattern.split(".")
        s_parts = subject.split(".")
        if len(p_parts) != len(s_parts):
            return False
        return all(not (p not in ("*", s)) for p, s in zip(p_parts, s_parts, strict=True))


async def create_mock_nats() -> MockNATS:
    """工厂函数：创建并连接 MockNATS。"""
    client = MockNATS()
    await client.connect()
    return client
