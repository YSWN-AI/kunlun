"""
昆仑创作引擎 — 滑动窗口熔断器 (Sliding Window Circuit Breaker)

设计参考:
  - Netflix Hystrix: 熔断器模式鼻祖
  - Resilience4j: 滑动窗口实现
  - Polly (.NET): 策略组合

核心机制:
  1. 滑动窗口统计: 最近 N 次调用的失败率（而非简单计数）
  2. 三态状态机: CLOSED → OPEN → HALF_OPEN → CLOSED
  3. 半开探测: 熔断后定时放行一个请求探测恢复
  4. 指数退避重试: 在 CLOSED 状态下的独立重试逻辑

用法:
    breaker = CircuitBreaker(failure_threshold=0.5, window_size=10, recovery_timeout=30)
    async with breaker:
        result = await call_llm()
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum

from loguru import logger

# ── 状态枚举 ─────────────────────────────────────────


class CircuitState(StrEnum):
    """熔断器三态"""

    CLOSED = "closed"  # 正常通行
    OPEN = "open"  # 熔断中，拒绝请求
    HALF_OPEN = "half_open"  # 半开，放行一个请求探测恢复


class CircuitBreakerOpenError(Exception):
    """熔断器开启时抛出的异常"""

    pass


# ── 滑动窗口统计 ─────────────────────────────────────


@dataclass
class SlidingWindowStats:
    """滑动窗口统计器

    维护最近 window_size 秒内的成功/失败时间戳。
    通过清理过期时间戳来保持窗口精确。
    """

    window_size_seconds: float = 60.0  # 窗口大小（秒）
    failures: deque[float] = field(default_factory=deque)
    successes: deque[float] = field(default_factory=deque)

    @property
    def failure_rate(self) -> float:
        """当前窗口内的失败率"""
        total = len(self.failures) + len(self.successes)
        if total == 0:
            return 0.0
        return len(self.failures) / total

    @property
    def total_calls(self) -> int:
        """窗口内总调用次数"""
        return len(self.failures) + len(self.successes)

    def record_success(self) -> None:
        """记录一次成功调用"""
        now = time.time()
        self.successes.append(now)
        self._cleanup()

    def record_failure(self) -> None:
        """记录一次失败调用"""
        now = time.time()
        self.failures.append(now)
        self._cleanup()

    def _cleanup(self) -> None:
        """清理超过窗口的过期记录"""
        cutoff = time.time() - self.window_size_seconds
        while self.failures and self.failures[0] < cutoff:
            self.failures.popleft()
        while self.successes and self.successes[0] < cutoff:
            self.successes.popleft()

    def reset(self) -> None:
        """重置统计（熔断恢复后调用）"""
        self.failures.clear()
        self.successes.clear()


# ── 熔断器 ───────────────────────────────────────────


class CircuitBreaker:
    """滑动窗口熔断器 — 异步上下文管理器

    用法:
        breaker = CircuitBreaker(
            failure_threshold=0.5,   # 失败率 >= 50% 触发熔断
            window_size_seconds=60,  # 60秒滑动窗口
            recovery_timeout=30,     # 30秒后半开探测
        )
        try:
            async with breaker:
                result = await call_llm()
        except CircuitBreakerOpenError:
            # 熔断中，降级处理
            pass
    """

    def __init__(
        self,
        failure_threshold: float = 0.5,
        window_size_seconds: float = 60.0,
        recovery_timeout: float = 30.0,
        min_calls_before_break: int = 5,
        name: str = "default",
    ):
        """
        Args:
            failure_threshold: 失败率阈值 (0.0-1.0)，超过则熔断
            window_size_seconds: 滑动窗口大小（秒）
            recovery_timeout: 熔断后等待多久进入半开状态（秒）
            min_calls_before_break: 最少调用次数才触发熔断（防止冷启动误熔断）
            name: 熔断器名称（用于日志）
        """
        self._state = CircuitState.CLOSED
        self._stats = SlidingWindowStats(window_size_seconds=window_size_seconds)
        self._threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._min_calls = min_calls_before_break
        self._name = name
        self._opened_at: float = 0.0
        self._last_failure_reason: str = ""

    # ── 属性 ────────────────────────────────────────

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_rate(self) -> float:
        return self._stats.failure_rate

    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN

    # ── 异步上下文管理器 ────────────────────────────

    async def __aenter__(self) -> CircuitBreaker:
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - self._opened_at
            if elapsed >= self._recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info(f"[熔断器:{self._name}] 进入半开状态，放行探测请求")
            else:
                remaining = self._recovery_timeout - elapsed
                raise CircuitBreakerOpenError(
                    f"[{self._name}] 熔断中，{remaining:.0f}秒后恢复 "
                    f"(失败率 {self._stats.failure_rate:.1%}，"
                    f"最后失败: {self._last_failure_reason})"
                )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            self._on_success()
        elif exc_type is not None:
            self._on_failure(exc_val)
        return False  # 不吞异常，继续传播

    # ── 手动控制 ────────────────────────────────────

    def force_open(self, reason: str = "") -> None:
        """强制打开熔断器"""
        self._state = CircuitState.OPEN
        self._opened_at = time.time()
        self._last_failure_reason = reason
        logger.warning(f"[熔断器:{self._name}] 手动打开: {reason}")

    def force_close(self) -> None:
        """强制关闭熔断器（重置）"""
        self._state = CircuitState.CLOSED
        self._stats.reset()
        logger.info(f"[熔断器:{self._name}] 手动关闭并重置统计")

    # ── 内部状态转换 ────────────────────────────────

    def _on_success(self) -> None:
        """记录成功"""
        self._stats.record_success()
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._stats.reset()
            logger.info(f"[熔断器:{self._name}] 探测成功，恢复关闭状态")

    def _on_failure(self, exc_val) -> None:
        """记录失败"""
        if exc_val:
            self._last_failure_reason = str(exc_val)[:200]
        self._stats.record_failure()

        if self._state == CircuitState.HALF_OPEN:
            # 半开状态下失败 → 立即重新熔断
            self._state = CircuitState.OPEN
            self._opened_at = time.time()
            logger.warning(
                f"[熔断器:{self._name}] 探测失败，重新熔断 ({self._last_failure_reason})"
            )
        elif (
            self._state == CircuitState.CLOSED
            and self._stats.total_calls >= self._min_calls
            and self._stats.failure_rate >= self._threshold
        ):
            # 关闭状态且失败率超过阈值 → 触发熔断
            self._state = CircuitState.OPEN
            self._opened_at = time.time()
            logger.warning(
                f"[熔断器:{self._name}] 熔断触发！"
                f"失败率 {self._stats.failure_rate:.1%} >= {self._threshold:.1%}，"
                f"窗口内 {self._stats.total_calls} 次调用"
            )


# ── 多 Key 轮换器 ────────────────────────────────────


class KeyRotator:
    """API Key 轮换器 — 支持多 Key 自动轮换和冷却

    用法:
        rotator = KeyRotator(["key1", "key2", "key3"], cooldown_seconds=60)
        key = rotator.next()
    """

    def __init__(self, keys: list[str], cooldown_seconds: float = 60.0):
        self._keys = keys[:]
        self._cooldown = cooldown_seconds
        self._index = 0
        self._cooldowns: dict[str, float] = {}  # key → cooldown_until

    def has_keys(self) -> bool:
        """是否还有可用 Key"""
        return len(self._keys) > 0

    def next(self) -> str | None:
        """获取下一个可用 Key（跳过冷却中的）"""
        if not self._keys:
            return None

        now = time.time()
        # 从当前位置开始查找第一个不在冷却中的 Key
        for _ in range(len(self._keys)):
            key = self._keys[self._index]
            cooldown_until = self._cooldowns.get(key, 0)
            if now >= cooldown_until:
                self._index = (self._index + 1) % len(self._keys)
                return key
            self._index = (self._index + 1) % len(self._keys)

        # 所有 Key 都在冷却中，返回冷却时间最短的那个
        best_key = min(self._keys, key=lambda k: self._cooldowns.get(k, 0))
        self._cooldowns[best_key] = 0  # 清除冷却
        return best_key

    def mark_rate_limited(self, key: str) -> None:
        """标记 Key 被限流，进入冷却"""
        self._cooldowns[key] = time.time() + self._cooldown
        logger.info(f"[KeyRotator] {key[:8]}*** 进入 {self._cooldown:.0f}s 冷却")

    def mark_failed(self, key: str) -> None:
        """标记 Key 彻底失败"""
        if key in self._keys:
            self._keys.remove(key)
            self._cooldowns.pop(key, None)
            logger.warning(f"[KeyRotator] {key[:8]}*** 移除（不可用）")
            if self._index >= len(self._keys):
                self._index = 0

    @property
    def available_count(self) -> int:
        """可用 Key 数量"""
        now = time.time()
        return sum(1 for k in self._keys if self._cooldowns.get(k, 0) <= now)
