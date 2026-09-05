"""
G8: 战斗场景节奏

检测战斗场景段落的节奏变化是否合理。
"""

from __future__ import annotations

import math

from kunlun.audit.gates._base import GateLevel, GateResult


class GateG8BattleRhythm:
    """G8: 战斗场景节奏"""

    BATTLE_KEYWORDS = [
        "剑",
        "刀",
        "枪",
        "拳",
        "掌",
        "腿",
        "招",
        "式",
        "攻",
        "防",
        "闪",
        "躲",
        "避",
        "格",
        "挡",
        "击",
        "打",
        "杀",
        "斩",
        "劈",
        "刺",
        "挑",
        "扫",
        "震",
        "爆",
        "轰",
        "炸",
        "裂",
        "碎",
    ]

    def run(self, draft: str) -> GateResult:
        paragraphs = draft.split("\n\n")
        battle_para_count = sum(
            1 for p in paragraphs if sum(1 for kw in self.BATTLE_KEYWORDS if kw in p) >= 3
        )
        has_battle = battle_para_count >= 2
        if not has_battle:
            return GateResult(
                gate_id="G8",
                level=GateLevel.PASS,
                score=0.8,
                detail="无战斗关键词，跳过节奏检测",
            )

        battle_paragraphs = [
            para for para in paragraphs if any(kw in para for kw in self.BATTLE_KEYWORDS)
        ]

        if not battle_paragraphs:
            return GateResult(
                gate_id="G8",
                level=GateLevel.PASS,
                score=0.7,
                detail="有战斗关键词但未形成段落",
            )

        para_lengths = [len(p) for p in battle_paragraphs]
        if len(para_lengths) < 2:
            return GateResult(
                gate_id="G8",
                level=GateLevel.PASS,
                score=0.7,
                detail="战斗段落过少，无法分析节奏",
            )

        mean = sum(para_lengths) / len(para_lengths)
        if mean == 0:
            cv = 0.0
        else:
            variance = sum((x - mean) ** 2 for x in para_lengths) / len(para_lengths)
            cv = math.sqrt(variance) / mean

        if cv < 0.2:
            level = GateLevel.WARN
            score = 0.5
            detail = f"战斗段落长度过于均匀 (CV={cv:.2f})，缺乏节奏变化"
        elif cv > 0.8:
            level = GateLevel.WARN
            score = 0.5
            detail = f"战斗段落长度差异过大 (CV={cv:.2f})，节奏可能失衡"
        else:
            level = GateLevel.PASS
            score = 0.9 - abs(cv - 0.5) * 0.5
            detail = f"战斗段落节奏正常 (CV={cv:.2f})"

        return GateResult(
            gate_id="G8",
            level=level,
            score=score,
            detail=detail,
            data={"battle_paragraphs": len(battle_paragraphs), "cv": cv, "lengths": para_lengths},
        )
