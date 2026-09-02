"""
昆仑创作引擎 — 上下文管理系统

核心组件:
  1. ContextBudgetAllocator: Token预算分配器（WenShape + SAGA）
  2. TemporalMemory: 时序记忆管理器（InkOS风格）

优化策略:
  - 时序记忆: 基于SQLite的对话历史存储，支持相关性检索
  - 距离衰减: 越近的上下文权重越高
  - 动态窗口: 长对话场景下自动优化Token使用
"""

from .budget import (
    DEFAULT_BUDGET_ALLOCATION,
    ContextBudgetAllocator,
    create_context_budget,
    log_distance_decay,
    sliding_window_weight,
)
from .temporal_memory import MemoryEntry, TemporalMemory, get_temporal_memory

__all__ = [
    "DEFAULT_BUDGET_ALLOCATION",
    "ContextBudgetAllocator",
    "MemoryEntry",
    "TemporalMemory",
    "create_context_budget",
    "get_temporal_memory",
    "log_distance_decay",
    "sliding_window_weight",
]
