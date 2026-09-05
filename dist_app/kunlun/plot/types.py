"""
昆仑创作引擎 — 情节类型定义

包含叙事相关的枚举（伏笔状态、叙事线程、冲突类型）
和数据类（CausalEvent、ForeshadowingItem、PacingProfile）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# ══════════════════════════════════════════════════════
# 枚举
# ══════════════════════════════════════════════════════


class ForeshadowingStatus(StrEnum):
    PLANTED = "planted"  # 已埋设
    REINFORCED = "reinforced"  # 已强化（多次提及）
    HALF_REVEALED = "half_revealed"  # 半揭示
    RECYCLED = "recycled"  # 已回收
    ABANDONED = "abandoned"  # 已废弃


class NarrativeThread(StrEnum):
    MAIN = "main"  # 主线
    SUB_A = "sub_a"  # 支线A
    SUB_B = "sub_b"  # 支线B
    PARALLEL = "parallel"  # 并行线
    FLASHBACK = "flashback"  # 闪回线


class ConflictType(StrEnum):
    PERSON_VS_PERSON = "person_vs_person"
    PERSON_VS_SELF = "person_vs_self"
    PERSON_VS_SOCIETY = "person_vs_society"
    PERSON_VS_NATURE = "person_vs_nature"
    PERSON_VS_FATE = "person_vs_fate"
    PERSON_VS_SYSTEM = "person_vs_system"  # 网文常见：与体制对抗


# ══════════════════════════════════════════════════════
# 数据类
# ══════════════════════════════════════════════════════


@dataclass
class CausalEvent:
    """因果链事件 — Dramatica-Flow 核心数据结构"""

    event_id: str
    chapter_num: int
    name: str

    # 因果四元组
    cause: str = ""  # 因：因为什么
    event: str = ""  # 事：发生了什么
    effect: str = ""  # 果：导致了什么
    decision: str = ""  # 决：角色做了什么决定

    # 关联
    prerequisites: list[str] = field(default_factory=list)  # 前置事件ID
    consequences: list[str] = field(default_factory=list)  # 后果事件ID
    participants: list[str] = field(default_factory=list)  # 参与角色
    thread: NarrativeThread = NarrativeThread.MAIN

    # 元数据
    tension_level: int = 1  # 1-5
    is_turning_point: bool = False


@dataclass
class ForeshadowingItem:
    """伏笔条目"""

    foreshadow_id: str
    name: str
    description: str

    # 生命周期
    planted_chapter: int
    target_chapter: int = 0  # 预期回收章节
    status: ForeshadowingStatus = ForeshadowingStatus.PLANTED

    # 类型
    foreshadow_type: str = "foreshadow"  # foreshadow/promise/mystery/conflict

    # 关联
    related_characters: list[str] = field(default_factory=list)
    related_events: list[str] = field(default_factory=list)

    # 追踪
    reinforced_at: list[int] = field(default_factory=list)  # 强化章节
    recycled_at: int = 0
    overdue_warning: bool = False


@dataclass
class PacingProfile:
    """节奏配置"""

    chapter_num: int
    target_words: int = 2500
    dialogue_ratio: float = 0.3
    action_ratio: float = 0.25
    description_ratio: float = 0.25
    internal_ratio: float = 0.2

    # 爽点配置
    min_pleasure_points: int = 1
    max_consecutive_slow_chapters: int = 2
