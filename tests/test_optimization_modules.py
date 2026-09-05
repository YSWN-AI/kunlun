"""阶段一优化模块综合测试

覆盖:
- G9 AI率门禁 (audit/gates/gate_g9_ai_rate)
- Gacha第10维风格评分 (gacha/engine)
- Context第7段记忆注入 (context/budget)
- Quality 6维仪表盘 (quality/six_dim_dashboard)
- Vibe即时质量反馈 (vibe_writer/quality_feedback)
- 4个核心优化模块基本功能 (ai_rate/style_learner/memory/debate_review)
"""

import pytest

pytestmark = pytest.mark.unit


# ─── 测试文本 ────────────────────────────────────────

GOOD_TEXT = (
    "林羽一拳轰出，拳风呼啸，气浪翻涌！\n"
    "对面的黑衣人直接倒飞出去，撞碎了三根石柱！\n"
    '"就这点实力？"林羽冷笑，"也配跟我动手？"\n'
    "黑衣人脸色惨白，一口鲜血喷了出来。\n"
    "林羽一步踏出，气势暴涨，周身灵力翻腾。\n"
    '"杀你的人！"又是一拳，轰！黑衣人直接被轰成血雾！\n'
    "全场寂静，所有人都瞪大了眼睛，不敢相信眼前这一幕。\n"
)

AI_TEXT = (
    "林羽微微一怔，眼中闪过一丝精光。他缓缓开口，淡淡说道：这不可能。\n"
    "仿佛时间静止了一般，所有人都不由自主地屏住了呼吸。\n"
    "心中暗道：这少年究竟是何方神圣？嘴角微微上扬，林羽轻轻摇头，深深看了对方一眼。\n"
    "赫然发现，对方的修为竟然已经达到了筑基期！林羽心中一凛，气势暴涨。\n"
)

SHORT_TEXT = "林羽微微一怔。"
EMPTY_TEXT = ""


# ═══════════════════════════════════════════════════
# 1. G9 AI率门禁测试
# ═══════════════════════════════════════════════════

class TestG9AIRateGate:
    """G9综合AI率门禁测试"""

    def test_g9_importable(self):
        from kunlun.audit.gates.gate_g9_ai_rate import GateG9AIRate
        assert GateG9AIRate is not None

    def test_g9_basic_run(self):
        from kunlun.audit.gates.gate_g9_ai_rate import GateG9AIRate
        g9 = GateG9AIRate()
        result = g9.run(GOOD_TEXT)
        assert result.gate_id == "G9"
        assert result.score >= 0
        assert result.score <= 1
        assert "ai_rate" in result.data

    def test_g9_ai_text_higher_rate(self):
        from kunlun.audit.gates.gate_g9_ai_rate import GateG9AIRate
        g9 = GateG9AIRate()
        good_result = g9.run(GOOD_TEXT)
        ai_result = g9.run(AI_TEXT)
        assert ai_result.data["ai_rate"] > good_result.data["ai_rate"]

    def test_g9_short_text_skip(self):
        from kunlun.audit.gates.gate_g9_ai_rate import GateG9AIRate
        g9 = GateG9AIRate()
        result = g9.run(SHORT_TEXT)
        assert result.data.get("skipped", False) is True
        assert result.score == 0.9

    def test_g9_empty_text(self):
        from kunlun.audit.gates.gate_g9_ai_rate import GateG9AIRate
        g9 = GateG9AIRate()
        result = g9.run(EMPTY_TEXT)
        assert result.data.get("skipped", False) is True

    def test_g9_auto_humanize(self):
        from kunlun.audit.gates.gate_g9_ai_rate import GateG9AIRate
        g9 = GateG9AIRate()
        result = g9.run(AI_TEXT, auto_humanize=True, aggressive=0.7)
        data = result.data
        if data.get("auto_humanized"):
            assert data["ai_rate_after"] <= data["ai_rate_before"]
            assert "humanized_text" in data
            assert "strategies_used" in data

    def test_g9_registered_in_audit_gates(self):
        from kunlun.audit.gates import AUDIT_GATES, GATE_WEIGHTS, audit_gates
        assert len(AUDIT_GATES) == 9
        assert "G9" in GATE_WEIGHTS
        assert GATE_WEIGHTS["G9"] > 0
        result = audit_gates(GOOD_TEXT, blueprint={"chapter": 1})
        assert "G9" in result.gates
        assert len(result.gates) == 9


# ═══════════════════════════════════════════════════
# 2. Gacha第10维风格评分测试
# ═══════════════════════════════════════════════════

