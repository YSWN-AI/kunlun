"""
张力分析 — 张力级别、章节张力评分、张力分析器
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class TensionLevel(StrEnum):
    """张力级别"""

    NONE = "none"  # 无张力
    LOW = "low"  # 低 — 日常/铺垫
    MEDIUM = "medium"  # 中 — 小冲突/摩擦
    HIGH = "high"  # 高 — 激烈对抗
    PEAK = "peak"  # 巅峰 — 决战/高潮

    @property
    def numeric(self) -> int:
        return {"none": 0, "low": 1, "medium": 2, "high": 3, "peak": 4}[self.value]


class ConflictType(StrEnum):
    """冲突类型（网文高频分类）"""

    PERSON_VS_PERSON = "person_vs_person"  # 人与人（对抗/战斗/斗智）
    PERSON_VS_SELF = "person_vs_self"  # 人与自我（心魔/选择/成长）
    PERSON_VS_SOCIETY = "person_vs_society"  # 人与社会（体制/宗门/家族）
    PERSON_VS_NATURE = "person_vs_nature"  # 人与自然（天劫/绝境/兽潮）
    PERSON_VS_FATE = "person_vs_fate"  # 人与命运（天道/宿命/预言）

    @property
    def label(self) -> str:
        labels = {
            "person_vs_person": "人与人",
            "person_vs_self": "人与自我",
            "person_vs_society": "人与社会",
            "person_vs_nature": "人与自然",
            "person_vs_fate": "人与命运",
        }
        return labels.get(self.value, self.value)


@dataclass
class ChapterTension:
    """章节张力评分"""

    chapter: int
    tension_level: TensionLevel = TensionLevel.NONE
    active_conflicts: list[str] = field(default_factory=list)
    conflict_types_present: list[ConflictType] = field(default_factory=list)
    tension_score: float = 0.0  # 0-1
    key_tension_events: list[str] = field(default_factory=list)


class TensionAnalyzer:
    """张力分析器 — 基于关键词+句式的纯规则分析"""

    # 冲突关键词（中文网文高频）
    CONFLICT_KEYWORDS: dict[ConflictType, list[tuple[str, float]]] = {
        ConflictType.PERSON_VS_PERSON: [
            ("战斗", 0.3),
            ("对决", 0.4),
            ("厮杀", 0.5),
            ("激战", 0.5),
            ("交手", 0.2),
            ("围攻", 0.4),
            ("单挑", 0.3),
            ("拼死", 0.5),
            ("击败", 0.3),
            ("斩杀", 0.4),
            ("秒杀", 0.3),
            ("压制", 0.3),
            ("挑衅", 0.2),
            ("威胁", 0.2),
            ("嘲讽", 0.1),
            ("对峙", 0.3),
            ("谈判破裂", 0.4),
            ("反目", 0.4),
            ("背叛", 0.5),
        ],
        ConflictType.PERSON_VS_SELF: [
            ("心魔", 0.5),
            ("挣扎", 0.3),
            ("纠结", 0.2),
            ("犹豫", 0.2),
            ("动摇", 0.3),
            ("质疑自己", 0.4),
            ("自我否定", 0.4),
            ("突破自我", 0.4),
            ("明悟", 0.3),
            ("顿悟", 0.4),
            ("选择", 0.2),
            ("抉择", 0.3),
            ("两难", 0.4),
        ],
        ConflictType.PERSON_VS_SOCIETY: [
            ("宗门", 0.2),
            ("家族", 0.2),
            ("势力", 0.2),
            ("联盟", 0.2),
            ("规则", 0.3),
            ("规矩", 0.2),
            ("传统", 0.2),
            ("排挤", 0.3),
            ("孤立", 0.3),
            ("打压", 0.3),
            ("陷害", 0.4),
            ("夺权", 0.4),
            ("篡位", 0.4),
            ("政变", 0.5),
        ],
        ConflictType.PERSON_VS_NATURE: [
            ("天劫", 0.5),
            ("雷劫", 0.5),
            ("天罚", 0.5),
            ("兽潮", 0.4),
            ("妖兽", 0.3),
            ("凶兽", 0.3),
            ("绝境", 0.4),
            ("绝地", 0.3),
            ("险境", 0.3),
            ("暴风雪", 0.2),
            ("地震", 0.3),
            ("火山", 0.3),
            ("洪水", 0.2),
        ],
        ConflictType.PERSON_VS_FATE: [
            ("宿命", 0.4),
            ("命运", 0.3),
            ("天道", 0.4),
            ("天意", 0.3),
            ("预言", 0.3),
            ("注定", 0.3),
            ("轮回", 0.3),
            ("逆天", 0.5),
            ("改命", 0.5),
            ("逆天改命", 0.6),
            ("诅咒", 0.4),
            ("劫数", 0.4),
        ],
    }

    # 张力增强句式
    TENSION_BOOSTERS: list[tuple[str, float]] = [
        ("突然", 0.1),
        ("猛然", 0.1),
        ("瞬间", 0.1),
        ("刹那", 0.1),
        ("轰", 0.2),
        ("砰", 0.2),
        ("杀", 0.15),
        ("死", 0.15),
        ("血", 0.1),
        ("剑光", 0.1),
        ("一刀", 0.1),
        ("竟然", 0.1),
        ("居然", 0.1),
        ("什么？", 0.15),
        ("不可能", 0.15),
        ("原来如此", 0.1),
        ("难怪", 0.05),
        (r"！{2,}", 0.1),  # 多个感叹号
    ]

    @classmethod
    def analyze_chapter(cls, text: str, chapter: int) -> ChapterTension:
        """分析章节张力"""
        conflict_types_present: set[ConflictType] = set()
        total_score = 0.0
        key_events: list[str] = []

        for conflict_type, keywords in cls.CONFLICT_KEYWORDS.items():
            type_score = 0.0
            for kw, weight in keywords:
                count = len(re.findall(kw, text))
                if count > 0:
                    conflict_types_present.add(conflict_type)
                    type_score += count * weight
                    if weight >= 0.4 and count >= 2:
                        key_events.append(f"{conflict_type.label}: {kw}(x{count})")

            total_score += type_score

        # 应用张力增强因子
        booster_score = 0.0
        for pattern, weight in cls.TENSION_BOOSTERS:
            count = len(re.findall(pattern, text))
            booster_score += count * weight
        total_score += booster_score

        # 归一化到0-1
        normalized = min(1.0, total_score / 10.0)

        # 判定张力级别
        if normalized >= 0.8:
            level = TensionLevel.PEAK
        elif normalized >= 0.5:
            level = TensionLevel.HIGH
        elif normalized >= 0.25:
            level = TensionLevel.MEDIUM
        elif normalized >= 0.1:
            level = TensionLevel.LOW
        else:
            level = TensionLevel.NONE

        return ChapterTension(
            chapter=chapter,
            tension_level=level,
            conflict_types_present=list(conflict_types_present),
            tension_score=round(normalized, 2),
            key_tension_events=key_events[:5],
        )
