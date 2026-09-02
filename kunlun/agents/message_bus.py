"""
进程内消息总线 — 替代 NATS 的本地消息机制

当 NATS 不可用时，Agent 间通过此总线进行消息传递，
支持通配符订阅 (agent.*) 和协程安全 (asyncio.Lock)。
"""

from __future__ import annotations

import asyncio
import fnmatch
from collections.abc import Awaitable, Callable

from loguru import logger

MessageCallback = Callable[..., Awaitable[None]]


class InProcessMessageBus:
    """
    进程内消息总线

    - subscribe(topic, callback): 订阅主题，支持通配符 *
    - unsubscribe(topic, callback): 取消订阅
    - publish(topic, message): 向匹配主题的所有订阅者发布消息
    """

    def __init__(self):
        self._subscriptions: dict[str, list[MessageCallback]] = {}
        self._bus_lock = asyncio.Lock()
        self._notify_semaphore = asyncio.Semaphore(10)  # 限制并发通知数，防止协程爆炸

    async def subscribe(self, topic: str, callback: MessageCallback) -> None:
        """订阅某个主题"""
        async with self._bus_lock:
            if topic not in self._subscriptions:
                self._subscriptions[topic] = []
            self._subscriptions[topic].append(callback)
            logger.debug(f"MessageBus: +订阅 {topic} ({len(self._subscriptions[topic])} 回调)")

    async def unsubscribe(self, topic: str, callback: MessageCallback) -> None:
        """取消订阅"""
        async with self._bus_lock:
            if topic in self._subscriptions:
                self._subscriptions[topic] = [
                    cb for cb in self._subscriptions[topic] if cb != callback
                ]
                if not self._subscriptions[topic]:
                    del self._subscriptions[topic]

    async def publish(self, topic: str, message: object) -> None:
        """
        向所有匹配的订阅者发布消息

        匹配规则：精确匹配 或 通配符 * 匹配（支持 "agent.*" 模式）
        """
        async with self._bus_lock:
            # 收集所有匹配的回调
            matched_callbacks: list[MessageCallback] = []
            for sub_topic, callbacks in self._subscriptions.items():
                if self._topic_match(sub_topic, topic):
                    matched_callbacks.extend(callbacks)

        if not matched_callbacks:
            logger.debug(f"MessageBus: 无订阅者匹配 topic={topic}")
            return

        # 并发通知所有匹配的订阅者（带并发限制）
        async def _bounded(cb):
            async with self._notify_semaphore:
                await self._safe_invoke(cb, topic, message)

        tasks = [_bounded(cb) for cb in matched_callbacks]
        if tasks:
            await asyncio.gather(*tasks)

    async def _safe_invoke(self, callback: MessageCallback, topic: str, message):
        """安全调用回调，捕获异常"""
        try:
            await callback(message)
        except Exception as e:
            logger.error(f"MessageBus: 回调异常 (topic={topic}): {e}")

    @staticmethod
    def _topic_match(pattern: str, topic: str) -> bool:
        """支持 glob 通配符 * 的主题匹配"""
        return fnmatch.fnmatch(topic, pattern)


# 全局单例 — 模块级实例即为单例，无需 __new__ 或 get_instance()
message_bus = InProcessMessageBus()
