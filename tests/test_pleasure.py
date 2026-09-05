"""
测试 — 爽点系统 (pleasure/)
"""

import pytest

pytestmark = pytest.mark.unit

from kunlun.pleasure.engine import (  # noqa: E402
    ArcPhase,
    PleasureArcPlan,
    PleasureArcPlanner,
    PleasureEngine,
    PleasureFatigueDetector,
    PleasureType,
    PleasureTypeConfig,
    get_pleasure_config,
    get_pleasure_engine,
)


class TestPleasureTypeConfigs:
    """测试爽点类型配置"""

    def test_all_types_have_config(self):
        """所有爽点类型都有配置"""
        for ptype in PleasureType:
            config = get_pleasure_config(ptype)
            assert isinstance(config, PleasureTypeConfig)
            assert config.intensity_base > 0
            assert config.fatigue_decay > 0
            assert config.optimal_interval > 0
            assert config.min_interval > 0
            assert len(config.suitable_genres) > 0

    def test_new_types_present(self):
        """新增的6种爽点类型存在"""
        assert PleasureType.AWAKENING.value == "awakening"
        assert PleasureType.SYSTEM_REWARD.value == "system_reward"
        assert PleasureType.FORTUNATE.value == "fortunate"
        assert PleasureType.HAREM.value == "harem"
        assert PleasureType.TORTURE.value == "torture"
        assert PleasureType.RHYTHM_BREAK.value == "rhythm_break"

    def test_grade_s_types(self):
        """S级爽点（最强爽点）"""
        from kunlun.pleasure.engine import PLEASURE_TYPE_CONFIGS

        s_configs = [
            PLEASURE_TYPE_CONFIGS[p]
            for p in [
                PleasureType.FACE_SLAP,
                PleasureType.LEVEL_UP,
                PleasureType.SHOW_OFF,
                PleasureType.AWAKENING,
                PleasureType.SYSTEM_REWARD,
                PleasureType.REVENGE,
            ]
        ]
        for cfg in s_configs:
            assert cfg.grade == "S", f"{cfg.name_cn} should be grade S"

    def test_effective_intensity(self):
        """有效强度计算: 间距太近→衰减"""
        config = get_pleasure_config(PleasureType.FACE_SLAP)
        full = config.get_effective_intensity(interval=3000, previous_count=0)
        close = config.get_effective_intensity(interval=500, previous_count=0)
        many = config.get_effective_intensity(interval=3000, previous_count=5)
        assert close < full, "近距离应降低强度"
        assert many < full, "多次重复应降低强度"

    def test_default_config_fallback(self):
        """未配置的类型返回默认值"""
        from kunlun.pleasure.engine import PLEASURE_TYPE_CONFIGS

        fake_type = PleasureType.FACE_SLAP
        config = PLEASURE_TYPE_CONFIGS.get(fake_type)
        assert config is not None
        assert config.grade == "S"


