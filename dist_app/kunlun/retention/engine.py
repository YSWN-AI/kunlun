"""
昆仑创作引擎 — 追读力系统 (Retention Engine) — 主引擎

灵感来源: webnovel-writer 追读力系统 + InkOS 37维审计
对标: 番茄/起点/七猫 平台的追读率优化最佳实践

核心概念:
  追读力 = 读者"忍不住看下一章"的驱动力
  = Hook强度 × 爽点密度 × 微兑现频率 × 悬念张力 − 无聊债务

四大子系统:
  1. Hook检测 — 章节开头/结尾钩子强度
  2. 爽点评分 — 爽点间隔/密度/多样性/类型疲劳
  3. 微兑现 — 伏笔回收/承诺兑现的节奏控制
  4. 债务追踪 — 未兑现的伏笔/冲突/悬念 (无聊债务)

输出:
  RetentionReport { hook_score, pleasure_score, payoff_score, debt_score, overall }
  平台适配: 番茄(黄金三章)、起点(慢热长线)、七猫(快节奏)

设计原则:
  - 纯规则计算，零 LLM 成本
  - 所有评分 0.0~1.0
  - 独立可插拔，每项可单独禁用
"""

from __future__ import annotations

# Re-export submodule classes for backward compatibility
from .debt import DebtTracker
from .dropoff import DropOffPredictor
from .features import ChapterFeatureExtractor
from .hooks import (
    HookDetector,
    HookStrengthScorer,
)
from .optimizer import RetentionOptimizer
from .payoff import PayoffTracker
from .platform import PlatformAdapter
from .pleasure_scorer import PleasureScorer
from .types import (
    Debt,
    DebtType,
    DropOffPrediction,
    HookResult,
    HookStrengthReport,
    HookType,
    RetentionOptimizationPlan,
    RetentionReport,
    RiskLevel,
)

__all__ = [
    "ChapterFeatureExtractor",
    "Debt",
    "DebtTracker",
    "DebtType",
    "DropOffPrediction",
    "DropOffPredictor",
    "HookDetector",
    "HookResult",
    "HookStrengthReport",
    "HookStrengthScorer",
    "HookType",
    "PayoffTracker",
    "PlatformAdapter",
    "PleasureScorer",
    "RetentionOptimizationPlan",
    "RetentionOptimizer",
    "RetentionReport",
    "RiskLevel",
]

# ─── 追读力主引擎 ────────────────────────────────────


