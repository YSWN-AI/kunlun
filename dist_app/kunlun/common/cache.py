"""
TTL缓存装饰器 — 减少频繁属性的重复计算开销。

用法:
    @ttl_cache(seconds=60)
    def expensive_check():
        ...

    @ttl_cache(seconds=5, maxsize=128)
    def cached_func(arg):
        ...
"""

from __future__ import annotations

import functools
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


def ttl_cache(seconds: float = 60, maxsize: int = 32):
    """带TTL和LRU淘汰的函数结果缓存装饰器。

    Args:
        seconds: 缓存有效期（秒），默认60秒
        maxsize: 最大缓存条目数，超过时按LRU淘汰

    特性:
        - 线程安全（reentrant lock）
        - 支持不同参数产生不同缓存键（基于 repr）
        - 自动淘汰过期条目和LRU条目
    """

    def decorator(func: F) -> F:
        cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        lock = threading.RLock()

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            key = _make_key(args, kwargs)

            with lock:
                if key in cache:
                    expiry, value = cache[key]
                    if now < expiry:
                        cache.move_to_end(key)
                        return value
                    del cache[key]

                value = func(*args, **kwargs)
                cache[key] = (now + seconds, value)
                cache.move_to_end(key)

                while len(cache) > maxsize:
                    cache.popitem(last=False)

            return value

        def cache_clear():
            with lock:
                cache.clear()

        cast(Any, wrapper).cache_clear = cache_clear
        cast(Any, wrapper).cache_info = lambda: {
            "size": len(cache),
            "maxsize": maxsize,
            "ttl": seconds,
        }
        return cast(F, wrapper)

    return decorator


def _make_key(args: tuple, kwargs: dict) -> str:
    return repr(args) + repr(sorted(kwargs.items()))


class TTLPropertyCache:
    """TTL属性缓存管理器 — 用于对象的 @property 方法结果缓存。

    与 @ttl_cache 不同，此管理器更轻量，专门用于属性缓存场景。

    用法:
        class KGClient:
            def __init__(self):
                self._prop_cache = TTLPropertyCache()

            @property
            def neo4j_available(self):
                return self._prop_cache.get("neo4j_available", 30, self._check_neo4j)
    """

    def __init__(self):
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = threading.RLock()

    def get(self, key: str, ttl: float, factory: Callable[[], Any]) -> Any:
        now = time.time()
        with self._lock:
            if key in self._cache:
                expiry, value = self._cache[key]
                if now < expiry:
                    return value
            value = factory()
            self._cache[key] = (now + ttl, value)
            return value

    def invalidate(self, key: str | None = None):
        with self._lock:
            if key is None:
                self._cache.clear()
            else:
                self._cache.pop(key, None)
