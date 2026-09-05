"""
昆仑创作引擎 — 角色设定引擎 (Character Engine)

深度融合 Dramatica 7角色职能 + StoryCraft Studio 角色关系图 + 网文角色弧线理论。

子模块:
  - types: 枚举定义 + 数据类（零外部依赖）
  - engine: 引擎类 + 分析器 + 统一入口
"""

from kunlun.character.engine import (
    CharacterArcEngine,
    CharacterConsistencyChecker,
    CharacterDialogueStyleAnalyzer,
    CharacterEngine,
    CharacterRelationshipGraph,
    character_engine,
)
from kunlun.character.types import (
    CharacterArcType,
    CharacterDialogueStyle,
    CharacterProfile,
    CharacterRole,
    DramaticaRole,
    RelationshipType,
)

__all__ = [
    "CharacterArcEngine",
    "CharacterArcType",
    "CharacterConsistencyChecker",
    "CharacterDialogueStyle",
    "CharacterDialogueStyleAnalyzer",
    "CharacterEngine",
    "CharacterProfile",
    "CharacterRelationshipGraph",
    "CharacterRole",
    "DramaticaRole",
    "RelationshipType",
    "character_engine",
]
