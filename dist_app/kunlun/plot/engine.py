"""
昆仑创作引擎 — 情节引擎

深度融合 Dramatica-Flow 因果链引擎 + 伏笔生命周期管理 + 冲突引擎 + 节奏控制。

核心类:
  - CausalChainEngine: 因果链引擎
  - ForeshadowingManager: 伏笔生命周期管理
  - ConflictEngine: 冲突引擎
  - PacingController: 节奏控制器
"""

from __future__ import annotations

import re
from typing import ClassVar

from loguru import logger

from kunlun.plot.types import (
    CausalEvent,
    ConflictType,
    ForeshadowingItem,
    ForeshadowingStatus,
    PacingProfile,
)

# ══════════════════════════════════════════════════════
# CausalChainEngine — 因果链引擎
# ══════════════════════════════════════════════════════


class CausalChainEngine:
    """因果链引擎 — Dramatica-Flow 核心

    每个事件都遵循严格的因果结构：
      因（Cause）→ 事（Event）→ 果（Effect）→ 决（Decision）
    """

    def __init__(self) -> None:
        self._events: dict[str, CausalEvent] = {}
        self._chapter_events: dict[int, list[str]] = {}  # 章节 → 事件ID列表

    def add_event(self, event: CausalEvent) -> None:
        self._events[event.event_id] = event
        self._chapter_events.setdefault(event.chapter_num, []).append(event.event_id)

    def get_chain(self, start_event_id: str, max_depth: int = 10) -> list[CausalEvent]:
        """获取从某个事件开始的因果链"""
        chain: list[CausalEvent] = []
        current_id = start_event_id
        visited = set()

        while current_id and len(chain) < max_depth:
            if current_id in visited:
                break
            visited.add(current_id)

            event = self._events.get(current_id)
            if not event:
                break
            chain.append(event)

            if event.consequences:
                current_id = event.consequences[0]
            else:
                break

        return chain

    def get_context_for_chapter(self, chapter_num: int, context_window: int = 5) -> str:
        """为章节生成因果链上下文（注入 Architect/Writer prompt）"""
        lines = ["## 因果链上下文\n"]

        for ch in range(max(1, chapter_num - context_window), chapter_num):
            event_ids = self._chapter_events.get(ch, [])
            for eid in event_ids[-3:]:  # 每章最多3个事件
                event = self._events.get(eid)
                if not event:
                    continue
                lines.append(f"- 第{ch}章【{event.name}】")
                if event.cause:
                    lines.append(f"  因：{event.cause}")
                if event.effect:
                    lines.append(f"  果：{event.effect}")
                if event.decision:
                    lines.append(f"  决：{event.decision}")

        return "\n".join(lines) if len(lines) > 1 else ""

    def detect_broken_chains(self) -> list[dict]:
        """检测断裂的因果链"""
        broken: list[dict] = []
        for eid, event in self._events.items():
            broken.extend(
                {
                    "event_id": eid,
                    "event_name": event.name,
                    "issue": f"前置事件'{pid}'不存在",
                    "severity": "high",
                }
                for pid in event.prerequisites
                if pid not in self._events
            )
            if not event.consequences and event.chapter_num < max(
                self._chapter_events.keys(), default=0
            ):
                broken.append(
                    {
                        "event_id": eid,
                        "event_name": event.name,
                        "issue": "缺少后果事件，因果链断裂",
                        "severity": "medium",
                    }
                )
        return broken

    def get_causal_graph_data(self) -> dict:
        """生成因果链图数据"""
        nodes = [
            {"id": eid, "name": e.name, "chapter": e.chapter_num, "tension": e.tension_level}
            for eid, e in self._events.items()
        ]
        edges = [
            {"source": eid, "target": cid}
            for eid, event in self._events.items()
            for cid in event.consequences
            if cid in self._events
        ]
        return {"nodes": nodes, "edges": edges}


# ══════════════════════════════════════════════════════
# ForeshadowingManager — 伏笔生命周期管理
# ══════════════════════════════════════════════════════


