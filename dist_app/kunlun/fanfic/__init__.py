"""
昆仑创作引擎 — 同人创作模式

支持基于已有IP/正典的二次创作，区别于原创的专属功能:
  1. 正典导入 — 导入原作的角色/事件/设定/时间线
  2. 同人审计维度 — OOC检测 / 正典一致性 / 同人创新度
  3. 正典知识库 — 基于原作构建可检索的知识图谱
  4. 同人规则层 — 在原作规则之上叠加同人创作约束
"""

from kunlun.fanfic.engine import (
    CanonCharacter,
    CanonImport,
    CanonImporter,
    CanonSetting,
    FanficKnowledgeBase,
    FanficMode,
    OOCDetector,
    OOCReport,
    OOCSeverity,
    get_fanfic_kb,
)

__all__ = [
    "CanonCharacter",
    "CanonImport",
    "CanonImporter",
    "CanonSetting",
    "FanficKnowledgeBase",
    "FanficMode",
    "OOCDetector",
    "OOCReport",
    "OOCSeverity",
    "get_fanfic_kb",
]
