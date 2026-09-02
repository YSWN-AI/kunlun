"""
昆仑创作引擎 — 情节推演与伏笔管理 (Plot Engine)

深度融合 Dramatica-Flow 因果链引擎 + SCORE 论文的连贯性检索增强。

子模块:
  - types: 枚举定义 + 数据类（零外部依赖）
  - engine: 因果链引擎 + 伏笔管理 + 冲突引擎 + 节奏控制
"""

from kunlun.plot.engine import (
    CausalChainEngine,
    ConflictEngine,
    ForeshadowingManager,
    PacingController,
    causal_chain_engine,
    conflict_engine,
    foreshadowing_manager,
    pacing_controller,
)
from kunlun.plot.types import (
    CausalEvent,
    ConflictType,
    ForeshadowingItem,
    ForeshadowingStatus,
    NarrativeThread,
    PacingProfile,
)