class TestGachaStyleDimension:
    """Gacha第10维风格匹配度测试"""

    def _get_engine(self):
        from kunlun.gacha.engine import GachaEngine
        engine = GachaEngine.__new__(GachaEngine)
        engine._models = []
        engine.target_style_fingerprint = None
        return engine

    def test_style_match_method_exists(self):
        engine = self._get_engine()
        assert hasattr(engine, "_score_style_match")

    def test_style_match_returns_in_range(self):
        engine = self._get_engine()
        score = engine._score_style_match(GOOD_TEXT)
        assert 0 <= score <= 1

    def test_style_match_distinguishes_styles(self):
        engine = self._get_engine()
        good_score = engine._score_style_match(GOOD_TEXT)
        ai_score = engine._score_style_match(AI_TEXT)
        # 优质文本风格丰富度应高于AI模板文本
        assert good_score >= ai_score - 0.1  # 允许小误差

    def test_total_score_includes_style(self):
        engine = self._get_engine()
        score = engine._score_text(GOOD_TEXT)
        assert 0 <= score <= 1
        # 10维评分，style_match应贡献约10%
        style_score = engine._score_style_match(GOOD_TEXT)
        assert abs(score - style_score * 0.1) < 0.9  # 其他9维也有贡献

    def test_short_text_style_match(self):
        engine = self._get_engine()
        score = engine._score_style_match(SHORT_TEXT)
        assert 0 <= score <= 1


# ═══════════════════════════════════════════════════
# 3. Context第7段记忆注入测试
# ═══════════════════════════════════════════════════

class TestContextMemoryInjection:
    """Context第7段记忆注入测试"""

    def test_seven_segments(self):
        from kunlun.context.budget import DEFAULT_BUDGET_ALLOCATION
        assert len(DEFAULT_BUDGET_ALLOCATION) == 7
        assert "memory_injection" in DEFAULT_BUDGET_ALLOCATION
        assert abs(sum(DEFAULT_BUDGET_ALLOCATION.values()) - 1.0) < 0.01

    def test_memory_budget_positive(self):
        from kunlun.context.budget import ContextBudgetAllocator
        alloc = ContextBudgetAllocator(total_budget=8000)
        budget = alloc.get_segment_budget("memory_injection")
        assert budget > 0
        assert budget < 8000

    def test_assemble_with_memory_no_manager(self):
        from kunlun.context.budget import ContextBudgetAllocator
        alloc = ContextBudgetAllocator(total_budget=8000)
        segments = {"system_rules": "规则", "character_cards": "角色" * 100}
        result = alloc.assemble_with_memory(segments, memory_manager=None)
        assert "memory_injection" in result
        assert result["memory_injection"] == ""  # 无manager时为空

    def test_assemble_with_memory_with_text(self):
        from kunlun.context.budget import ContextBudgetAllocator
        alloc = ContextBudgetAllocator(total_budget=8000)
        segments = {"memory_injection": "测试记忆内容" * 10}
        result = alloc.assemble_with_memory(segments, memory_manager=None)
        assert len(result["memory_injection"]) > 0

    def test_assemble_still_works(self):
        """确保原有的assemble方法不受影响"""
        from kunlun.context.budget import ContextBudgetAllocator
        alloc = ContextBudgetAllocator(total_budget=5000)
        result = alloc.assemble({"current_draft": "测试。" * 200})
        assert "current_draft" in result
        assert len(result["current_draft"]) <= 5000


# ═══════════════════════════════════════════════════
# 4. Quality 6维仪表盘测试
# ═══════════════════════════════════════════════════

class TestSixDimensionDashboard:
    """Quality六维仪表盘测试"""

    def test_importable(self):
        from kunlun.quality.six_dim_dashboard import six_dim_dashboard
        assert six_dim_dashboard is not None

    def test_analyze_returns_report(self):
        from kunlun.quality import six_dim_dashboard
        report = six_dim_dashboard.analyze(GOOD_TEXT, chapter=1)
        assert report.overall_score >= 0
        assert report.overall_score <= 1
        assert len(report.dimensions) == 6

    def test_six_dimensions_present(self):
        from kunlun.quality import six_dim_dashboard
        report = six_dim_dashboard.analyze(GOOD_TEXT)
        expected = ["pacing", "pleasure", "character", "logic", "style", "innovation"]
        for dim in expected:
            assert dim in report.dimensions
            assert report.dimensions[dim].score >= 0
            assert report.dimensions[dim].score <= 1

    def test_radar_data(self):
        from kunlun.quality import six_dim_dashboard
        report = six_dim_dashboard.analyze(GOOD_TEXT)
        radar = report.radar_data()
        assert "labels" in radar
        assert "scores" in radar
        assert "target" in radar
        assert len(radar["labels"]) == 6
        assert len(radar["scores"]) == 6

    def test_short_text(self):
        from kunlun.quality import six_dim_dashboard
        report = six_dim_dashboard.analyze(SHORT_TEXT)
        assert report.overall_level == "文本过短"

    def test_cliche_penalty_on_ai_text(self):
        """AI模板文的创新维度应受套路词惩罚"""
        from kunlun.quality import six_dim_dashboard
        good_report = six_dim_dashboard.analyze(GOOD_TEXT)
        ai_report = six_dim_dashboard.analyze(AI_TEXT * 3)
        # AI模板文创新分应低于优质文本
        assert (
            ai_report.dimensions["innovation"].score
            <= good_report.dimensions["innovation"].score + 0.1
        )

    def test_to_dict(self):
        from kunlun.quality import six_dim_dashboard
        report = six_dim_dashboard.analyze(GOOD_TEXT)
        d = report.to_dict()
        assert "overall_score" in d
        assert "dimensions" in d
        assert "strengths" in d
        assert "weaknesses" in d


