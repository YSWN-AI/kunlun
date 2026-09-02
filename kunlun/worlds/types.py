"""
昆仑创作引擎 — 世界观类型定义

包含枚举和数据类：FactionType, RelationType, LocationType, LocationCard, FactionNode, TimelineEvent
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class FactionType(StrEnum):
    EMPIRE = "empire"
    KINGDOM = "kingdom"
    SECT = "sect"
    CLAN = "clan"
    GUILD = "guild"
    TRIBE = "tribe"
    ALLIANCE = "alliance"
    ORDER = "order"
    MERCHANT = "merchant"
    REBEL = "rebel"
    NEUTRAL = "neutral"
    OTHER = "other"


class RelationType(StrEnum):
    ALLIANCE = "alliance"
    HOSTILE = "hostile"
    VASSAL = "vassal"
    TRADE = "trade"
    RIVALRY = "rivalry"
    NEUTRAL = "neutral"
    MARRIAGE = "marriage"
    BLOOD_FEUD = "blood_feud"


class LocationType(StrEnum):
    CONTINENT = "continent"
    REGION = "region"
    KINGDOM = "kingdom"
    CITY = "city"
    TOWN = "town"
    VILLAGE = "village"
    DUNGEON = "dungeon"
    SECT = "sect"
    WILDERNESS = "wilderness"
    RUIN = "ruin"
    TEMPLE = "temple"
    ACADEMY = "academy"
    OTHER = "other"


# ══════════════════════════════════════════════════════
# 数据类
# ══════════════════════════════════════════════════════


@dataclass
class LocationCard:
    """地点卡片 — StoryCraft Studio 交互式图集的核心数据单元"""

    location_id: str
    name: str
    location_type: LocationType = LocationType.OTHER
    parent_id: str = ""
    description: str = ""
    climate: str = ""
    population: str = ""
    ruler: str = ""
    resources: list[str] = field(default_factory=list)
    connections: list[dict] = field(default_factory=list)  # [{to_id, type, distance}]
    completeness: int = 0  # 0-100

    def calculate_completeness(self) -> int:
        """计算地点完善度"""
        score = 0
        if self.description:
            score += 25
        if self.climate:
            score += 10
        if self.population:
            score += 15
        if self.ruler:
            score += 15
        if self.resources:
            score += 10
        if self.connections:
            score += 15
        if self.parent_id:
            score += 10
        return min(score, 100)


@dataclass
class FactionNode:
    """势力节点"""

    faction_id: str
    name: str
    faction_type: FactionType = FactionType.OTHER
    power_level: int = 50  # 0-100
    leader: str = ""
    members: list[str] = field(default_factory=list)
    territory: list[str] = field(default_factory=list)
    goal: str = ""
    description: str = ""
    relationships: list[dict] = field(default_factory=list)  # [{target_id, type, strength}]

    def get_relation_with(self, target_id: str) -> dict | None:
        for rel in self.relationships:
            if rel.get("target_id") == target_id:
                return rel
        return None


@dataclass
class TimelineEvent:
    """世界历史事件"""

    event_id: str
    name: str
    era: str = "当代"
    year: str = ""
    description: str = ""
    participants: list[str] = field(default_factory=list)
    location: str = ""
    prerequisites: list[str] = field(default_factory=list)  # 前置事件ID
    consequences: list[str] = field(default_factory=list)  # 后果事件ID
    impact_level: int = 1  # 1-5