class TestPleasureFatigueDetector:
    """测试爽点疲劳检测器"""

    def test_no_fatigue_on_fresh(self):
        detector = PleasureFatigueDetector()
        from kunlun.pleasure.engine import PleasureEvent

        events = [
            PleasureEvent(
                event_type=PleasureType.FACE_SLAP,
                position=0,
                intensity=0.9,
                keywords_matched=["打脸"],
            ),
            PleasureEvent(
                event_type=PleasureType.LEVEL_UP,
                position=1000,
                intensity=0.8,
                keywords_matched=["升级"],
            ),
            PleasureEvent(
                event_type=PleasureType.REVEAL,
                position=2000,
                intensity=0.7,
                keywords_matched=["揭秘"],
            ),
        ]
        report = detector.feed(events)
        assert report["fatigue_detected"] is False

    def test_detect_consecutive_same(self):
        detector = PleasureFatigueDetector()
        from kunlun.pleasure.engine import PleasureEvent

        events = [
            PleasureEvent(
                event_type=PleasureType.FACE_SLAP,
                position=0,
                intensity=0.9,
                keywords_matched=["打脸"],
            ),
        ]
        detector.feed(events)
        detector.feed(events)
        detector.feed(events)
        report = detector.feed(events)
        assert report["fatigue_detected"] is True
        assert len(report["suggestions"]) > 0

    def test_detect_fixed_pattern(self):
        detector = PleasureFatigueDetector()
        from kunlun.pleasure.engine import PleasureEvent

        pattern = [
            PleasureEvent(
                event_type=PleasureType.FACE_SLAP, position=0, intensity=0.9, keywords_matched=["a"]
            ),
            PleasureEvent(
                event_type=PleasureType.LEVEL_UP,
                position=100,
                intensity=0.8,
                keywords_matched=["b"],
            ),
            PleasureEvent(
                event_type=PleasureType.OVERWHELM,
                position=200,
                intensity=0.7,
                keywords_matched=["c"],
            ),
        ]
        for _ in range(4):
            for e in pattern:
                detector.feed([e])
        report = detector.feed(pattern)
        assert report["fatigue_detected"] is True

    def test_variety_suggestions(self):
        detector = PleasureFatigueDetector()
        from kunlun.pleasure.engine import PleasureEvent

        for _ in range(5):
            detector.feed(
                [
                    PleasureEvent(
                        event_type=PleasureType.FACE_SLAP,
                        position=0,
                        intensity=0.9,
                        keywords_matched=["a"],
                    ),
                ]
            )
        suggestions = detector.get_variety_suggestions("玄幻")
        assert len(suggestions) > 0

    def test_reset(self):
        detector = PleasureFatigueDetector()
        from kunlun.pleasure.engine import PleasureEvent

        detector.feed(
            [
                PleasureEvent(
                    event_type=PleasureType.FACE_SLAP,
                    position=0,
                    intensity=0.9,
                    keywords_matched=["a"],
                ),
                PleasureEvent(
                    event_type=PleasureType.FACE_SLAP,
                    position=100,
                    intensity=0.9,
                    keywords_matched=["b"],
                ),
                PleasureEvent(
                    event_type=PleasureType.FACE_SLAP,
                    position=200,
                    intensity=0.9,
                    keywords_matched=["c"],
                ),
                PleasureEvent(
                    event_type=PleasureType.FACE_SLAP,
                    position=300,
                    intensity=0.9,
                    keywords_matched=["d"],
                ),
            ]
        )
        detector.reset()
        report = detector.feed([])
        assert report["fatigue_detected"] is False


class TestPleasureArcPlanner:
    """测试爽点弧线规划器"""

    def test_default_arc_creation(self):
        plan = PleasureArcPlanner.plan_default_arc("test_book", 100)
        assert plan.total_chapters == 100
        assert plan.book_id == "test_book"
        assert len(plan.phases) == 5
        assert len(plan.notes) > 0

    def test_phase_structure(self):
        plan = PleasureArcPlanner.plan_default_arc("test_book", 100)
        assert plan.phases[0].name == "开场引爆期（黄金三章）"
        assert plan.phases[0].target_density > plan.phases[1].target_density
        assert plan.phases[3].target_density >= plan.phases[0].target_density  # 高潮≥开场
        assert plan.phases[3].target_density > 3.0  # 高潮应为高密度

    def test_genre_specific_arc(self):
        plan = PleasureArcPlanner.plan_for_genre("test_book", 100, "系统流")
        assert any(PleasureType.SYSTEM_REWARD in p.primary_types for p in plan.phases)

    def test_genre_suspense_arc(self):
        plan = PleasureArcPlanner.plan_for_genre("test_book", 100, "悬疑推理")
        for phase in plan.phases:
            assert PleasureType.HOT_BLOOD not in phase.primary_types
            assert PleasureType.HAREM not in phase.primary_types

    def test_genre_romance_arc(self):
        plan = PleasureArcPlanner.plan_for_genre("test_book", 100, "言情")
        assert PleasureType.ROMANCE in plan.phases[1].primary_types

    def test_get_phase_for_chapter(self):
        plan = PleasureArcPlanner.plan_default_arc("test_book", 100)
        phase = PleasureArcPlanner.get_phase_for_chapter(plan, 1)
        assert phase is not None
        assert "黄金三章" in phase.name

        phase = PleasureArcPlanner.get_phase_for_chapter(plan, 95)
        assert phase is not None
        assert "收尾" in phase.name

        phase = PleasureArcPlanner.get_phase_for_chapter(plan, 999)
        assert phase is None

    def test_chapter_guidance(self):
        plan = PleasureArcPlanner.plan_default_arc("test_book", 100)
        guidance = PleasureArcPlanner.generate_chapter_guidance(plan, 5, 3000)
        assert "phase" in guidance
        assert "target_event_count" in guidance
        assert guidance["target_event_count"] > 0


