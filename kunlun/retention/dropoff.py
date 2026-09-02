"""
昆仑创作引擎 — 章节级读者流失预测器
"""

from __future__ import annotations

from typing import Any

from .types import DropOffPrediction, RiskLevel


class DropOffPredictor:
    """章节级读者流失预测器

    基于竞品研究的多因素流失模型:
      - 钩子强度不足 (结尾钩子<0.3 = 高流失风险)
      - 章节过长/过短 (超出平台最佳字数范围)
      - 节奏突变 (与前章节奏差异过大)
      - 疲劳积累 (连续N章爽点密度下降)
      - 债务爆炸 (未回收伏笔>15个)
    """

    OPTIMAL_WORD_RANGES: dict[str, tuple[int, int]] = {
        "fanqie": (1500, 3000),
        "qidian": (2000, 5000),
        "qimao": (1500, 3000),
        "feilu": (1000, 2500),
        "jjwxc": (2500, 6000),
        "default": (2000, 4000),
    }

    def __init__(self):
        self._chapter_stats: list[dict[str, Any]] = []

    def predict(
        self,
        chapter_number: int,
        hook_score: float,
        pleasure_score: float,
        word_count: int,
        active_debt_count: int,
        prev_chapter_hook_score: float = 0.0,
        _prev_chapter_pleasure_score: float = 0.0,
        platform: str = "default",
    ) -> DropOffPrediction:
        """预测本章读者流失率

        Args:
            chapter_number: 章节号
            hook_score: 本章钩子评分
            pleasure_score: 本章爽点评分
            word_count: 本章字数
            active_debt_count: 当前活跃债务数
            prev_chapter_hook_score: 前章钩子评分
            prev_chapter_pleasure_score: 前章爽点评分
            platform: 平台
        """
        factors: list[str] = []
        base_dropoff = 0.15  # 基础流失率

        word_min, word_max = self.OPTIMAL_WORD_RANGES.get(platform, (2000, 4000))
        word_score = 1.0
        if word_count < word_min * 0.7:
            word_score = 0.4
            factors.append(f"章节过短({word_count}字 < {int(word_min * 0.7)}字)")
        elif word_count < word_min:
            word_score = 0.7
        elif word_count > word_max * 1.5:
            word_score = 0.5
            factors.append(f"章节过长({word_count}字 > {int(word_max * 1.5)}字)")
        elif word_count > word_max:
            word_score = 0.8

        hook_factor = 1.0 - hook_score
        if hook_score < 0.3:
            factors.append(f"钩子强度严重不足({hook_score:.2f})")
            hook_factor += 0.15
        elif hook_score < 0.5:
            factors.append(f"钩子强度偏低({hook_score:.2f})")

        pleasure_factor = 1.0 - pleasure_score
        if pleasure_score < 0.4:
            factors.append(f"爽点密度不足({pleasure_score:.2f})")
            pleasure_factor += 0.1

        debt_factor = min(active_debt_count * 0.01, 0.15)
        if active_debt_count > 10:
            factors.append(f"活跃债务过多({active_debt_count}个)")
        if active_debt_count > 15:
            debt_factor += 0.05

        prev_hook_drop = 0.0
        if prev_chapter_hook_score > 0 and hook_score < prev_chapter_hook_score * 0.5:
            drop = prev_chapter_hook_score - hook_score
            prev_hook_drop = min(drop * 0.2, 0.1)
            factors.append(f"钩子强度骤降(前章{prev_chapter_hook_score:.2f}→本章{hook_score:.2f})")

        fatigue_factor = 0.0
        if len(self._chapter_stats) >= 3:
            recent_pleasures = [s.get("pleasure_score", 0) for s in self._chapter_stats[-3:]]
            if len(recent_pleasures) == 3:
                if all(p < 0.5 for p in recent_pleasures):
                    fatigue_factor = 0.08
                    factors.append("连续3章爽点密度偏低")
                elif recent_pleasures[0] > recent_pleasures[1] > recent_pleasures[2]:
                    fatigue_factor = 0.04
                    factors.append("爽点密度持续下降")

        predicted = (
            base_dropoff
            + hook_factor * 0.25
            + pleasure_factor * 0.20
            + (1.0 - word_score) * 0.15
            + debt_factor
            + prev_hook_drop
            + fatigue_factor
        )
        predicted = min(max(predicted, 0.0), 1.0)

        risk = RiskLevel.SAFE
        if predicted > 0.50:
            risk = RiskLevel.CRITICAL
        elif predicted > 0.35:
            risk = RiskLevel.WARN
        elif predicted > 0.20:
            risk = RiskLevel.WATCH

        self._chapter_stats.append(
            {
                "chapter": chapter_number,
                "hook_score": hook_score,
                "pleasure_score": pleasure_score,
                "word_count": word_count,
                "predicted_dropoff": predicted,
            }
        )

        return DropOffPrediction(
            chapter_number=chapter_number,
            predicted_dropoff_rate=round(predicted, 3),
            risk_level=risk,
            contributing_factors=factors,
            hook_strength=round(hook_score, 2),
            word_count_score=round(word_score, 2),
            pace_score=round(1.0 - abs(prev_chapter_hook_score - hook_score) * 0.5, 2),
            fatigue_score=round(1.0 - fatigue_factor * 5, 2),
            cliff_strength=round(hook_score, 2),
        )

    def get_trend(self) -> dict[str, Any]:
        """获取流失趋势"""
        if not self._chapter_stats:
            return {"trend": "无数据", "avg_dropoff": 0.0}
        rates = [s["predicted_dropoff"] for s in self._chapter_stats]
        avg = sum(rates) / len(rates)
        if len(rates) >= 3:
            recent = rates[-3:]
            if all(r > 0.30 for r in recent):
                trend = "上升（危险）"
            elif recent[-1] > avg * 1.3:
                trend = "上升"
            elif recent[-1] < avg * 0.7:
                trend = "下降"
            else:
                trend = "稳定"
        else:
            trend = "数据不足"
        return {
            "trend": trend,
            "avg_dropoff": round(avg, 3),
            "history": [round(r, 3) for r in rates],
        }
