"""
昆仑创作引擎 — 连贯性类型定义

包含连贯性相关的数据类（ChapterSummary、TrackedItem、CoherenceIssue）。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChapterSummary:
    """章节摘要 — SCORE 论文的"生成剧集摘要"概念"""

    chapter_num: int
    title: str = ""
    summary: str = ""  # 300字以内摘要
    key_events: list[str] = field(default_factory=list)
    character_changes: list[dict] = field(
        default_factory=list
    )  # [{character, change_type, detail}]
    new_items: list[str] = field(default_factory=list)
    new_locations: list[str] = field(default_factory=list)
    foreshadowing_planted: list[str] = field(default_factory=list)
    foreshadowing_recycled: list[str] = field(default_factory=list)
    emotion_tone: str = "neutral"


@dataclass
class TrackedItem:
    """追踪的物品/设定/角色状态 — SCORE 的"关键物品状态追踪" """

    item_id: str
    name: str
    category: str = "item"  # item/character/ability/location
    current_state: str = ""
    state_history: list[dict] = field(default_factory=list)  # [{chapter, state}]
    last_seen_chapter: int = 0

    def update_state(self, chapter_num: int, new_state: str) -> None:
        self.state_history.append({"chapter": chapter_num, "state": self.current_state})
        self.current_state = new_state
        self.last_seen_chapter = chapter_num

    def is_missing(self, current_chapter: int, max_gap: int = 10) -> bool:
        """物品是否'消失'过久"""
        return current_chapter - self.last_seen_chapter > max_gap


@dataclass
class CoherenceIssue:
    """连贯性问题"""

    category: str  # character/item/location/timeline/logic
    severity: str  # low/medium/high/critical
    chapter_a: int
    chapter_b: int
    description: str
    entity_name: str = ""
