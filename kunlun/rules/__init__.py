"""
昆仑创作引擎 — 三层规则分离系统 (Three-Layer Rule Separation)

灵感来源: InkOS 三层规则分离架构
核心设计:
  规则来源层 (engine.py):
    Layer 1 — 通用规则 (Universal Rules): 适用于所有网文的普适规则
    Layer 2 — 题材规则 (Genre Rules): 特定题材的专属规则
    Layer 3 — 书籍规则 (Book Rules): 单本书的自定义规则
  优先级: 书籍规则 > 题材规则 > 通用规则 (后层覆盖前层)

  规则执行层 (layers.py):
    HARD  — 硬规则: 逻辑矛盾、世界观冲突 (auto-reject)
    SOFT  — 软规则: 风格偏离、节奏问题 (warn)
    AI_GUIDE — AI引导: 创意方向、爽点建议 (suggest)
"""

from __future__ import annotations

from kunlun.rules.engine import (
    UNIVERSAL_RULES,
    Rule,
    RuleCategory,
    RuleEngine,
    RuleLayer,
    RuleSeverity,
    RuleStack,
    get_rule_engine,
)
from kunlun.rules.layers import (
    ALL_BUILTIN_RULES,
    BUILTIN_AI_RULES,
    BUILTIN_HARD_RULES,
    BUILTIN_SOFT_RULES,
    RuleResult,
    get_layer_engine,
    reset_layer_engine,
)
from kunlun.rules.layers import (
    Rule as LayeredRule,
)
from kunlun.rules.layers import (
    RuleEngine as LayerRuleEngine,
)
from kunlun.rules.layers import (
    RuleLayer as EnforcementLayer,
)

__all__ = [
    "ALL_BUILTIN_RULES",
    "BUILTIN_AI_RULES",
    "BUILTIN_HARD_RULES",
    "BUILTIN_SOFT_RULES",
    "UNIVERSAL_RULES",
    "EnforcementLayer",
    "LayerRuleEngine",
    "LayeredRule",
    "Rule",
    "RuleCategory",
    "RuleEngine",
    "RuleLayer",
    "RuleResult",
    "RuleSeverity",
    "RuleStack",
    "get_layer_engine",
    "get_rule_engine",
    "reset_layer_engine",
]
