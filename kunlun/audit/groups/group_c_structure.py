"""
C组: 伏笔管理 (C1-C5) — 种伏、回收、逾期、优先级、信息边界
"""

from __future__ import annotations

from typing import Any

from .._base33 import DimResult


class Auditor33GroupC:
    """C组: 伏笔管理 mixin"""

    _truth_manager: Any | None = None

    def _check_C1_hook_planted(self, draft: str, _chapter: int, blueprint: dict) -> DimResult:
        fp = blueprint.get("foreshadowing", {})
        planted = fp.get("to_plant", [])
        if planted:
            missing = [p for p in planted if p not in draft]
            if missing:
                return DimResult(
                    "C1",
                    "伏笔种植",
                    40,
                    "FAIL",
                    f"蓝图要求种植{len(planted)}个伏笔,"
                    f"但{len(missing)}个未在正文中出现: {missing[:3]}",
                    "将伏笔自然融入叙事,可通过人物对话/环境描写/心理活动植入",
                    True,
                )
            return DimResult("C1", "伏笔种植", 90, "PASS", f"已成功种植全部{len(planted)}个伏笔")
        return DimResult("C1", "伏笔种植", 90, "PASS", "本章无需种植伏笔")

    def _check_C2_hook_revealed(self, draft: str, _chapter: int, blueprint: dict) -> DimResult:
        fp = blueprint.get("foreshadowing", {})
        revealed = fp.get("to_reveal", [])
        if revealed:
            revealed_in_text = [r for r in revealed if r in draft]
            missing = len(revealed) - len(revealed_in_text)
            if missing > 0:
                return DimResult(
                    "C2",
                    "伏笔回收",
                    50,
                    "WARN",
                    f"有{missing}/{len(revealed)}个伏笔未回收: "
                    f"{[r for r in revealed if r not in revealed_in_text][:3]}",
                    "在合适位置揭示伏笔,可通过角色对话/新发现/转折事件",
                    True,
                )
        return DimResult("C2", "伏笔回收", 90, "PASS", "伏笔回收正常")

    def _check_C3_overdue_hooks(self, _draft: str, chapter: int, _blueprint: dict) -> DimResult:
        if self._truth_manager:
            overdue = self._truth_manager.check_overdue_hooks(chapter)
            if overdue:
                names = [h.get("name", "?") for h in overdue[:5]]
                by_chapters = [h.get("overdue_by", 0) for h in overdue[:5]]
                detail_parts = [f"{n}(逾期{c}章)" for n, c in zip(names, by_chapters, strict=True)]
                return DimResult(
                    "C3",
                    "逾期伏笔",
                    30,
                    "FAIL",
                    f"发现{len(overdue)}个逾期伏笔: {', '.join(detail_parts)}",
                    "在接下来1-3章内安排伏笔回收,避免读者遗忘",
                    True,
                )
        return DimResult("C3", "逾期伏笔", 90, "PASS", "无逾期伏笔")

    def _check_C4_hook_priority(self, _draft: str, chapter: int, _blueprint: dict) -> DimResult:
        if self._truth_manager:
            data = self._truth_manager.get("pending_hooks")
            hooks = data.get("hooks", [])
            high_priority_overdue = [
                h
                for h in hooks
                if h.get("priority") == "high" and chapter > h.get("expected_reveal_chapter", 0)
            ]
            if high_priority_overdue:
                return DimResult(
                    "C4",
                    "伏笔优先级",
                    40,
                    "WARN",
                    f"{len(high_priority_overdue)}个高优先级伏笔逾期未处理",
                    "优先回收高优先级伏笔,避免影响主线节奏",
                    True,
                )
        return DimResult("C4", "伏笔优先级", 90, "PASS", "伏笔优先级管理正常")

    def _check_C5_info_boundary(self, draft: str, chapter: int, _blueprint: dict) -> DimResult:
        if self._truth_manager:
            char_matrix = self._truth_manager.get("character_matrix")
            info_transfers = [
                {
                    "from": inter.get("char_a", ""),
                    "to": inter.get("char_b", ""),
                    "info": inter.get("info_transferred", []),
                    "chapter": inter.get("chapter", 0),
                }
                for inter in char_matrix.get("interactions", [])
                if inter.get("info_transferred")
            ]

            for transfer in info_transfers:
                if transfer["chapter"] > chapter:
                    for info in transfer["info"]:
                        if info in draft and transfer["to"] in draft:
                            idx_info = draft.find(info)
                            idx_char = draft.find(transfer["to"])
                            if abs(idx_info - idx_char) < 100:
                                return DimResult(
                                    "C5",
                                    "信息边界",
                                    25,
                                    "FAIL",
                                    f"{transfer['to']}在第{chapter}章知晓了"
                                    f"来自第{transfer['chapter']}章才传递的信息",
                                    "删除角色不该知晓的信息,或调整信息传递时序",
                                    True,
                                )

        return DimResult("C5", "信息边界", 85, "PASS", "信息边界管控正常")
