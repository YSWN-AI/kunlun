"""
测试 — 题材模板库 (genre/)
"""

import pytest

pytestmark = pytest.mark.unit

from kunlun.genre.engine import (  # noqa: E402
    TOP10_TEMPLATES,
    GenreCategory,
    GenreConfig,
    GenreRuleEngine,
    GenreTemplate,
    PaceType,
    get_genre_engine,
)


class TestTop10Templates:
    """测试TOP10题材模板"""

    def test_all_10_templates_exist(self):
        assert len(TOP10_TEMPLATES) == 10

    def test_template_ids(self):
        expected_ids = [
            "dushi_xiuzhen",
            "xuanhuan",
            "xitong",
            "chongsheng",
            "chuanyue",
            "mori",
            "xuanyi",
            "youxi",
            "kehuan",
            "yanqing",
        ]
        for tid in expected_ids:
            assert tid in TOP10_TEMPLATES, f"Missing template: {tid}"

    def test_template_structure(self):
        for t in TOP10_TEMPLATES.values():
            assert isinstance(t, GenreTemplate)
            assert t.name
            assert t.description
            assert t.typical_word_count[0] > 0
            assert t.typical_word_count[1] >= t.typical_word_count[0]
            assert t.pleasure_point_density > 0
            assert len(t.primary_pleasure_types) >= 2
            assert len(t.conflict_archetypes) >= 2
            assert len(t.golden_three_blueprint) == 3
            assert len(t.suitable_platforms) > 0
            assert isinstance(t.pace, PaceType)

    def test_get_prompt_context(self):
        t = TOP10_TEMPLATES["xitong"]
        ctx = t.get_prompt_context()
        assert "系统流" in ctx
        assert "金手指" in ctx or "系统" in ctx
        assert "爽点密度" in ctx

    def test_match_score_exact(self):
        t = TOP10_TEMPLATES["xuanhuan"]
        score = t.match_score(
            {
                "genre": "玄幻",
                "pace": "medium",
                "target_words": 3000000,
                "platform": "qidian",
                "preferred_pleasures": ["升级", "热血"],
                "audience": "general",
            }
        )
        assert score >= 70  # 高匹配

    def test_match_score_partial(self):
        t = TOP10_TEMPLATES["xitong"]
        score = t.match_score(
            {
                "genre": "系统",
                "pace": "fast",
                "target_words": 2000000,
                "platform": "fanqie",
                "preferred_pleasures": ["打脸"],
                "audience": "mass",
            }
        )
        assert score >= 60

    def test_match_score_low(self):
        t = TOP10_TEMPLATES["yanqing"]
        score = t.match_score(
            {
                "genre": "科幻",
                "pace": "fast",
                "target_words": 5000000,
                "platform": "feilu",
                "preferred_pleasures": ["打脸", "碾压"],
                "audience": "mass",
            }
        )
        assert score < 50  # 低匹配


class TestGenreRuleEngine:
    """测试题材规则引擎"""

    def test_get_config(self):
        cfg = GenreRuleEngine.get_config("xuanhuan_dongfang")
        assert cfg is not None
        assert cfg.name == "东方玄幻"

    def test_get_config_invalid(self):
        cfg = GenreRuleEngine.get_config("nonexistent")
        assert cfg is None

    def test_list_all_genres(self):
        genres = GenreRuleEngine.list_all_genres()
        assert len(genres) > 10
        assert all("id" in g for g in genres)

    def test_list_by_category(self):
        genres = GenreRuleEngine.list_by_category(GenreCategory.DUSHI)
        assert len(genres) > 0
        assert all(g.category == GenreCategory.DUSHI for g in genres)

    def test_list_templates(self):
        templates = GenreRuleEngine.list_templates()
        assert len(templates) == 10
        assert all("id" in t for t in templates)

    def test_get_template(self):
        t = GenreRuleEngine.get_template("xitong")
        assert t is not None
        assert t.name == "系统流"

    def test_get_template_invalid(self):
        t = GenreRuleEngine.get_template("nonexistent")
        assert t is None

    def test_recommend_basic(self):
        results = GenreRuleEngine.recommend(
            genre="都市",
            pace="fast",
            target_words=2000000,
            platform="fanqie",
            preferred_pleasures=["打脸", "装逼"],
            top_n=3,
        )
        assert len(results) <= 3
        assert len(results) >= 1
        assert all("score" in r for r in results)
        assert all("reasons" in r for r in results)

    def test_recommend_with_empty_prefs(self):
        results = GenreRuleEngine.recommend(top_n=5)
        assert len(results) <= 5
        assert len(results) >= 1

    def test_recommend_genre_xuanhuan(self):
        results = GenreRuleEngine.recommend(genre="玄幻", preferred_pleasures=["升级", "热血"])
        assert results  # 应该能匹配到
        assert any("玄幻" in r["name"] for r in results) or any(
            r["template_id"] == "xuanhuan" for r in results
        )

    def test_recommend_platform_specific(self):
        results = GenreRuleEngine.recommend(platform="jjwxc", top_n=2)
        assert any(
            r.get("template_id") == "yanqing" or "言情" in r.get("name", "") for r in results
        )

    def test_merge_configs(self):
        merged = GenreRuleEngine.merge_configs(["xuanhuan_dongfang", "xitong_liu"])
        assert merged is not None
        assert len(merged.preferred_pleasures) > 0
        assert merged.pace == PaceType.FAST  # 系统流的快节奏优先

    def test_merge_configs_single(self):
        merged = GenreRuleEngine.merge_configs(["xuanhuan_dongfang"])
        assert merged.name == "东方玄幻"

    def test_merge_configs_invalid(self):
        with pytest.raises(ValueError):
            GenreRuleEngine.merge_configs([])

    def test_generate_creative_brief(self):
        brief = GenreRuleEngine.generate_creative_brief("xitong_liu")
        assert brief["genre"] == "系统流"
        assert "golden_three_tips" in brief

    def test_generate_creative_brief_invalid(self):
        brief = GenreRuleEngine.generate_creative_brief("nonexistent")
        assert brief == {}

    def test_get_genre_prompt_context(self):
        ctx = GenreRuleEngine.get_genre_prompt_context("xitong_liu")
        assert "系统流" in ctx
        assert "禁忌" in ctx

    def test_get_genre_prompt_context_invalid(self):
        ctx = GenreRuleEngine.get_genre_prompt_context("nonexistent")
        assert ctx == ""


def test_genre_config_fields():
    from kunlun.genre.engine import AudienceLevel

    cfg = GenreConfig(
        genre_id="test",
        name="Test",
        category=GenreCategory.QITA,
        description="Desc",
        suggested_words_per_chapter=(2000, 3000),
        suggested_total_words=(1000000, 2000000),
        pace=PaceType.FAST,
        audience=AudienceLevel.MASS,
        preferred_pleasures=["打脸", "升级"],
    )
    assert cfg.name == "Test"
    assert cfg.preferred_pleasures == ["打脸", "升级"]


def test_factory():
    e1 = get_genre_engine()
    e2 = get_genre_engine()
    assert e1 is e2
