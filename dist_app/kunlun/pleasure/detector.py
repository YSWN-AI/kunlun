"""
pleasure 爽点引擎 — 爽点识别器
"""

from __future__ import annotations

import re

from kunlun.pleasure.types import PLEASURE_KEYWORDS, PleasureEvent


class PleasureDetector:
    """爽点识别器"""

    @classmethod
    def detect_events(cls, text: str, _chapter_id: str = "") -> list[PleasureEvent]:
        """从文本中检测所有爽点事件"""
        events: list[PleasureEvent] = []

        for ptype, level_dict in PLEASURE_KEYWORDS.items():
            for level, keywords in level_dict.items():
                weight = 1.0 if level == "high" else 0.6
                for kw in keywords:
                    for match in re.finditer(re.escape(kw), text):
                        start = match.start()
                        # 上下文片段
                        ctx_start = max(0, start - 20)
                        ctx_end = min(len(text), match.end() + 20)
                        snippet = text[ctx_start:ctx_end].replace("\n", " ")

                        # 找到所在段落索引
                        para_idx = text[:start].count("\n")

                        events.append(
                            PleasureEvent(
                                event_type=ptype,
                                position=start,
                                intensity=weight,
                                keywords_matched=[kw],
                                context_snippet=snippet,
                                paragraph_index=para_idx,
                            )
                        )

        # 去重：同一位置只保留最高强度的
        events.sort(key=lambda e: (e.position, -e.intensity))
        deduped: list[PleasureEvent] = []
        last_pos = -100
        for e in events:
            if e.position - last_pos > 10:  # 10字内视为同一事件
                deduped.append(e)
                last_pos = e.position

        return deduped