class ForeshadowingManager:
    """伏笔生命周期管理 — Dramatica-Flow 四种叙事承诺"""

    MAX_OVERDUE_CHAPTERS = 15

    def __init__(self) -> None:
        self._items: dict[str, ForeshadowingItem] = {}

    def plant(self, item: ForeshadowingItem) -> None:
        self._items[item.foreshadow_id] = item
        logger.debug(f"Foreshadowing: 埋设伏笔 '{item.name}'（第{item.planted_chapter}章）")

    def reinforce(self, foreshadow_id: str, chapter_num: int) -> bool:
        item = self._items.get(foreshadow_id)
        if not item:
            return False
        item.reinforced_at.append(chapter_num)
        item.status = ForeshadowingStatus.REINFORCED
        return True

    def recycle(self, foreshadow_id: str, chapter_num: int) -> bool:
        item = self._items.get(foreshadow_id)
        if not item:
            return False
        item.status = ForeshadowingStatus.RECYCLED
        item.recycled_at = chapter_num
        item.overdue_warning = False
        logger.info(
            f"Foreshadowing: 回收伏笔 '{item.name}'"
            f"（第{chapter_num}章，埋设于第{item.planted_chapter}章）"
        )
        return True

    def half_reveal(self, foreshadow_id: str) -> bool:
        item = self._items.get(foreshadow_id)
        if not item:
            return False
        item.status = ForeshadowingStatus.HALF_REVEALED
        return True

    def check_overdue(self, current_chapter: int) -> list[ForeshadowingItem]:
        overdue = []
        for item in self._items.values():
            if item.status in (ForeshadowingStatus.PLANTED, ForeshadowingStatus.REINFORCED):
                distance = current_chapter - item.planted_chapter
                if distance > self.MAX_OVERDUE_CHAPTERS or (
                    item.target_chapter > 0 and current_chapter > item.target_chapter
                ):
                    item.overdue_warning = True
                    overdue.append(item)
        return overdue

    def get_pending_foreshadows(self) -> list[ForeshadowingItem]:
        return [
            item
            for item in self._items.values()
            if item.status
            in (
                ForeshadowingStatus.PLANTED,
                ForeshadowingStatus.REINFORCED,
                ForeshadowingStatus.HALF_REVEALED,
            )
        ]

    def get_stats(self) -> dict:
        total = len(self._items)
        planted = sum(1 for i in self._items.values() if i.status == ForeshadowingStatus.PLANTED)
        reinforced = sum(
            1 for i in self._items.values() if i.status == ForeshadowingStatus.REINFORCED
        )
        half = sum(1 for i in self._items.values() if i.status == ForeshadowingStatus.HALF_REVEALED)
        recycled = sum(1 for i in self._items.values() if i.status == ForeshadowingStatus.RECYCLED)
        overdue = sum(1 for i in self._items.values() if i.overdue_warning)
        return {
            "total": total,
            "planted": planted,
            "reinforced": reinforced,
            "half_revealed": half,
            "recycled": recycled,
            "recycle_rate": round(recycled / max(total, 1) * 100, 1),
            "overdue": overdue,
        }

    def get_context_for_chapter(self, current_chapter: int) -> str:
        pending = self.get_pending_foreshadows()
        overdue = self.check_overdue(current_chapter)
        lines = []
        if overdue:
            lines.append("⚠️ 以下伏笔已过期未回收，请在本章考虑回收：")
            lines.extend(
                f"- {item.name}（埋设于第{item.planted_chapter}章，"
                f"已过{current_chapter - item.planted_chapter}章）"
                for item in overdue[:3]
            )
        if pending and not overdue:
            lines.append("📌 以下伏笔待回收：")
            for item in pending[:5]:
                target = f"，计划第{item.target_chapter}章回收" if item.target_chapter else ""
                lines.append(f"- {item.name}（第{item.planted_chapter}章埋设{target}）")
        return "\n".join(lines) if lines else ""


# ══════════════════════════════════════════════════════
# ConflictEngine — 冲突引擎
# ══════════════════════════════════════════════════════


