"""
昆仑创作引擎 — 长文本连贯性引擎 (Coherence Engine)

深度融合 SCORE 论文 + GraphRAG + DOME 动态层级大纲。

子模块:
  - types: 数据类（ChapterSummary、TrackedItem、CoherenceIssue）
  - engine: 摘要链 + 状态追踪 + 上下文管理 + 统一入口
"""

from kunlun.coherence.engine import (
    ChapterSummaryChain,
    CoherenceEngine,
    ContextWindowManager,
    KeyItemTracker,
    coherence_engine,
)
from kunlun.coherence.types import (
    ChapterSummary,
    CoherenceIssue,
    TrackedItem,
)

__all__ = [
    "ChapterSummary",
    "ChapterSummaryChain",
    "CoherenceEngine",
    "CoherenceIssue",
    "ContextWindowManager",
    "KeyItemTracker",
    "TrackedItem",
    "coherence_engine",
]
