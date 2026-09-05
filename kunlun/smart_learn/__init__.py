"""
昆仑创作引擎 — 智能学习增强 (Smart Learn)

从用户反馈/修改中自动提取写作偏好，更新学习历史，并可输出为 KUNLUN.md 约束。

用法:
    from kunlun.smart_learn import PreferenceExtractor, LearningHistory
    from kunlun.smart_learn import get_preference_extractor, get_learning_history

    extractor = get_preference_extractor()
    pref = extractor.extract_from_feedback("让对话不那么正式")

    history = get_learning_history()
    history.add_record("book_001", pref)
"""

from kunlun.smart_learn.extractor import (
    PreferenceExtractor,
    get_preference_extractor,
)
from kunlun.smart_learn.history import LearningHistory, get_learning_history

__all__ = [
    "LearningHistory",
    "PreferenceExtractor",
    "get_learning_history",
    "get_preference_extractor",
]
