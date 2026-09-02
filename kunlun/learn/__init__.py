"""
LearnAgent 偏好学习模块

7类事件监听 → 50维偏好向量 → 注入创作 pipeline

使用:
    from kunlun.learn import get_learner, on_creation_event

    learner = get_learner("my_book")
    learner.on_event("AUDIT_FAILED", {"gate": "G3", "reason": "AI味过重"})

    # 获取 prompt 提示
    hints = learner.get_prompt_hints()
"""

from kunlun.learn.learner import (
    PREFERENCE_DIM_LABELS,
    LearnAgent,
    PreferenceVector,
    get_learner,
    on_creation_event,
)

__all__ = [
    "PREFERENCE_DIM_LABELS",
    "LearnAgent",
    "PreferenceVector",
    "get_learner",
    "on_creation_event",
]
