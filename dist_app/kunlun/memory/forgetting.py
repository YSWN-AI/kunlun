"""
昆仑创作引擎 — 艾宾浩斯遗忘曲线 (Ebbinghaus Forgetting Curve)

基于艾宾浩斯遗忘曲线的记忆保持率计算，为情景记忆提供主动遗忘机制。

公式:
  retention = exp(-decay_rate * (age_hours / half_life_hours))
  访问次数加成: retention *= (1 + 0.1 * access_count)
  重要度加成: importance >= HIGH(4) 时 retention = max(retention, 0.8)
              CRITICAL(5) 永久保留 retention = 1.0

核心能力:
  - 计算单条记忆的保持率
  - 判断是否应遗忘
  - 批量应用遗忘曲线（返回保留/遗忘两组）
  - 访问后增强记忆（更新last_accessed和access_count）

Author: 昆仑创作引擎
"""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kunlun.memory.engine import EpisodicEvent, MemoryItem


class EbbinghausForgetting:
    """艾宾浩斯遗忘曲线"""

    def __init__(
        self,
        initial_retention: float = 1.0,
        decay_rate: float = 0.3,
        half_life_hours: float = 72.0,
    ):
        self.initial_retention = initial_retention
        self.decay_rate = decay_rate
        self.half_life_hours = half_life_hours

    def _get_age_hours(
        self,
        item: MemoryItem | EpisodicEvent,
        current_time: float | None = None,
    ) -> float:
        """获取记忆存在时长（小时）"""
        now = current_time if current_time is not None else time.time()
        created = getattr(item, "created_at", now)
        return max(0.0, (now - created) / 3600.0)

    def _get_access_count(self, item: MemoryItem | EpisodicEvent) -> int:
        """获取访问次数（兼容无此字段的对象）"""
        return int(getattr(item, "access_count", 0))

    def _get_importance_value(self, item: MemoryItem | EpisodicEvent) -> int:
        """获取重要度数值（1-5）

        MemoryItem 有 importance (MemoryImportance枚举)
        EpisodicEvent 有 importance (MemoryImportance枚举，增强后新增)
        若无 importance 字段，用 plot_relevance 映射：>=0.7→4, >=0.5→3, else→2
        """
        imp = getattr(item, "importance", None)
        if imp is not None:
            if hasattr(imp, "value"):
                return int(imp.value)
            return int(imp)
        # 回退：用 plot_relevance 映射
        plot_rel = getattr(item, "plot_relevance", 0.5)
        if plot_rel >= 0.7:
            return 4
        if plot_rel >= 0.5:
            return 3
        return 2

    def calculate_retention(
        self,
        item: MemoryItem | EpisodicEvent,
        current_time: float | None = None,
    ) -> float:
        """计算记忆保持率 (0-1)

        Args:
            item: 记忆项（MemoryItem 或 EpisodicEvent）
            current_time: 当前时间戳，None则用系统时间

        Returns:
            保持率 0.0 - 1.0
        """
        importance_val = self._get_importance_value(item)

        # CRITICAL(5) 永久保留
        if importance_val >= 5:
            return 1.0

        age_hours = self._get_age_hours(item, current_time)
        # 基础遗忘曲线
        retention = self.initial_retention * math.exp(
            -self.decay_rate * (age_hours / self.half_life_hours)
        )

        # 访问次数加成
        access_count = self._get_access_count(item)
        retention *= 1.0 + 0.1 * access_count

        # 重要度加成：HIGH(4) 及以上最低保持0.8
        if importance_val >= 4:
            retention = max(retention, 0.8)

        # 限制在 [0, 1]
        return max(0.0, min(1.0, retention))

    def should_forget(
        self,
        item: MemoryItem | EpisodicEvent,
        threshold: float = 0.1,
    ) -> bool:
        """判断是否应该遗忘

        Args:
            item: 记忆项
            threshold: 遗忘阈值，保持率低于此值则遗忘

        Returns:
            True 表示应遗忘
        """
        # CRITICAL 永不遗忘
        if self._get_importance_value(item) >= 5:
            return False
        return self.calculate_retention(item) < threshold

    def apply_forgetting(
        self,
        events: list[EpisodicEvent],
        current_time: float | None = None,
    ) -> tuple[list[EpisodicEvent], list[EpisodicEvent]]:
        """批量应用遗忘曲线

        Args:
            events: 情景事件列表
            current_time: 当前时间戳

        Returns:
            (保留列表, 遗忘列表)
        """
        kept: list[EpisodicEvent] = []
        forgotten: list[EpisodicEvent] = []
        for event in events:
            if self.should_forget(event, threshold=0.1):
                forgotten.append(event)
            else:
                kept.append(event)
        return kept, forgotten

    def boost_memory(
        self,
        item_id: str,
        events: list[EpisodicEvent],
    ) -> None:
        """访问后增强记忆（更新last_accessed和access_count）

        Args:
            item_id: 要增强的记忆项ID
            events: 事件列表（在其中查找匹配项并更新）
        """
        now = time.time()
        for event in events:
            if event.id == item_id:
                event.last_accessed = now
                event.access_count += 1
