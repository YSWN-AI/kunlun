"""
黄金三章引擎 — 开篇创作核心模块

提供:
- 6种开篇原型（悬念/冲突/反差/日常异常/强者归来/系统降临）
- 5维钩子评分（冲突强度/信息差/情绪冲击/代入感/节奏感）
- 黄金三章模板生成（含平台适配：起点/番茄/七猫）
- GachaEngine集成 + Agent系统集成

用法:
    from kunlun.golden_triple import (
        golden_triple_engine,
        GoldenTripleEngine,
        GoldenTripleAgent,
    )
"""

from kunlun.golden_triple.engine import (
    ChapterPlan,
    GoldenTripleAgent,
    GoldenTripleEngine,
    HookScore,
    golden_triple_engine,
)
from kunlun.golden_triple.templates import (
    ARCHETYPES,
    CHAPTER_THREE_PLAN,
    CORE_TEMPLATES,
    ArchetypeTemplate,
    CoreTemplate,
)

__all__ = [
    "ARCHETYPES",
    "CHAPTER_THREE_PLAN",
    "CORE_TEMPLATES",
    "ArchetypeTemplate",
    "ChapterPlan",
    "CoreTemplate",
    "GoldenTripleAgent",
    "GoldenTripleEngine",
    "HookScore",
    "golden_triple_engine",
]
