"""
测试短篇生成引擎 (Shortform Engine)
"""
import pytest

from kunlun.shortform import (
    SHORTFORM_TEMPLATES,
    ShortformEngine,
    ShortformResult,
    shortform_engine,
)

pytestmark = pytest.mark.unit


class TestShortformTemplates:
    def test_templates_exist(self):
        assert len(SHORTFORM_TEMPLATES) == 4
        assert "short_story" in SHORTFORM_TEMPLATES
        assert "opening_hook" in SHORTFORM_TEMPLATES
        assert "flash_fiction" in SHORTFORM_TEMPLATES
        assert "essay" in SHORTFORM_TEMPLATES

    def test_template_structure(self):
        for template in SHORTFORM_TEMPLATES.values():
            assert "word_count" in template
            assert "structure" in template
            assert "scene_count" in template
            wmin, wmax = template["word_count"]
            assert wmin > 0
            assert wmax >= wmin

    def test_short_story_word_count(self):
        wmin, wmax = SHORTFORM_TEMPLATES["short_story"]["word_count"]
        assert wmin == 3000
        assert wmax == 10000

    def test_opening_hook_structure(self):
        structure = SHORTFORM_TEMPLATES["opening_hook"]["structure"]
        assert "hook" in structure
        assert "cliffhanger" in structure


class TestShortformResult:
    def test_result_success(self):
        result = ShortformResult(
            success=True, text="测试正文内容", word_count=500,
            mode="short_story", model_used="deepseek-chat",
            generation_time=2.5,
        )
        assert result.success is True
        assert result.word_count == 500
        assert result.mode == "short_story"
        assert result.model_used == "deepseek-chat"

    def test_result_failure(self):
        result = ShortformResult(
            success=False, text="", word_count=0,
            mode="short_story", model_used="",
            generation_time=0.0,
        )
        assert result.success is False
        assert result.text == ""


class TestShortformEngine:
    def test_init(self):
        engine = ShortformEngine()
        assert engine is not None

    def test_singleton(self):
        assert shortform_engine is not None
        assert isinstance(shortform_engine, ShortformEngine)
