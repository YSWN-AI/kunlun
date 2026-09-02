"""
昆仑创作引擎 — 分支剧情系统

对标竞品多分支叙事能力：分支点检测 → 树形结构 → 推荐引擎。
与现有冲突引擎 (conflict) 深度集成，复用冲突检测结果生成分支点。
"""

from kunlun.branch_plot.engine import (
    BranchPlotEngine,
    BranchRecommendation,
    get_branch_engine,
)
from kunlun.branch_plot.types import (
    BranchCondition,
    BranchConditionType,
    BranchNode,
    BranchPointType,
    BranchTree,
)

__all__ = [
    "BranchCondition",
    "BranchConditionType",
    "BranchNode",
    "BranchPlotEngine",
    "BranchPointType",
    "BranchRecommendation",
    "BranchTree",
    "get_branch_engine",
]
