"""
昆仑创作引擎 — 债务追踪器
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .types import Debt, RiskLevel


class DebtTracker:
    """无聊债务追踪器

    追踪所有"承诺但未兑现"的债务:
      - 未回收伏笔
      - 未解决冲突
      - 未揭示谜题
      - 未完成角色弧
      - 未推进感情线
      - 契诃夫之枪 (埋了但没用的道具/设定)
    """

    # 债务老化系数 (拖欠越久越严重)
    @staticmethod
    def aging_multiplier(age_chapters: int) -> float:
        """债务老化乘数"""
        if age_chapters <= 3:
            return 1.0
        if age_chapters <= 10:
            return 1.0 + (age_chapters - 3) * 0.05  # 1.0~1.35
        if age_chapters <= 30:
            return 1.35 + (age_chapters - 10) * 0.03  # 1.35~1.95
        return 2.0  # 超过30章封顶

    @staticmethod
    def severity_by_age(age_chapters: int) -> RiskLevel:
        """按拖欠时间评估风险"""
        if age_chapters <= 5:
            return RiskLevel.SAFE
        if age_chapters <= 10:
            return RiskLevel.WATCH
        if age_chapters <= 20:
            return RiskLevel.WARN
        return RiskLevel.CRITICAL

    @classmethod
    def calculate_debt_score(cls, debts: list[Debt]) -> tuple[float, dict[str, Any]]:
        """计算债务健康度评分

        1.0 = 无债务，0.0 = 债务爆炸
        """
        if not debts:
            return 1.0, {"total_debts": 0}

        diag: dict[str, Any] = {
            "total_debts": len(debts),
            "by_type": defaultdict(int),
            "by_severity": defaultdict(int),
            "oldest_chapters": 0,
        }

        weighted_sum = 0.0
        for debt in debts:
            multiplier = cls.aging_multiplier(debt.age_chapters)
            severity_weight = {
                RiskLevel.SAFE: 0.05,
                RiskLevel.WATCH: 0.1,
                RiskLevel.WARN: 0.2,
                RiskLevel.CRITICAL: 0.4,
            }
            weighted_sum += severity_weight[debt.severity] * multiplier
            diag["by_type"][debt.debt_type.value] += 1
            diag["by_severity"][debt.severity.value] += 1
            diag["oldest_chapters"] = max(diag["oldest_chapters"], debt.age_chapters)

        # 评分 = 1 - 加权债务 / 最大容忍度
        max_tolerable = 3.0  # 超过3.0视为债务爆炸
        score = max(0.0, 1.0 - weighted_sum / max_tolerable)

        diag["by_type"] = dict(diag["by_type"])
        diag["by_severity"] = dict(diag["by_severity"])
        diag["weighted_sum"] = round(weighted_sum, 2)

        return round(score, 2), diag
