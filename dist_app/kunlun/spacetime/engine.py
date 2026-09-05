"""
时空引擎 — 故事世界时空管理

功能:
- 空间节点管理 (SpaceNode) — 地点/场景层级
- 时间节点管理 (TimeNode) — 时间线事件
- 时空事件关联 (SpacetimeEvent) — 事件在时空中的位置

用法:
    from kunlun.spacetime import SpacetimeEngine, SpaceNode, TimeNode, SpacetimeEvent
    engine = SpacetimeEngine(book_id="book_001")
    engine.add_space("天庭", parent="仙界", chapter=5)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpaceNode:
    """空间节点"""

    name: str = ""
    space_id: str = ""
    parent: str = ""
    space_type: str = "location"  # location / region / realm / building
    description: str = ""
    first_appeared: int = 0
    last_appeared: int = 0
    chapter_count: int = 0
    tags: list[str] = field(default_factory=list)


@dataclass
class TimeNode:
    """时间节点"""

    name: str = ""
    time_id: str = ""
    chapter: int = 0
    timestamp: str = ""  # 故事内时间描述 (e.g. "仙历三百二十年")
    event_count: int = 0
    description: str = ""


@dataclass
class SpacetimeEvent:
    """时空事件"""

    event_id: str = ""
    description: str = ""
    chapter: int = 0
    space_name: str = ""
    time_name: str = ""
    characters: list[str] = field(default_factory=list)
    importance: int = 0  # 重要性 1-5


class SpacetimeEngine:
    """时空引擎

    管理故事中的空间（地点）和时间（时间线）信息。

    用法:
        engine = SpacetimeEngine(book_id="book_001")
        engine.add_space("天庭", description="天界最高统治机构所在地")
        engine.add_event("主角飞升", chapter=42, space_name="天庭")
    """

    def __init__(self, book_id: str = ""):
        self.book_id = book_id
        self._spaces: dict[str, SpaceNode] = {}
        self._times: dict[str, TimeNode] = {}
        self._events: dict[str, SpacetimeEvent] = {}

    def add_space(
        self,
        name: str,
        parent: str = "",
        space_type: str = "location",
        description: str = "",
        chapter: int = 0,
        tags: list[str] | None = None,
    ) -> SpaceNode:
        """添加空间节点"""
        import uuid

        space_id = str(uuid.uuid4())[:8]
        node = SpaceNode(
            name=name,
            space_id=space_id,
            parent=parent,
            space_type=space_type,
            description=description,
            first_appeared=chapter,
            last_appeared=chapter,
            chapter_count=1 if chapter else 0,
            tags=tags or [],
        )
        self._spaces[space_id] = node
        return node

    def get_space(self, space_id: str) -> SpaceNode | None:
        return self._spaces.get(space_id)

    def find_space_by_name(self, name: str) -> SpaceNode | None:
        for s in self._spaces.values():
            if s.name == name:
                return s
        return None

    def list_spaces(self) -> list[SpaceNode]:
        return sorted(self._spaces.values(), key=lambda s: -s.chapter_count)

    def add_event(
        self,
        description: str,
        chapter: int = 0,
        space_name: str = "",
        time_name: str = "",
        characters: list[str] | None = None,
        importance: int = 0,
    ) -> SpacetimeEvent:
        """添加时空事件"""
        import uuid

        event = SpacetimeEvent(
            event_id=str(uuid.uuid4())[:8],
            description=description,
            chapter=chapter,
            space_name=space_name,
            time_name=time_name,
            characters=characters or [],
            importance=importance,
        )
        self._events[event.event_id] = event
        return event

    def get_events_by_chapter(self, chapter: int) -> list[SpacetimeEvent]:
        return [e for e in self._events.values() if e.chapter == chapter]

    def get_events_by_space(self, space_name: str) -> list[SpacetimeEvent]:
        return [e for e in self._events.values() if e.space_name == space_name]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_spaces": len(self._spaces),
            "total_events": len(self._events),
            "space_types": list({s.space_type for s in self._spaces.values()}),
        }


# 全局单例
spacetime_engine = SpacetimeEngine()
