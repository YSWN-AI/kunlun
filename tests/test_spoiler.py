"""
测试剧透过滤系统 (Spoiler Filter)
"""

import pytest

from kunlun.spoiler import (
    STAGES,
    SpoilerFilter,
    SpoilerLevel,
    StageResult,
    spoiler_filter,
)

pytestmark = pytest.mark.unit


class TestSpoilerLevel:
    def test_levels(self):
        assert SpoilerLevel.STRICT == "strict"
        assert SpoilerLevel.MODERATE == "moderate"
        assert SpoilerLevel.MINIMAL == "minimal"
        assert SpoilerLevel.NONE == "none"


class TestStages:
    def test_six_stages(self):
        assert len(STAGES) == 6
        names = [s.name for s in STAGES]
        assert "开篇铺垫" in names
        assert "早期发展" in names
        assert "中期发展" in names
        assert "后期发展" in names
        assert "高潮迭起" in names
        assert "收尾完结" in names

    def test_stages_cover_full_range(self):
        assert STAGES[0].chapter_range[0] == 0
        assert STAGES[-1].chapter_range[1] == 1.0
        for i in range(len(STAGES) - 1):
            assert STAGES[i].chapter_range[1] == STAGES[i + 1].chapter_range[0]


class TestSpoilerFilter:
    def test_get_stage_opening(self):
        result = SpoilerFilter.get_stage(chapter=5, total=100)
        assert isinstance(result, StageResult)
        assert result.stage.name == "开篇铺垫"
        assert result.progress == 5.0
        assert result.stage.spoiler_level == SpoilerLevel.STRICT

    def test_get_stage_early(self):
        result = SpoilerFilter.get_stage(chapter=20, total=100)
        assert result.stage.name == "早期发展"
        assert result.stage.rag_lookahead == 1
        assert result.stage.use_future_rag is False

    def test_get_stage_mid(self):
        result = SpoilerFilter.get_stage(chapter=50, total=100)
        assert result.stage.name == "中期发展"
        assert result.stage.rag_lookahead == 2
        assert result.stage.use_future_rag is True

    def test_get_stage_late(self):
        result = SpoilerFilter.get_stage(chapter=70, total=100)
        assert result.stage.name == "后期发展"

    def test_get_stage_climax(self):
        result = SpoilerFilter.get_stage(chapter=85, total=100)
        assert result.stage.name == "高潮迭起"
        assert result.stage.spoiler_level == SpoilerLevel.NONE

    def test_get_stage_ending(self):
        result = SpoilerFilter.get_stage(chapter=95, total=100)
        assert result.stage.name == "收尾完结"

    def test_get_stage_first_chapter(self):
        result = SpoilerFilter.get_stage(chapter=1, total=100)
        assert result.stage.name == "开篇铺垫"
        assert result.chapter == 1

    def test_get_stage_last_chapter(self):
        result = SpoilerFilter.get_stage(chapter=100, total=100)
        assert result.stage.name == "收尾完结"
        assert result.progress == 100.0

    def test_get_stage_total_zero(self):
        result = SpoilerFilter.get_stage(chapter=1, total=0)
        assert result.progress == 100.0

    def test_spoiler_instructions_strict(self):
        result = SpoilerFilter.get_stage(chapter=5, total=100)
        assert "STRICT" in result.spoiler_instructions
        assert "剧透约束" in result.spoiler_instructions

    def test_spoiler_instructions_moderate(self):
        result = SpoilerFilter.get_stage(chapter=40, total=100)
        assert "MODERATE" in result.spoiler_instructions

    def test_spoiler_instructions_minimal(self):
        result = SpoilerFilter.get_stage(chapter=70, total=100)
        assert "MINIMAL" in result.spoiler_instructions

    def test_spoiler_instructions_none(self):
        result = SpoilerFilter.get_stage(chapter=85, total=100)
        assert "NONE" in result.spoiler_instructions

    def test_rag_query_modifier(self):
        result = SpoilerFilter.get_stage(chapter=5, total=100)
        assert "仅检索" in result.rag_query_modifier

    def test_visible_range_opening(self):
        result = SpoilerFilter.get_stage(chapter=5, total=100)
        assert result.visible_range[0] <= result.visible_range[1]

    def test_filter_rag_candidates(self):
        candidates = [
            {"chapter": 4, "text": "最近章节"},
            {"chapter": 15, "text": "未来内容"},
            {"chapter": 5, "text": "当前章节"},
        ]
        filtered = SpoilerFilter.filter_rag_candidates(candidates, chapter=5, total=100)
        assert len(filtered) == 2
        chapters = [c["chapter"] for c in filtered]
        assert 4 in chapters
        assert 5 in chapters
        assert 15 not in chapters

    def test_filter_rag_candidates_no_chapter(self):
        candidates = [
            {"text": "无章节号"},
            {"chapter": 2, "text": "有章节号"},
        ]
        filtered = SpoilerFilter.filter_rag_candidates(candidates, chapter=10, total=100)
        assert len(filtered) >= 1
        assert any("无章节号" in c.get("text", "") for c in filtered)

    def test_filter_rag_candidates_climax(self):
        candidates = [
            {"chapter": 84, "text": "高潮前"},
            {"chapter": 85, "text": "当前"},
            {"chapter": 86, "text": "高潮后"},
        ]
        filtered = SpoilerFilter.filter_rag_candidates(candidates, chapter=85, total=100)
        assert len(filtered) == 3


class TestStageConfig:
    def test_stage_config_fields(self):
        config = STAGES[0]
        assert isinstance(config.chapter_range, tuple)
        assert isinstance(config.rag_lookahead, int)
        assert isinstance(config.use_future_rag, bool)
        assert config.spoiler_level in [
            SpoilerLevel.STRICT,
            SpoilerLevel.MODERATE,
            SpoilerLevel.MINIMAL,
            SpoilerLevel.NONE,
        ]


class TestStageResult:
    def test_stage_result_fields(self):
        result = SpoilerFilter.get_stage(chapter=10, total=100)
        assert result.chapter == 10
        assert result.total == 100
        assert isinstance(result.progress, float)
        assert isinstance(result.visible_range, tuple)
        assert isinstance(result.rag_query_modifier, str)
        assert isinstance(result.spoiler_instructions, str)


class TestSingleton:
    def test_spoiler_filter_singleton(self):
        assert spoiler_filter is not None
        assert isinstance(spoiler_filter, SpoilerFilter)
