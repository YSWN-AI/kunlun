"""
pleasure 爽点引擎 — 疲劳度追踪器 & 爽点疲劳检测器
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from kunlun.pleasure.types import (
    PLEASURE_TYPE_CONFIGS,
    FatigueLevel,
    PleasureEvent,
    PleasureType,
    TypeFatigue,
    get_pleasure_config,
)

# ============================================================================
# 疲劳度追踪器
# ============================================================================


class FatigueTracker:
    """爽点类型疲劳度追踪"""

    # 疲劳阈值
    CONSECUTIVE_THRESHOLD = 3  # 连续出现≥3次开始疲劳
    INTERVAL_THRESHOLD = 500  # 间隔<500字视为连续
    DECAY_PER_CONSECUTIVE = 0.15  # 每次连续衰减15%

    def __init__(self):
        self._type_history: dict[PleasureType, list[PleasureEvent]] = defaultdict(list)

    def feed_events(self, events: list[PleasureEvent]) -> dict[str, TypeFatigue]:
        """喂入爽点事件，返回各类疲劳度"""
        for e in events:
            self._type_history[e.event_type].append(e)

        fatigue_map: dict[str, TypeFatigue] = {}
        for ptype in PleasureType:
            history = self._type_history.get(ptype, [])
            tf = TypeFatigue(event_type=ptype, total_occurrences=len(history))

            if len(history) >= 2:
                # 最近间隔
                tf.recent_interval = history[-1].position - history[-2].position

                # 连续出现次数
                consecutive = 1
                for i in range(len(history) - 1, 0, -1):
                    interval = history[i].position - history[i - 1].position
                    if interval < self.INTERVAL_THRESHOLD:
                        consecutive += 1
                    else:
                        break
                tf.consecutive_count = consecutive

                # 疲劳度判定
                if consecutive >= 5:
                    tf.fatigue_level = FatigueLevel.EXHAUSTED
                    tf.decay_factor = max(0.2, 1.0 - self.DECAY_PER_CONSECUTIVE * consecutive)
                elif consecutive >= self.CONSECUTIVE_THRESHOLD:
                    tf.fatigue_level = FatigueLevel.TIRING
                    tf.decay_factor = max(0.5, 1.0 - self.DECAY_PER_CONSECUTIVE * consecutive)
                elif tf.recent_interval < self.INTERVAL_THRESHOLD:
                    tf.fatigue_level = FatigueLevel.NORMAL
                else:
                    tf.fatigue_level = FatigueLevel.FRESH
            else:
                tf.fatigue_level = FatigueLevel.FRESH

            fatigue_map[ptype.value] = tf

        return fatigue_map

    def reset(self) -> None:
        """重置疲劳度追踪"""
        self._type_history.clear()


# ============================================================================
# 爽点疲劳检测器 — 追踪模式重复并建议多样性
# ============================================================================


class PleasureFatigueDetector:
    """爽点疲劳检测器 — 追踪模式重复并建议多样性

    检测维度:
      1. 单一类型连续重复 — 同类爽点连续出现≥N次
      2. 固定模式 — ABC-ABC 三段式完全重复
      3. 宏观节奏 — 爽点密度趋势是否单调
      4. 类型分布 — 距上次同类爽点出现的间隔是否过短
    """

    MAX_CONSECUTIVE_SAME = 3  # 同类型最大连续次数（超过则警告）
    PATTERN_WINDOW = 6  # 模式检测窗口大小
    DENSITY_TREND_WINDOW = 5  # 密度趋势检测窗口

    def __init__(self):
        self._history: list[PleasureType] = []

    def feed(self, events: list[PleasureEvent]) -> dict[str, Any]:
        """喂入新事件并返回疲劳检测报告"""
        new_types = [e.event_type for e in events]
        self._history.extend(new_types)

        report: dict[str, Any] = {
            "fatigue_detected": False,
            "severity": "low",
            "warnings": [],
            "suggestions": [],
            "patterns_detected": [],
        }

        if len(self._history) < 3:
            return report

        consecutive = self._detect_consecutive_same()
        if consecutive:
            report["fatigue_detected"] = True
            report["warnings"].append(consecutive)
            report["suggestions"].append(
                f"'{consecutive['type_name']}'类爽点已连续出现{consecutive['count']}次，"
                f"建议穿插其他类型（如打脸→升级→奇遇）交替使用"
            )

        patterns = self._detect_fixed_patterns()
        if patterns:
            report["patterns_detected"] = patterns
            report["fatigue_detected"] = True
            report["warnings"].append(
                f"检测到{len(patterns)}个固定爽点模式排列，读者可能产生预期疲劳"
            )
            report["suggestions"].append("建议打乱爽点出现顺序，增加不可预测性")

        density_trend = self._detect_density_monotony()
        if density_trend:
            report["fatigue_detected"] = True
            report["warnings"].append(density_trend)
            report["suggestions"].append(
                "爽点密度持续单调变化，建议制造波浪式节奏（如松→紧→松→紧）"
            )

        type_gaps = self._detect_type_gaps()
        if type_gaps:
            report["warnings"].extend(type_gaps)
            report["suggestions"].append("部分爽点类型间隔过近（<1000字），建议拉大间距避免麻木")

        if report["fatigue_detected"]:
            report["severity"] = self._assess_severity(report)

        return report

    def _detect_consecutive_same(self) -> dict[str, Any] | None:
        """检测单一类型连续出现"""
        if not self._history:
            return None
        current = self._history[-1]
        count = 0
        for t in reversed(self._history):
            if t == current:
                count += 1
            else:
                break
        if count >= self.MAX_CONSECUTIVE_SAME:
            config = get_pleasure_config(current)
            return {
                "type_name": config.name_cn,
                "type_value": current.value,
                "count": count,
                "fatigue_decay": config.fatigue_decay,
            }
        return None

    def _detect_fixed_patterns(self) -> list[str]:
        """检测固定模式重复"""
        if len(self._history) < self.PATTERN_WINDOW * 2:
            return []
        patterns: list[str] = []
        recent = [t.value for t in self._history[-self.PATTERN_WINDOW :]]
        older = [t.value for t in self._history[-self.PATTERN_WINDOW * 2 : -self.PATTERN_WINDOW]]
        if recent == older:
            patterns.append("→".join(recent[:3]) + "...")
        mid = self.PATTERN_WINDOW // 2
        recent_mid = [t.value for t in self._history[-mid:]]
        older_mid = [t.value for t in self._history[-mid * 2 : -mid]]
        if recent_mid == older_mid:
            patterns.append("→".join(recent_mid) + "（中段重复）")
        return patterns

    def _detect_density_monotony(self) -> str | None:
        """检测密度单调趋势"""
        if len(self._history) < self.DENSITY_TREND_WINDOW * 2:
            return None
        all_types_count = len(set(self._history))
        if all_types_count <= 2:
            return f"爽点类型极度单一（近{len(self._history)}个爽点仅{all_types_count}种类型）"
        return None

    def _detect_type_gaps(self) -> list[str]:
        """检测同类型间隔过短"""
        warnings: list[str] = []
        type_positions: dict[PleasureType, int] = {}
        for i, t in enumerate(self._history[-20:]):
            if t in type_positions:
                gap = i - type_positions[t]
                config = get_pleasure_config(t)
                if gap < 3 and config.min_interval < 1000:
                    warnings.append(f"'{config.name_cn}'类爽点间隔过近（{gap}个爽点内重复）")
            type_positions[t] = i
        return warnings

    def _assess_severity(self, report: dict[str, Any]) -> str:
        """评估严重程度"""
        warning_count = len(report["warnings"])
        pattern_count = len(report.get("patterns_detected", []))
        if warning_count >= 3 or pattern_count >= 2:
            return "high"
        if warning_count >= 2 or pattern_count >= 1:
            return "medium"
        return "low"

    def get_variety_suggestions(self, current_genre: str = "") -> list[str]:
        """根据题材推荐爽点类型轮换方案"""
        suggestions: list[str] = []
        matched = [
            pt
            for pt, cfg in PLEASURE_TYPE_CONFIGS.items()
            if not current_genre or any(g in current_genre for g in cfg.suitable_genres)
        ]
        if len(matched) >= 3:
            top3 = sorted(
                matched, key=lambda p: PLEASURE_TYPE_CONFIGS[p].intensity_base, reverse=True
            )[:3]
            names = [PLEASURE_TYPE_CONFIGS[p].name_cn for p in top3]
            suggestions.append(f"推荐轮换方案: {' → '.join(names)}")
        remaining = (
            [p for p in matched if p not in self._history[-6:]] if self._history else matched
        )
        if remaining:
            fresh = sorted(
                remaining, key=lambda p: PLEASURE_TYPE_CONFIGS[p].intensity_base, reverse=True
            )[:2]
            names = [PLEASURE_TYPE_CONFIGS[p].name_cn for p in fresh]
            suggestions.append(f"近期未使用的爽点: {', '.join(names)}，可穿插使用增加新鲜感")
        return suggestions

    def reset(self) -> None:
        """重置历史"""
        self._history.clear()
