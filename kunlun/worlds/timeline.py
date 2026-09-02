"""
昆仑创作引擎 — 世界历史时间线 (TimelineEngine)

因果链引擎。
"""

from __future__ import annotations

from pathlib import Path

from kunlun.config import settings
from kunlun.worlds.types import TimelineEvent

# ══════════════════════════════════════════════════════
# TimelineEngine — 世界历史时间线
# ══════════════════════════════════════════════════════


class TimelineEngine:
    """世界历史时间线 — 因果链引擎"""

    def __init__(self, book_id: str = "") -> None:
        self.book_id = book_id
        self._events: dict[str, TimelineEvent] = {}
        self._eras: list[str] = ["上古", "中古", "近古", "当代"]
        self._data_dir = Path(settings.DATA_DIR) / "worlds" / book_id if book_id else None

    def add_event(self, event: TimelineEvent) -> None:
        self._events[event.event_id] = event

    def get_event(self, event_id: str) -> TimelineEvent | None:
        return self._events.get(event_id)

    def get_events_by_era(self, era: str) -> list[TimelineEvent]:
        return [e for e in self._events.values() if e.era == era]

    def get_timeline(self) -> list[TimelineEvent]:
        """按时代排序返回所有事件"""
        era_order = {e: i for i, e in enumerate(self._eras)}
        return sorted(self._events.values(), key=lambda e: (era_order.get(e.era, 99), e.year or ""))

    def detect_causal_chains(self) -> list[list[str]]:
        """检测因果链"""
        chains = []
        visited = set()

        def trace(event_id: str, chain: list[str]) -> None:
            if event_id in visited:
                if chain:
                    chains.append(chain[:])
                return
            visited.add(event_id)
            chain.append(event_id)
            event = self._events.get(event_id)
            if event and event.consequences:
                for cid in event.consequences:
                    trace(cid, chain)
            else:
                chains.append(chain[:])

        for eid, event in self._events.items():
            if eid not in visited and not event.prerequisites:
                trace(eid, [])

        return [c for c in chains if len(c) > 1]

    def export_markdown(self) -> str:
        """导出 Markdown 格式时间线"""
        lines = ["# 世界历史时间线\n"]
        for era in self._eras:
            events = self.get_events_by_era(era)
            if not events:
                continue
            lines.append(f"## {era}\n")
            for e in events:
                year_str = f"({e.year})" if e.year else ""
                lines.append(f"- **{e.name}** {year_str}: {e.description}")
            lines.append("")
        return "\n".join(lines)

    def check_timeline_consistency(self) -> list[str]:
        """时间线一致性检查"""
        issues = []
        for event in self._events.values():
            issues.extend(
                f"事件'{event.name}'的前置事件'{pid}'不存在"
                for pid in event.prerequisites
                if pid not in self._events
            )
        return issues