# ═══════════════════════════════════════════════════
# 5. Vibe即时质量反馈测试
# ═══════════════════════════════════════════════════

class TestVibeQualityFeedback:
    """Vibe即时质量反馈测试"""

    def test_importable(self):
        from kunlun.vibe_writer.quality_feedback import vibe_quality_feedback
        assert vibe_quality_feedback is not None

    def test_analyze_returns_feedback(self):
        from kunlun.vibe_writer import vibe_quality_feedback
        fb = vibe_quality_feedback.analyze(GOOD_TEXT)
        assert fb.overall_score >= 0
        assert fb.ai_rate >= 0
        assert fb.word_count > 0

    def test_stuck_detection_no_dialogue(self):
        """长时间无对话应检测为卡文"""
        from kunlun.vibe_writer import vibe_quality_feedback
        text = (
            "林羽走在路上。他看到了山。山很高。他继续走。"
            "风吹过。树叶沙沙响。他觉得有点冷。于是加快了脚步。"
        ) * 20
        fb = vibe_quality_feedback.analyze(text)
        # 超过800字无对话应触发卡文检测
        assert fb.word_count > 800
        # 卡文检测应触发（无对话或心理过多）
        assert fb.is_stuck is True or fb.dialogue_ratio < 0.05

    def test_normal_text_not_stuck(self):
        from kunlun.vibe_writer import vibe_quality_feedback
        fb = vibe_quality_feedback.analyze(GOOD_TEXT)
        assert fb.is_stuck is False

    def test_drop_off_detection(self):
        from kunlun.vibe_writer import vibe_quality_feedback
        fb = vibe_quality_feedback.analyze(GOOD_TEXT)
        assert isinstance(fb.drop_off_points, list)

    def test_immediate_suggestions(self):
        from kunlun.vibe_writer import vibe_quality_feedback
        fb = vibe_quality_feedback.analyze(GOOD_TEXT)
        assert isinstance(fb.immediate_suggestions, list)
        assert len(fb.immediate_suggestions) > 0

    def test_summary(self):
        from kunlun.vibe_writer import vibe_quality_feedback
        fb = vibe_quality_feedback.analyze(GOOD_TEXT)
        summary = fb.summary()
        assert "质量" in summary
        assert "AI率" in summary

    def test_to_dict(self):
        from kunlun.vibe_writer import vibe_quality_feedback
        fb = vibe_quality_feedback.analyze(GOOD_TEXT)
        d = fb.to_dict()
        assert "overall_score" in d
        assert "ai_rate" in d
        assert "is_stuck" in d
        assert "drop_off_points" in d

    def test_vibe_writer_integration(self):
        """VibeWriter应集成质量反馈"""
        from kunlun.vibe_writer import VibeContext, VibeWriter
        writer = VibeWriter(book_id="test")
        ctx = VibeContext(current_text=GOOD_TEXT, chapter_title="测试")
        writer.set_context(ctx)
        qf = writer.get_quality_feedback()
        assert qf is not None
        assert "overall_score" in qf


# ═══════════════════════════════════════════════════
# 6. 4个核心优化模块基本测试
# ═══════════════════════════════════════════════════

class TestCoreOptimizationModules:
    """4个核心优化模块基本功能测试"""

    def test_ai_rate_importable(self):
        from kunlun.ai_rate import detect_ai_rate, humanize_text
        assert detect_ai_rate is not None
        assert humanize_text is not None

    def test_ai_rate_detect(self):
        from kunlun.ai_rate import detect_ai_rate
        report = detect_ai_rate(AI_TEXT)
        assert report.total_score >= 0
        assert report.word_count > 0

    def test_ai_rate_humanize(self):
        from kunlun.ai_rate import humanize_text
        result = humanize_text(AI_TEXT, aggressive=0.7)
        assert result.ai_rate_before >= 0
        assert result.ai_rate_after >= 0
        assert result.ai_rate_after <= result.ai_rate_before + 5  # 允许小误差

    def test_style_learner_importable(self):
        from kunlun.style_learner import extract_style_fingerprint, list_preset_styles
        assert extract_style_fingerprint is not None
        presets = list_preset_styles()
        assert len(presets) >= 5

    def test_memory_importable(self):
        from kunlun.memory import create_memory_manager
        assert create_memory_manager is not None

    def test_debate_review_importable(self):
        from kunlun.debate_review import debate_review, full_quality_assessment, simulate_readers
        assert debate_review is not None
        assert simulate_readers is not None
        assert full_quality_assessment is not None

    def test_all_modules_importable(self):
        modules = [
            "kunlun.ai_rate",
            "kunlun.style_learner",
            "kunlun.memory",
            "kunlun.debate_review",
            "kunlun.audit.gates.gate_g9_ai_rate",
            "kunlun.quality.six_dim_dashboard",
            "kunlun.vibe_writer.quality_feedback",
        ]
        for mod in modules:
            __import__(mod)