class ConflictEngine:
    """冲突引擎 — 确保每个场景都有足够的戏剧冲突"""

    CONFLICT_MARKERS: ClassVar[dict[ConflictType, list[str]]] = {
        ConflictType.PERSON_VS_PERSON: ["对决", "对抗", "交手", "对峙", "谈判破裂"],
        ConflictType.PERSON_VS_SELF: ["挣扎", "犹豫", "矛盾", "自责", "怀疑自己"],
        ConflictType.PERSON_VS_SOCIETY: ["规则", "不公", "压迫", "体制", "偏见"],
        ConflictType.PERSON_VS_NATURE: ["天劫", "雷劫", "绝境", "天灾"],
        ConflictType.PERSON_VS_FATE: ["命运", "宿命", "注定", "逆天"],
        ConflictType.PERSON_VS_SYSTEM: ["系统", "天道", "法则", "规则之力"],
    }

    @classmethod
    def detect_conflicts(cls, text: str) -> dict[ConflictType, float]:
        scores: dict[ConflictType, float] = {}
        for ctype, markers in cls.CONFLICT_MARKERS.items():
            hits = sum(1 for m in markers if m in text)
            scores[ctype] = min(hits / max(len(markers), 1) * 3, 1.0)
        return scores

    @classmethod
    def has_sufficient_conflict(cls, text: str, min_level: float = 0.1) -> bool:
        scores = cls.detect_conflicts(text)
        return max(scores.values()) >= min_level if scores else False

    @classmethod
    def get_primary_conflict(cls, text: str) -> ConflictType | None:
        scores = cls.detect_conflicts(text)
        if not scores:
            return None
        return max(scores, key=lambda k: scores[k])

    @classmethod
    def suggest_conflict(cls, current_type: ConflictType | None = None) -> str:
        suggestions = {
            ConflictType.PERSON_VS_PERSON: "增加角色间的直接对抗或价值观冲突",
            ConflictType.PERSON_VS_SELF: "增加角色内心的挣扎和矛盾",
            ConflictType.PERSON_VS_SOCIETY: "增加角色与社会规则/偏见的冲突",
            ConflictType.PERSON_VS_NATURE: "增加天劫/自然灾害/绝境求生",
            ConflictType.PERSON_VS_FATE: "增加角色与命运的对抗",
            ConflictType.PERSON_VS_SYSTEM: "增加角色与修炼体系/天道规则的对抗",
        }
        if current_type is not None:
            return suggestions.get(current_type, "增加任意类型的戏剧冲突")
        return "增加任意类型的戏剧冲突"


# ══════════════════════════════════════════════════════
# PacingController — 节奏控制器
# ══════════════════════════════════════════════════════


class PacingController:
    """节奏控制器 — 确保叙事节奏张弛有度"""

    def __init__(self) -> None:
        self._chapter_pacing: dict[int, PacingProfile] = {}
        self._default_profile = PacingProfile(chapter_num=0)

    def set_profile(self, chapter_num: int, profile: PacingProfile) -> None:
        profile.chapter_num = chapter_num
        self._chapter_pacing[chapter_num] = profile

    def get_profile(self, chapter_num: int) -> PacingProfile:
        return self._chapter_pacing.get(chapter_num, self._default_profile)

    def analyze_chapter_pacing(self, text: str) -> dict:
        total = len(text)
        if total < 100:
            return {"error": "文本过短"}

        dialogue_chars = len(re.findall(r'[""][^""]*[""]', text)) + len(
            re.findall(r"「[^」]*」", text)
        )
        return {
            "total_chars": total,
            "estimated_dialogue_ratio": round(dialogue_chars * 3 / max(total, 1), 2),
        }

    def check_pacing_health(self, _chapter_num: int, text: str) -> list[str]:
        issues: list[str] = []
        pacing = self.analyze_chapter_pacing(text)
        if pacing.get("error"):
            return issues
        dialogue_ratio = pacing.get("estimated_dialogue_ratio", 0.3)
        if dialogue_ratio > 0.6:
            issues.append("对话比例过高，建议增加叙事和动作描写")
        elif dialogue_ratio < 0.1 and len(text) > 2000:
            issues.append("对话比例过低，建议增加角色互动")
        return issues


# ══════════════════════════════════════════════════════
# 模块级便捷实例
# ══════════════════════════════════════════════════════

causal_chain_engine = CausalChainEngine()
foreshadowing_manager = ForeshadowingManager()
conflict_engine = ConflictEngine()
pacing_controller = PacingController()