class RetentionPredictor:
    """追读力预测器 — 综合四大子系统

    用法:
        predictor = RetentionPredictor(book_id="my_book")
        report = predictor.analyze(
            text="章节正文...",
            chapter_number=42,
            active_foreshadows=[...],
            is_first_three=False,
            is_climax=False,
        )
    """

    def __init__(self, book_id: str = ""):
        self.book_id = book_id
        self._debt_history: list[float] = []  # 最近N章的债务评分
        self._hook_history: list[float] = []
        self._pleasure_history: list[float] = []

    def analyze(  # noqa: PLR0912
        self,
        text: str,
        chapter_number: int,
        active_foreshadows: list[dict] | None = None,
        active_debts: list[Debt] | None = None,
        is_first_three: bool = False,
        is_climax: bool = False,
        platform: str = "",
    ) -> RetentionReport:
        """执行完整的追读力分析

        Args:
            text: 章节正文
            chapter_number: 章节号
            active_foreshadows: 活跃伏笔列表
            active_debts: 当前活跃债务列表
            is_first_three: 是否前3章 (黄金三章)
            is_climax: 是否高潮章节
            platform: 目标平台 (fanqie/qidian/qimao/feilu/jjwxc)
        """
        if active_foreshadows is None:
            active_foreshadows = []
        if active_debts is None:
            active_debts = []

        # 1. 提取章节特征
        features = ChapterFeatureExtractor.extract(text, chapter_number)

        # 2. 钩子检测
        hooks = HookDetector.detect_hooks(text)
        hook_score = HookDetector.calculate_hook_score(hooks, is_first_three)
        weak_closings = HookDetector.detect_weak_closing(text)

        # 3. 爽点评分
        pleasure_points = PleasureScorer.detect_pleasure_points(text)
        pleasure_score, _pleasure_diag = PleasureScorer.calculate_pleasure_score(
            pleasure_points, features.word_count, features.paragraph_count, is_climax
        )

        # 4. 微兑现评分
        payoff_score, _payoff_diag = PayoffTracker.calculate_payoff_score(
            active_foreshadows, chapter_number
        )

        # 5. 债务评分
        debt_score, debt_diag = DebtTracker.calculate_debt_score(active_debts)

        # 6. 综合评分 (权重动态调整)
        if is_first_three:
            weights = {"hook": 0.35, "pleasure": 0.30, "payoff": 0.15, "debt": 0.20}
        elif is_climax:
            weights = {"hook": 0.20, "pleasure": 0.45, "payoff": 0.20, "debt": 0.15}
        else:
            weights = {"hook": 0.25, "pleasure": 0.35, "payoff": 0.20, "debt": 0.20}

        overall = (
            hook_score * weights["hook"]
            + pleasure_score * weights["pleasure"]
            + payoff_score * weights["payoff"]
            + debt_score * weights["debt"]
        )

        # 7. 风险评估
        risk_level = RiskLevel.SAFE
        risk_reasons: list[str] = []

        if overall < 0.4:
            risk_level = RiskLevel.CRITICAL
            risk_reasons.append("综合追读力极低 (<0.4)")
        elif overall < 0.55:
            risk_level = RiskLevel.WARN
            risk_reasons.append("综合追读力偏低 (<0.55)")
        elif overall < 0.7:
            risk_level = RiskLevel.WATCH
            risk_reasons.append("综合追读力一般 (<0.7)")

        if hook_score < 0.3:
            risk_reasons.append(f"钩子强度不足 ({hook_score})")
        if pleasure_score < 0.4:
            risk_reasons.append(f"爽点密度不足 ({pleasure_score})")
        if debt_score < 0.5:
            risk_reasons.append(f"债务积累严重 ({debt_score})")
        if weak_closings:
            risk_reasons.append(f"章节结尾弱: {', '.join(weak_closings[:2])}")

        # 8. 平台适配
        platform_scores: dict[str, float] = {}
        all_suggestions: list[str] = list(risk_reasons)

        if platform:
            ps, psug = PlatformAdapter.score_for_platform(
                platform, hook_score, pleasure_score, payoff_score, debt_score, features
            )
            platform_scores[platform] = ps
            all_suggestions.extend(psug)
        else:
            # 默认计算所有平台
            for p in PlatformAdapter.PLATFORM_WEIGHTS:
                ps, psug = PlatformAdapter.score_for_platform(
                    p, hook_score, pleasure_score, payoff_score, debt_score, features
                )
                platform_scores[p] = ps

        # 9. 生成建议
        suggestions = list(risk_reasons)
        if hook_score < 0.5:
            suggestions.append("建议加强章节结尾钩子（悬念/反转/预告）")
        if pleasure_score < 0.5:
            suggestions.append("建议增加爽点密度，目标每千字2-3个爽点")
        if features.dialogue_ratio > 0.6:
            suggestions.append("对话比例过高，建议增加动作和描述")
        if features.dialogue_ratio < 0.15:
            suggestions.append("对话比例过低，建议增加人物互动")
        if debt_diag.get("overdue", 0) > 0:
            suggestions.append(f"有{debt_diag['overdue']}个逾期伏笔(>30章)，建议尽快回收")

        # 10. 更新历史
        self._hook_history.append(hook_score)
        self._pleasure_history.append(pleasure_score)
        self._debt_history.append(debt_score)
        if len(self._debt_history) > 10:
            self._debt_history = self._debt_history[-10:]
            self._hook_history = self._hook_history[-10:]
            self._pleasure_history = self._pleasure_history[-10:]

        return RetentionReport(
            chapter_number=chapter_number,
            overall_score=round(overall, 2),
            hook_score=hook_score,
            pleasure_score=pleasure_score,
            payoff_score=payoff_score,
            debt_score=debt_score,
            hooks=hooks,
            pleasure_points=pleasure_points,
            active_debts=active_debts,
            features=features,
            risk_level=risk_level,
            risk_reasons=risk_reasons,
            platform_scores=platform_scores,
            suggestions=suggestions,
            debt_trend=list(self._debt_history),
        )


# ─── 工厂函数 ────────────────────────────────────────

_retention_predictors: dict[str, RetentionPredictor] = {}


def get_retention_predictor(book_id: str = "") -> RetentionPredictor:
    """获取或创建追读力预测器实例"""
    if book_id not in _retention_predictors:
        _retention_predictors[book_id] = RetentionPredictor(book_id)
    return _retention_predictors[book_id]