class TestPleasureEngine:
    """测试爽点引擎主类"""

    def test_engine_creation(self):
        engine = PleasureEngine(book_id="test")
        assert engine.book_id == "test"

    def test_analyze_chapter_basic(self):
        engine = PleasureEngine(book_id="test")
        text = "打脸！" * 20 + "升级！突破！觉醒！" * 10
        report = engine.analyze_chapter(text, chapter_id="1")
        assert report.total_events > 0
        assert report.density_per_1000 > 0
        assert len(report.type_distribution) > 0
        assert report.rhythm_score > 0

    def test_analyze_empty(self):
        engine = PleasureEngine(book_id="test")
        report = engine.analyze_chapter("", chapter_id="0")
        assert report.total_events == 0
        assert report.rhythm_score == 50

    def test_init_arc_and_guidance(self):
        engine = PleasureEngine(book_id="test")
        plan = engine.init_arc(100, "玄幻")
        assert plan is not None
        assert len(plan.phases) == 5

        guidance = engine.get_chapter_guidance(1, 3000)
        assert "phase" in guidance
        assert guidance["target_event_count"] >= 0

        arc_data = engine.get_arc_plan()
        assert arc_data is not None
        assert len(arc_data["phases"]) == 5

    def test_check_fatigue(self):
        engine = PleasureEngine(book_id="test")
        text = "打脸！打脸！打脸！打脸！打脸！" * 10
        engine.analyze_chapter(text, chapter_id="1")
        fatigue = engine.check_fatigue()
        assert "fatigue_detected" in fatigue

    def test_variety_suggestions(self):
        engine = PleasureEngine(book_id="test")
        text = "打脸！打脸！打脸！打脸！打脸！" * 10
        engine.analyze_chapter(text, chapter_id="1")
        suggestions = engine.get_variety_suggestions("都市")
        assert len(suggestions) >= 0

    def test_get_global_stats(self):
        engine = PleasureEngine(book_id="test")
        engine.analyze_chapter("打脸！升级！" * 20, chapter_id="1")
        stats = engine.get_global_stats()
        assert stats["total_events"] > 0
        assert "type_distribution" in stats
        assert stats["chapter_count"] == 1

    def test_reset_fatigue(self):
        engine = PleasureEngine(book_id="test")
        engine.analyze_chapter("打脸！" * 30, chapter_id="1")
        engine.reset_fatigue()
        stats = engine.get_global_stats()
        assert stats["total_events"] == 0

    def test_factory(self):
        e1 = get_pleasure_engine("book_a")
        e2 = get_pleasure_engine("book_a")
        assert e1 is e2  # 同book_id返回同一实例


def test_arc_plan_data_class():
    plan = PleasureArcPlan(book_id="t", total_chapters=50, chapters_per_act=10)
    plan.phases.append(
        ArcPhase(
            name="test",
            chapter_range=(1, 10),
            target_density=2.0,
            primary_types=[PleasureType.FACE_SLAP],
        )
    )
    assert plan.phases[0].name == "test"
