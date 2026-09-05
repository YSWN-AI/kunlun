"""Kunlun 创作引擎 — 抽卡引擎包"""

from __future__ import annotations

from kunlun.gacha.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    KeyRotator,
    SlidingWindowStats,
)
from kunlun.gacha.engine import (
    CASCADE_THRESHOLDS,
    DEFAULT_MODELS,
    GachaEngine,
    ModelCandidate,
    gacha_engine,
)
from kunlun.gacha.model_router import (
    DEFAULT_MODEL_LIBRARY,
    DEFAULT_ROUTING_TABLE,
    ModelInfo,
    ModelRouter,
    RoutingRule,
    TaskType,
    get_model_router,
    route_for_agent,
)
from kunlun.gacha.param_variator import ParamVariator

__all__ = [
    # Engine
    "CASCADE_THRESHOLDS",
    "DEFAULT_MODELS",
    # Router
    "DEFAULT_MODEL_LIBRARY",
    "DEFAULT_ROUTING_TABLE",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "CircuitState",
    "GachaEngine",
    "KeyRotator",
    "ModelCandidate",
    "ModelInfo",
    "ModelRouter",
    # Variator
    "ParamVariator",
    "RoutingRule",
    "SlidingWindowStats",
    "TaskType",
    "gacha_engine",
    "get_model_router",
    "route_for_agent",
]
