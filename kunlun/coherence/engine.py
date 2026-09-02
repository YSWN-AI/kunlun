"""
昆仑创作引擎 — 长文本连贯性引擎 (Coherence Engine)

深度融合 SCORE 论文 + GraphRAG + DOME 动态层级大纲。

核心类:
  - ChapterSummaryChain: 章节摘要链
  - KeyItemTracker: 关键物品/角色/设定状态追踪
  - ContextWindowManager: 上下文窗口管理器
  - CoherenceEngine: 统一入口
"""

from __future__ import annotations

from collections import OrderedDict
from typing import ClassVar

from kunlun.coherence.types import (
    ChapterSummary,
    CoherenceIssue,
    TrackedItem,
)

# ══════════════════════════════════════════════════════
# ChapterSummaryChain — 章节摘要链
# ══════════════════════════════════════════════════════


class ChapterSummaryChain:
    """章节摘要链 — SCORE 的动态记忆库"""

    def __init__(self, max_summaries: int = 200) -> None:
        self._summaries: OrderedDict[int, ChapterSummary] = OrderedDict()
        self._max_summaries = max_summaries

    def add_summary(self, summary: ChapterSummary) -> None:
        self._summaries[summary.chapter_num] = summary
        if len(self._summaries) > self._max_summaries:
            self._summaries.popitem(last=False)

    def get_summary(self, chapter_num: int) -> ChapterSummary | None:
        return self._summaries.get(chapter_num)

    def get_recent_summaries(self, count: int = 5) -> list[ChapterSummary]:
        items = list(self._summaries.values())
        return items[-count:] if len(items) >= count else items

    def get_context_for_chapter(self, current_chapter: int, window: int = 5) -> str:
        recent = self.get_recent_summaries(window)
        if not recent:
            return ""

        lines = ["## 前情摘要\n"]
        for s in recent:
            if s.chapter_num >= current_chapter:
                continue
            lines.append(f"### 第{s.chapter_num}章 {s.title}")
            lines.append(f"- {s.summary}")
            if s.key_events:
                lines.append(f"- 关键事件：{'、'.join(s.key_events[:3])}")
            if s.character_changes:
                changes = [f"{c['character']}{c['change_type']}" for c in s.character_changes[:2]]
                lines.append(f"- 角色变化：{'、'.join(changes)}")
            lines.append("")
        return "\n".join(lines)

    def find_relevant_chapters(self, query: str, max_results: int = 3) -> list[ChapterSummary]:
        query_words = set(query)
        scored = []
        for summary in self._summaries.values():
            text = summary.summary + " " + " ".join(summary.key_events)
            text_words = set(text)
            overlap = len(query_words & text_words)
            if overlap > 0:
                scored.append((overlap, summary))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:max_results]]

    def get_stats(self) -> dict:
        return {
            "total_summaries": len(self._summaries),
            "first_chapter": min(self._summaries.keys()) if self._summaries else 0,
            "last_chapter": max(self._summaries.keys()) if self._summaries else 0,
        }


# ══════════════════════════════════════════════════════
# KeyItemTracker — 关键物品状态追踪
# ══════════════════════════════════════════════════════


class KeyItemTracker:
    """关键物品/角色/设定状态追踪 — SCORE 核心机制"""

    def __init__(self) -> None:
        self._items: dict[str, TrackedItem] = {}

    def register(self, item: TrackedItem) -> None:
        self._items[item.item_id] = item

    def update(self, item_id: str, chapter_num: int, new_state: str) -> bool:
        item = self._items.get(item_id)
        if not item:
            return False
        item.update_state(chapter_num, new_state)
        return True

    def get_state(self, item_id: str) -> str | None:
        item = self._items.get(item_id)
        return item.current_state if item else None

    def get_history(self, item_id: str) -> list[dict]:
        item = self._items.get(item_id)
        return item.state_history if item else []

    def check_missing_items(self, current_chapter: int) -> list[TrackedItem]:
        return [
            item
            for item in self._items.values()
            if item.is_missing(current_chapter) and item.category == "item"
        ]

    def check_forgotten_abilities(self, current_chapter: int) -> list[TrackedItem]:
        return [
            item
            for item in self._items.values()
            if item.is_missing(current_chapter, max_gap=20) and item.category == "ability"
        ]

    def get_context_for_chapter(self, chapter_num: int) -> str:
        lines = [
            f"- {item.name}：{item.current_state}（最后出现：第{item.last_seen_chapter}章）"
            for item in self._items.values()
            if item.last_seen_chapter >= chapter_num - 5 and item.current_state
        ]
        if lines:
            return "## 关键物品/能力状态\n" + "\n".join(lines)
        return ""

    def get_stats(self) -> dict:
        return {
            "total_items": len(self._items),
            "by_category": {
                cat: sum(1 for i in self._items.values() if i.category == cat)
                for cat in {i.category for i in self._items.values()}
            },
        }


# ══════════════════════════════════════════════════════
# ContextWindowManager — 上下文窗口管理器
# ══════════════════════════════════════════════════════


