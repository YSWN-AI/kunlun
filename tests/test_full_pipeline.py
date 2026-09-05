"""
全管线集成标准 pytest 测试
覆盖: structure / proofread / character / plot / coherence / worlds / pipeline
"""

import pytest

pytestmark = pytest.mark.unit


class TestAllImports:
    """模块导入验证"""

    MODULES = [
        ("structure", "kunlun.structure", ["structure_analyzer", "tension_curve", "plot_detector"]),
        ("proofread", "kunlun.proofread", ["proofread_engine"]),
        ("character", "kunlun.character", ["character_engine"]),
        (
            "plot",
            "kunlun.plot",
            ["causal_chain_engine", "foreshadowing_manager", "conflict_engine"],
        ),
        ("coherence", "kunlun.coherence", ["coherence_engine"]),
        (
            "worlds",
            "kunlun.worlds",
            ["WorldBuilder", "WorldAtlas", "FactionNetwork", "TimelineEngine"],
        ),
    ]

    @pytest.mark.parametrize("name,module,attrs", MODULES)
    def test_module_import(self, name, module, attrs):  # noqa: ARG002
        mod = __import__(module, fromlist=attrs)
        for attr in attrs:
            obj = getattr(mod, attr)
            assert obj is not None, f"{module}.{attr} 导入为 None"


class TestStructureAnalyzer:
    """故事结构分析器"""

    def test_analyze_chapter(self):
        from kunlun.structure import structure_analyzer

        text = (
            "突然，一道剑光从黑暗中斩来。林尘心头一紧，连忙侧身躲避。"
            "然而那剑光太快，他还是被擦中了肩膀。"
        )
        report = structure_analyzer.analyze_chapter(text, 5, 100)
        assert hasattr(report, "detected_beat_stc")
        assert hasattr(report, "on_track")
        assert isinstance(report.on_track, bool)

    def test_tension_curve(self):
        from kunlun.structure import tension_curve

        text = "他握紧拳头，怒吼一声冲了上去。"
        tension = tension_curve.calculate_tension(text)
        assert hasattr(tension, "tension_score")
        assert hasattr(tension, "is_flat")

    def test_turning_points(self):
        from kunlun.structure import plot_detector

        text = "突然，门开了。然后一切都不一样了。"
        turning_points = plot_detector.detect_turning_points(text)
        assert isinstance(turning_points, list)


class TestProofread:
    """审校引擎"""

    def test_proofread_standard(self):
        from kunlun.proofread import proofread_engine

        text = "少先队员因该为老人让坐。他非常非常地生气，突然突然就出手了。"
        report = proofread_engine.proofread(text, level="standard")
        assert hasattr(report, "score")
        assert hasattr(report, "total_issues")
        assert 0 <= report.score <= 100

    def test_proofread_quick(self):
        from kunlun.proofread import proofread_engine

        text = "一切正常没有问题。"
        report = proofread_engine.proofread(text, level="quick")
        assert report.total_issues >= 0

    def test_proofread_empty_text(self):
        from kunlun.proofread import proofread_engine

        report = proofread_engine.proofread("", level="standard")
        assert report.total_issues >= 0


class TestCharacterEngine:
    """角色引擎"""

    def test_register_character(self):
        from kunlun.character import (
            CharacterArcType,
            CharacterProfile,
            CharacterRole,
            character_engine,
        )

        profile = CharacterProfile(
            character_id="test_lin_chen",
            name="林尘",
            role=CharacterRole.MAIN,
            arc_type=CharacterArcType.LEVEL_UP,
            personality=["坚毅", "隐忍", "重情义"],
            abilities=["九天剑诀", "星辰之力"],
            inner_conflict="复仇与守护的矛盾",
            external_goal="成为最强",
        )
        character_engine.register_character(profile)
        cast = character_engine.get_cast_summary()
        assert cast["total"] >= 1

    def test_arc_stage(self):
        from kunlun.character import CharacterArcType, character_engine

        arc = character_engine.arc_engine.get_current_stage(CharacterArcType.LEVEL_UP, 30, 200)
        assert "current_stage" in arc
        assert "progress_pct" in arc
        assert 0 <= arc["progress_pct"] <= 100


class TestPlotEngine:
    """情节引擎"""

    def test_causal_event(self):
        from kunlun.plot import CausalEvent, causal_chain_engine

        event = CausalEvent(
            event_id="test_evt_001",
            chapter_num=1,
            name="退婚",
            cause="慕家认为废灵根无价值",
            event="慕雪当众退婚",
            effect="林尘立下三年之约",
            decision="独闯青峰山",
            tension_level=4,
            is_turning_point=True,
        )
        causal_chain_engine.add_event(event)
        assert causal_chain_engine is not None

    def test_foreshadowing_plant(self):
        from kunlun.plot import ForeshadowingItem, foreshadowing_manager

        fs = ForeshadowingItem(
            foreshadow_id="test_fs_001",
            name="神秘玉佩",
            description="林尘母亲留下的玉佩，内含惊人秘密",
            planted_chapter=3,
            target_chapter=25,
        )
        foreshadowing_manager.plant(fs)
        stats = foreshadowing_manager.get_stats()
        assert stats["total"] >= 1

    def test_conflict_detection(self):
        from kunlun.plot import conflict_engine

        text = "两大强者对峙，空气几乎凝固。"
        scores = conflict_engine.detect_conflicts(text)
        assert len(scores) > 0


class TestCoherence:
    """连贯性引擎"""

    def test_chapter_summary(self):
        from kunlun.coherence import ChapterSummary, coherence_engine

        summary = ChapterSummary(
            chapter_num=1,
            title="退婚",
            summary="林尘被慕家退婚，立下三年之约。",
            key_events=["退婚事件", "三年之约"],
            character_changes=[{"character": "林尘", "change_type": "觉醒"}],
        )
        coherence_engine.add_chapter(summary)
        health = coherence_engine.get_health_report()
        assert health["summaries"]["total_summaries"] >= 1

    def test_tracked_item(self):
        from kunlun.coherence import TrackedItem, coherence_engine

        item = TrackedItem(
            item_id="test_sword_001",
            name="星辰剑",
            category="item",
            current_state="完好在手",
            last_seen_chapter=1,
        )
        coherence_engine.register_item(item)
        health = coherence_engine.get_health_report()
        assert health["health_score"] is not None
