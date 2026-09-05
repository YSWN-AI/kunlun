"""
conflict 扩展模块
"""

from kunlun.conflict.manager import (
    Conflict,
    ConflictManager,
    ConflictStatus,
    get_conflict_manager,
)
from kunlun.conflict.tension import (
    ChapterTension,
    ConflictType,
    TensionLevel,
)

__all__ = [
    "ChapterTension",
    "Conflict",
    "ConflictManager",
    "ConflictStatus",
    "ConflictType",
    "TensionLevel",
    "get_conflict_manager",
]