class ContextWindowManager:
    """上下文窗口管理器 — DOME 动态层级大纲思想"""

    DEFAULT_BUDGET: ClassVar[dict[str, float]] = {
        "core": 0.20,
        "recent": 0.35,
        "retrieval": 0.25,
        "generation": 0.20,
    }

    def __init__(self, total_budget: int = 8000) -> None:
        self.total_budget = total_budget
        self._budget = self.DEFAULT_BUDGET.copy()

    def allocate(self, total_tokens: int | None = None) -> dict[str, int]:
        budget = total_tokens or self.total_budget
        return {layer: int(budget * ratio) for layer, ratio in self._budget.items()}

    def estimate_tokens(self, text: str) -> int:
        return max(1, int(len(text) / 1.5))

    def fit_context(self, layers: dict[str, str], max_tokens: int | None = None) -> dict[str, str]:
        allocation = self.allocate(max_tokens)
        fitted = {}
        for layer, budget in allocation.items():
            text = layers.get(layer, "")
            if not text:
                fitted[layer] = ""
                continue
            estimated = self.estimate_tokens(text)
            if estimated <= budget:
                fitted[layer] = text
            else:
                char_limit = int(budget * 1.5)
                fitted[layer] = text[:char_limit] + "\n...(上下文已截断)"
        return fitted

    def build_context_prompt(
        self, core_context: str, recent_context: str, retrieval_context: str = ""
    ) -> str:
        layers = {"core": core_context, "recent": recent_context, "retrieval": retrieval_context}
        fitted = self.fit_context(layers)
        parts = [v for v in fitted.values() if v]
        return "\n\n".join(parts)


# ══════════════════════════════════════════════════════
# CoherenceEngine — 连贯性引擎主入口
# ══════════════════════════════════════════════════════


class CoherenceEngine:
    """连贯性引擎 — 整合 SCORE 三大机制的完整方案"""

    def __init__(self, context_budget: int = 8000) -> None:
        self.summary_chain = ChapterSummaryChain()
        self.item_tracker = KeyItemTracker()
        self.context_manager = ContextWindowManager(total_budget=context_budget)

    def add_chapter(self, summary: ChapterSummary) -> None:
        self.summary_chain.add_summary(summary)

    def register_item(self, item: TrackedItem) -> None:
        self.item_tracker.register(item)

    def build_chapter_context(self, chapter_num: int, core_context: str = "") -> str:
        recent = self.summary_chain.get_context_for_chapter(chapter_num)
        item_state = self.item_tracker.get_context_for_chapter(chapter_num)
        retrieval = ""

        try:
            from kunlun.plot import foreshadowing_manager

            fs_context = foreshadowing_manager.get_context_for_chapter(chapter_num)
            if fs_context:
                retrieval += fs_context + "\n"
        except ImportError:
            pass

        missing_items = self.item_tracker.check_missing_items(chapter_num)
        if missing_items:
            retrieval += "⚠️ 以下物品/能力长期未出现：\n"
            for item in missing_items[:3]:
                retrieval += f"- {item.name}（最后出现：第{item.last_seen_chapter}章）\n"

        return self.context_manager.build_context_prompt(
            core_context=core_context,
            recent_context=recent + "\n" + item_state,
            retrieval_context=retrieval,
        )

    def check_cross_chapter_consistency(
        self, _chapter_a: int, _chapter_b: int
    ) -> list[CoherenceIssue]:
        issues: list[CoherenceIssue] = []
        for item in self.item_tracker._items.values():
            history = item.state_history
            if len(history) >= 2:
                for i in range(1, len(history)):
                    prev = history[i - 1]
                    curr = history[i]
                    if prev["state"] == "destroyed" and curr["state"] not in ("destroyed", ""):
                        issues.append(
                            CoherenceIssue(
                                category="item",
                                severity="high",
                                chapter_a=prev["chapter"],
                                chapter_b=curr["chapter"],
                                description=f"物品'{item.name}'在第{prev['chapter']}章已损坏，但在第{curr['chapter']}章被使用",
                                entity_name=item.name,
                            )
                        )
        return issues

    def get_health_report(self) -> dict:
        stats = self.summary_chain.get_stats()
        item_stats = self.item_tracker.get_stats()
        missing = self.item_tracker.check_missing_items(stats.get("last_chapter", 0))
        forgotten = self.item_tracker.check_forgotten_abilities(stats.get("last_chapter", 0))
        return {
            "summaries": stats,
            "items": item_stats,
            "missing_items": len(missing),
            "forgotten_abilities": len(forgotten),
            "health_score": max(0, 100 - len(missing) * 3 - len(forgotten) * 5),
            "warnings": (
                ([f"{i.name}长期未出现" for i in missing[:3]] if missing else [])
                + ([f"{i.name}能力被遗忘" for i in forgotten[:3]] if forgotten else [])
            ),
        }


# ══════════════════════════════════════════════════════
# 模块级便捷实例
# ══════════════════════════════════════════════════════

coherence_engine = CoherenceEngine()
