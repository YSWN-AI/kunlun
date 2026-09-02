"""
测试 — 追读力系统 (retention/)
"""
import pytest

pytestmark = pytest.mark.unit

from kunlun.retention.engine import (
    Debt,
    DebtType,
    DropOffPrediction,
    DropOffPredictor,
    HookDetector,
    HookResult,
    HookStrengthReport,
    HookStrengthScorer,
    HookType,
    PlatformAdapter,
    PleasureScorer,
    RetentionOptimizationPlan,
    RetentionOptimizer,
    RetentionPredictor,
    RetentionReport,
    RiskLevel,
    get_retention_predictor,
)

SAMPLE_TEXT = """
突然，林风感觉到一股强大的力量从体内涌出！
他突破了一直以来的瓶颈，实力暴涨！
"你敢！"一声冷喝响起。
原来他一直在隐藏实力...
这让所有人都震惊了。
明天，一切将改变。
"""


class TestDropOffPredictor:
    """测试流失预测器"""

    def test_creation(self):
        predictor = DropOffPredictor()
        assert predictor is not None

    def test_predict_basic(self):
        predictor = DropOffPredictor()
        result = predictor.predict(
            chapter_number=1,
            hook_score=0.7,
            pleasure_score=0.6,
            word_count=2500,
            active_debt_count=3,
            platform="fanqie",
        )
        assert isinstance(result, DropOffPrediction)
        assert 0.0 <= result.predicted_dropoff_rate <= 1.0
        assert isinstance(result.risk_level, RiskLevel)

    def test_predict_high_risk(self):
        predictor = DropOffPredictor()
        result = predictor.predict(
            chapter_number=1,
            hook_score=0.2,
            pleasure_score=0.3,
            word_count=500,
            active_debt_count=20,
            platform="fanqie",
        )
        assert result.predicted_dropoff_rate > 0.30
        assert result.risk_level in (RiskLevel.WARN, RiskLevel.CRITICAL)

    def test_predict_low_risk(self):
        predictor = DropOffPredictor()
        result = predictor.predict(
            chapter_number=1,
            hook_score=0.85,
            pleasure_score=0.8,
            word_count=2500,
            active_debt_count=0,
            platform="qidian",
        )
        assert result.predicted_dropoff_rate < 0.25

    def test_predict_hook_drop(self):
        predictor = DropOffPredictor()
        predictor.predict(chapter_number=1, hook_score=0.9, pleasure_score=0.7, word_count=2500, active_debt_count=0)
        result = predictor.predict(
            chapter_number=2,
            hook_score=0.3,
            pleasure_score=0.7,
            word_count=2500,
            active_debt_count=0,
            prev_chapter_hook_score=0.9,
        )
        assert result.predicted_dropoff_rate > 0.20

    def test_get_trend(self):
        predictor = DropOffPredictor()
        predictor.predict(chapter_number=1, hook_score=0.7, pleasure_score=0.6, word_count=2500, active_debt_count=0)
        predictor.predict(chapter_number=2, hook_score=0.5, pleasure_score=0.5, word_count=2500, active_debt_count=0)
        predictor.predict(chapter_number=3, hook_score=0.3, pleasure_score=0.4, word_count=2500, active_debt_count=0)
        trend = predictor.get_trend()
        assert "trend" in trend
        assert "avg_dropoff" in trend
        assert len(trend["history"]) >= 3


class TestHookStrengthScorer:
    """测试钩子强度评分器"""

    def test_score_empty(self):
        report = HookStrengthScorer.score([])
        assert isinstance(report, HookStrengthReport)
        assert report.overall_score == 0.0

    def test_score_with_hooks(self):
        hooks = [
            HookResult(hook_type=HookType.CLIFFHANGER, position="closing", paragraph_index=0, strength=0.9),
            HookResult(hook_type=HookType.MYSTERY, position="opening", paragraph_index=0, strength=0.7),
            HookResult(hook_type=HookType.EMOTIONAL, position="closing", paragraph_index=1, strength=0.8),
        ]
        report = HookStrengthScorer.score(hooks)
        assert report.overall_score > 0.0
        assert report.cliffhanger_present is True
        assert report.emotional_peak_present is True
        assert report.mystery_hook_present is True

    def test_score_weak_closing(self):
        hooks = [
            HookResult(hook_type=HookType.CLIFFHANGER, position="closing", paragraph_index=0, strength=0.2),
            HookResult(hook_type=HookType.CONFRONTATION, position="opening", paragraph_index=0, strength=0.3),
        ]
        report = HookStrengthScorer.score(hooks)
        assert report.closing_hook_score < 0.4
        assert len(report.weak_spots) > 0

    def test_score_diverse(self):
        hooks = [
            HookResult(hook_type=HookType.CLIFFHANGER, position="closing", paragraph_index=0, strength=0.9),
            HookResult(hook_type=HookType.MYSTERY, position="opening", paragraph_index=0, strength=0.7),
            HookResult(hook_type=HookType.REVERSAL, position="closing", paragraph_index=1, strength=0.8),
            HookResult(hook_type=HookType.PROMISE, position="mid_chapter", paragraph_index=5, strength=0.6),
        ]
        report = HookStrengthScorer.score(hooks)
        assert "钩子类型丰富" in report.strengths


