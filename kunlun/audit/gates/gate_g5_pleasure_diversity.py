"""
G5: 爽点类型多样性

检测爽点类型是否过于集中。
"""

from __future__ import annotations

from loguru import logger

from kunlun.audit.gates._base import GateLevel, GateResult
from kunlun.audit.gates.gate_g4_pleasure_interval import GateG4PleasureGap
from kunlun.config import settings


class GateG5PleasureDiversity:
    """G5: 爽点类型多样性"""

    PLEASURE_TYPES = GateG4PleasureGap.PLEASURE_KEYWORDS.keys()

    def run(self, draft: str) -> GateResult:
        try:
            from kunlun.audit.jieba_analyzer import match_keywords

            matched = match_keywords(draft, GateG4PleasureGap.PLEASURE_KEYWORDS)
            type_counts = {ptype: matched.get(ptype, 0) for ptype in self.PLEASURE_TYPES}
        except Exception as e:
            logger.debug(f"G5 jieba匹配失败，回退到简单计次: {e}")
            type_counts = dict.fromkeys(self.PLEASURE_TYPES, 0)
            for ptype, keywords in GateG4PleasureGap.PLEASURE_KEYWORDS.items():
                for kw in keywords:
                    type_counts[ptype] += draft.count(kw)

        active_types = [ptype for ptype, count in type_counts.items() if count > 0]
        if not active_types:
            return GateResult(
                gate_id="G5",
                level=GateLevel.PASS,
                score=0.7,
                detail="未检测到爽点关键词，跳过多样性检查",
            )

        total_hits = sum(type_counts.values())
        max_type = max(type_counts.items(), key=lambda x: x[1])
        max_ratio = max_type[1] / total_hits if total_hits > 0 else 0

        max_streak = max(settings.audit_max_same_pleasure_type_streak, 1)
        fail_threshold = max(0.5, 1.0 / max_streak)
        if max_ratio > fail_threshold and total_hits >= 3:
            level = GateLevel.FAIL
            score = 0.3
        elif max_ratio > fail_threshold * 0.6:
            level = GateLevel.WARN
            score = 0.6
        else:
            level = GateLevel.PASS
            score = 0.9 - max_ratio

        detail = (
            f"爽点类型: {len(active_types)}种, "
            f"最多: {max_type[0]}({max_type[1]}次, {max_ratio:.1%})"
        )
        return GateResult(
            gate_id="G5",
            level=level,
            score=score,
            detail=detail,
            data={"type_counts": type_counts, "active_types": active_types, "max_ratio": max_ratio},
        )
