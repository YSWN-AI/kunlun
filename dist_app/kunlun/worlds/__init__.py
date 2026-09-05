"""
worlds 扩展模块
"""

from __future__ import annotations

from kunlun.worlds.atlas import WorldAtlas
from kunlun.worlds.builder import WorldBuilder, create_world_builder
from kunlun.worlds.engine import (
    ConsistencyIssue,
    Dimension,
    OverflowReport,
    Severity,
    WorldAuditReport,
    WorldConsistencyChecker,
    WorldOverflowChecker,
    WorldSetting,
    WorldSettingManager,
    get_world_checker,
    get_world_manager,
)
from kunlun.worlds.faction import FactionNetwork
from kunlun.worlds.timeline import TimelineEngine
from kunlun.worlds.types import (
    FactionNode,
    FactionType,
    LocationCard,
    LocationType,
    RelationType,
    TimelineEvent,
)

__all__ = [
    "ConsistencyIssue",
    "Dimension",
    # builder 新增
    "FactionNetwork",
    "FactionNode",
    "FactionType",
    "LocationCard",
    "LocationType",
    "OverflowReport",
    "RelationType",
    "Severity",
    "TimelineEngine",
    "TimelineEvent",
    "WorldAtlas",
    "WorldAuditReport",
    "WorldBuilder",
    "WorldConsistencyChecker",
    "WorldOverflowChecker",
    "WorldSetting",
    "WorldSettingManager",
    "create_world_builder",
    "get_world_checker",
    "get_world_manager",
]
