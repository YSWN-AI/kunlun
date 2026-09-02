"""
共享速率限制器 — 提供 per-endpoint 速率限制装饰器。
支持 slowapi 降级：未安装或禁用时装饰器为无操作直通。
"""

from __future__ import annotations

from typing import Any

_limiter: Any = None
_initialized: bool = False


def _is_enabled() -> bool:
    """检查速率限制是否启用"""
    try:
        from kunlun.config import settings

        return settings.rate_limit_per_minute > 0
    except Exception:
        return False


def get_limiter() -> Any:
    """获取速率限制器实例（延迟初始化）"""
    global _limiter, _initialized  # noqa: PLW0603
    if _initialized:
        return _limiter
    _initialized = True
    if not _is_enabled():
        return None
    try:
        from slowapi import Limiter
        from slowapi.util import get_remote_address

        _limiter = Limiter(key_func=get_remote_address)
    except ImportError:
        pass
    return _limiter
