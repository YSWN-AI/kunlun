"""
conflict 引擎核心实现
冲突张力管理

对标多智能体写作工具的剧情张力分析能力，
纯规则零LLM：5类冲突 + 张力曲线 + 章节张力评分。

Author: 昆仑创作引擎
"""

from __future__ import annotations

# 从拆分后的子模块重新导出所有符号，保持向后兼容
from kunlun.conflict.manager import (
    Conflict,
    ConflictManager,
    ConflictStatus,
    _conflict_managers,
    get_conflict_manager,
)
from kunlun.conflict.tension import (
    ChapterTension,
    ConflictType,
    TensionAnalyzer,
    TensionLevel,
)

__all__ = [
    "ChapterTension",
    "Conflict",
    "ConflictManager",
    "ConflictStatus",
    "ConflictType",
    "TensionAnalyzer",
    "TensionLevel",
    "_conflict_managers",
    "get_conflict_manager",
]