class TestRetentionOptimizer:
    """测试留存优化器"""

    def test_generate_plan(self):
        report = RetentionReport(
            chapter_number=1,
            overall_score=0.45,
            hook_score=0.3,
            pleasure_score=0.4,
            payoff_score=0.5,
            debt_score=0.6,
        )
        dropoff = DropOffPrediction(
            chapter_number=1,
            predicted_dropoff_rate=0.35,
            risk_level=RiskLevel.WARN,
            contributing_factors=["钩子强度不足"],
        )
        plan = RetentionOptimizer.generate_plan(
            chapter_number=1,
            retention_report=report,
            dropoff=dropoff,
            target_platform="fanqie",
        )
        assert isinstance(plan, RetentionOptimizationPlan)
        assert len(plan.priority_actions) > 0
        assert len(plan.quick_wins) > 0
        assert "fanqie" in plan.platform_specific_tips or len(plan.platform_specific_tips) > 0

    def test_generate_plan_good(self):
        report = RetentionReport(
            chapter_number=1,
            overall_score=0.85,
            hook_score=0.8,
            pleasure_score=0.9,
            payoff_score=0.8,
            debt_score=0.9,
        )
        plan = RetentionOptimizer.generate_plan(
            chapter_number=1,
            retention_report=report,
            target_platform="qidian",
        )
        assert plan.overall_retention_score == 0.85

    def test_generate_plan_structural(self):
        report = RetentionReport(
            chapter_number=1,
            overall_score=0.50,
            hook_score=0.4,
            pleasure_score=0.4,
            payoff_score=0.6,
            debt_score=0.3,
        )
        plan = RetentionOptimizer.generate_plan(
            chapter_number=1,
            retention_report=report,
            target_platform="qimao",
        )
        assert len(plan.structural_changes) > 0


class TestRetentionPredictor:
    """测试追读力预测器"""

    def test_factory(self):
        p1 = get_retention_predictor("book_x")
        p2 = get_retention_predictor("book_x")
        assert p1 is p2

    def test_analyze(self):
        predictor = RetentionPredictor(book_id="test")
        report = predictor.analyze(
            text=SAMPLE_TEXT * 10,
            chapter_number=1,
            is_first_three=True,
        )
        assert isinstance(report, RetentionReport)
        assert report.chapter_number == 1
        assert 0.0 <= report.overall_score <= 1.0
        assert 0.0 <= report.hook_score <= 1.0
        assert 0.0 <= report.pleasure_score <= 1.0
        assert len(report.platform_scores) > 0

    def test_analyze_with_platform(self):
        predictor = RetentionPredictor(book_id="test")
        report = predictor.analyze(
            text=SAMPLE_TEXT * 10,
            chapter_number=5,
            platform="fanqie",
        )
        assert "fanqie" in report.platform_scores

    def test_analyze_climax(self):
        predictor = RetentionPredictor(book_id="test")
        report = predictor.analyze(
            text=SAMPLE_TEXT * 20,
            chapter_number=50,
            is_climax=True,
        )
        assert report.overall_score >= 0  # 高潮章评分有效

    def test_analyze_empty(self):
        predictor = RetentionPredictor(book_id="test")
        report = predictor.analyze(text="", chapter_number=1)
        assert report.overall_score == 0.0 or report.overall_score >= 0.0  # 空文本不会崩溃

    def test_analyze_with_debts(self):
        predictor = RetentionPredictor(book_id="test")
        debts = [
            Debt(debt_type=DebtType.FORESHADOW, description="伏笔A", created_chapter=1,
                 age_chapters=5, severity=RiskLevel.WATCH, should_resolve_by=10),
        ]
        report = predictor.analyze(
            text=SAMPLE_TEXT * 5,
            chapter_number=10,
            active_debts=debts,
        )
        assert report.debt_score < 1.0  # 有债务则扣分


def test_hook_detector():
    hooks = HookDetector.detect_hooks(SAMPLE_TEXT)
    assert len(hooks) > 0

    score = HookDetector.calculate_hook_score(hooks, is_first_three_chapters=True)
    assert 0.0 <= score <= 1.0

    weak = HookDetector.detect_weak_closing(SAMPLE_TEXT)
    assert isinstance(weak, list)


def test_pleasure_scorer():
    points = PleasureScorer.detect_pleasure_points(SAMPLE_TEXT)
    assert isinstance(points, list)

    score, diag = PleasureScorer.calculate_pleasure_score(
        points, word_count=len(SAMPLE_TEXT), total_paragraphs=5
    )
    assert 0.0 <= score <= 1.0
    assert "density_per_1k" in diag


def test_platform_adapter():
    ps, _sug = PlatformAdapter.score_for_platform(
        "fanqie", hook_score=0.8, pleasure_score=0.7,
        payoff_score=0.6, debt_score=0.9,
    )
    assert 0.0 <= ps <= 1.0
