"""
昆仑创作引擎 — 微兑现追踪器
"""

from __future__ import annotations

import re
from typing import Any


class PayoffTracker:
    """微兑现追踪器 — 伏笔回收节奏控制

    核心原则:
      - 短伏笔(3章内) 回收率 > 80%
      - 中伏笔(10章内) 回收率 > 60%
      - 长伏笔(30章内) 需明确标注
      - 超过30章未回收 = 无聊债务
    """

    # 伏笔提示词 (检测文本中的伏笔埋设)
    FORESHADOW_INDICATORS = [
        r"(?:似乎|好像|隐约).{0,10}(?:感到|觉得|发现)",
        r"(?:不[知会料]).{0,10}(?:后来|以后|未来)",
        r"这.{0,5}(?:东西|事情|秘密).{0,5}(?:不简单|有蹊跷)",
        r"(?:隐约|隐隐).{0,5}(?:觉得|感到)",
        r"(?:眼角|余光).{0,10}(?:瞥见|看到)",
        r"(?:心中|脑海).{0,5}(?:闪过|浮现)",
        r"(?:如果|要是).{0,10}(?:真的|确实)",
        r"(?:谁也没有|没人).{0,10}(?:注意|发现)",
        r"后来.{0,10}(?:才知道|才明白)",
        r"(?:某个|某个角落).{0,10}(?:东西|人影)",
    ]

    # 兑现提示词 (检测伏笔回收)
    PAYOFF_INDICATORS = [
        r"原来[如这].{0,10}(?:就是|因为|如此)",
        r"终于[知明]白",
        r"难怪.{0,10}(?:会|能)",
        r"原来.{0,5}是.{0,10}(?:搞的鬼|做的|安排的)",
        r"一切都[说解]得通了",
        r"答案[终于揭]",
        r"(?:谜底|真相).{0,5}(?:揭晓|大白)",
    ]

    @classmethod
    def detect_new_foreshadows(cls, text: str, chapter: int) -> list[dict]:
        """检测新埋设的伏笔"""
        results: list[dict] = []
        for pattern in cls.FORESHADOW_INDICATORS:
            results.extend(
                {
                    "chapter": chapter,
                    "text": match.group()[:80],
                    "position": match.start(),
                }
                for match in re.finditer(pattern, text)
            )
        return results

    @classmethod
    def detect_payoffs(cls, text: str, chapter: int) -> list[dict]:
        """检测伏笔兑现"""
        results: list[dict] = []
        for pattern in cls.PAYOFF_INDICATORS:
            results.extend(
                {
                    "chapter": chapter,
                    "text": match.group()[:80],
                    "position": match.start(),
                }
                for match in re.finditer(pattern, text)
            )
        return results

    @classmethod
    def calculate_payoff_score(
        cls,
        active_foreshadows: list[dict],
        current_chapter: int,
    ) -> tuple[float, dict[str, Any]]:
        """计算微兑现评分

        Args:
            active_foreshadows: 活跃伏笔列表 (含埋设章节)
            current_chapter: 当前章节号
        """
        if not active_foreshadows:
            return 1.0, {"reason": "无活跃伏笔"}

        diag: dict[str, Any] = {
            "total_active": len(active_foreshadows),
        }

        # 按延迟分类
        short_term = [f for f in active_foreshadows if current_chapter - f["chapter"] <= 3]
        mid_term = [f for f in active_foreshadows if 3 < current_chapter - f["chapter"] <= 10]
        long_term = [f for f in active_foreshadows if 10 < current_chapter - f["chapter"] <= 30]
        overdue = [f for f in active_foreshadows if current_chapter - f["chapter"] > 30]

        diag["short_term"] = len(short_term)
        diag["mid_term"] = len(mid_term)
        diag["long_term"] = len(long_term)
        diag["overdue"] = len(overdue)

        # 评分: 逾期债务严重扣分
        if overdue:
            # 每个逾期伏笔扣0.1，最多扣0.5
            penalty = min(len(overdue) * 0.1, 0.5)
            score = 1.0 - penalty
        elif long_term:
            score = 0.7
        elif mid_term:
            score = 0.85
        else:
            score = 1.0

        # 总量惩罚 (活跃伏笔太多)
        if len(active_foreshadows) > 15:
            score = max(score - 0.2, 0.0)
        elif len(active_foreshadows) > 10:
            score = max(score - 0.1, 0.0)

        return round(score, 2), diag
