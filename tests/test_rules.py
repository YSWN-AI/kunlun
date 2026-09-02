"""
测试三层规则分离系统 (Three-Layer Rule Separation)
"""

import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

from kunlun.rules.engine import (
    UNIVERSAL_RULES,
    Rule,
    RuleCategory,
    RuleEngine,
    RuleLayer,
    RuleSeverity,
    RuleStack,
    get_rule_engine,
)


class TestRule:
    def test_rule_creation(self):
        r = Rule(
            id="TEST001",
            category=RuleCategory.STYLE,
            severity=RuleSeverity.HARD,
            description="测试规则",
        )
        assert r.id == "TEST001"
        assert r.category == RuleCategory.STYLE
        assert r.severity == RuleSeverity.HARD
        assert r.enabled is True
        assert r.tags == []

    def test_rule_with_params_and_tags(self):
        r = Rule(
            id="TEST002",
            category=RuleCategory.STRUCTURE,
            severity=RuleSeverity.SOFT,
            description="字数检查",
            check="word_count >= 500",
            params={"min_words": 500},
            tags=["structure"],
        )
        assert r.params["min_words"] == 500
        assert "structure" in r.tags

    def test_rule_disabled(self):
        r = Rule(
            id="TEST003",
            category=RuleCategory.PLEASURE,
            severity=RuleSeverity.INFO,
            description="测试",
            enabled=False,
        )
        assert r.enabled is False


class TestRuleEngine:
    def test_init(self):
        engine = RuleEngine()
        assert engine is not None
        assert engine._book_rules_cache == {}
        assert engine._genre_rules_cache == {}

    def test_get_universal_rules(self):
        engine = RuleEngine()
        layer = engine.get_universal_rules()
        assert isinstance(layer, RuleLayer)
        assert layer.layer_type == "universal"
        assert len(layer.rules) == 15
        assert "U001" in layer.rules
        assert layer.rules["U001"].severity == RuleSeverity.HARD

    def test_get_genre_rules_xuanhuan(self):
        engine = RuleEngine()
        layer = engine.get_genre_rules("xuanhuan_dongfang")
        assert layer.layer_type == "genre"
        assert "东方玄幻" in layer.name
        assert len(layer.rules) >= 8

    def test_get_genre_rules_unknown(self):
        engine = RuleEngine()
        layer = engine.get_genre_rules("nonexistent_genre")
        assert layer.layer_type == "genre"
        assert layer.rules == {}

    def test_genre_rules_cache(self):
        engine = RuleEngine()
        layer1 = engine.get_genre_rules("xuanhuan_dongfang")
        layer2 = engine.get_genre_rules("xuanhuan_dongfang")
        assert layer1 is layer2

    def test_build_rule_stack_with_genre_and_book(self):
        engine = RuleEngine()
        stack = engine.build_rule_stack(
            genre_id="xuanhuan_dongfang",
            book_id="test_book",
        )
        assert isinstance(stack, RuleStack)
        assert stack.book_id == "test_book"
        assert len(stack.layers) == 3  # universal + genre + book
        assert stack.stats["total_rules"] >= 23  # 15 universal + 8+ genre

    def test_build_rule_stack_empty(self):
        engine = RuleEngine()
        stack = engine.build_rule_stack()
        assert len(stack.layers) == 1
        assert stack.stats["total_rules"] == 15

    def test_get_active_rules(self):
        engine = RuleEngine()
        stack = engine.build_rule_stack()
        active = engine.get_active_rules(stack)
        assert len(active) == 15
        hard = engine.get_active_rules(stack, severity=RuleSeverity.HARD)
        assert len(hard) == stack.stats["hard_rules"]

    def test_get_rules_by_category(self):
        engine = RuleEngine()
        stack = engine.build_rule_stack()
        style_rules = engine.get_rules_by_category(stack, RuleCategory.STYLE)
        assert len(style_rules) >= 3

    def test_export_rule_stack_yaml(self):
        engine = RuleEngine()
        stack = engine.build_rule_stack(genre_id="xuanhuan_dongfang")
        yaml_str = engine.export_rule_stack(stack, format="yaml")
        assert "book_id" in yaml_str
        assert "stats" in yaml_str

    def test_export_rule_stack_markdown(self):
        engine = RuleEngine()
        stack = engine.build_rule_stack()
        md = engine.export_rule_stack(stack, format="markdown")
        assert "# 规则堆栈" in md
        assert "总规则数" in md

    def test_export_invalid_format(self):
        engine = RuleEngine()
        stack = engine.build_rule_stack()
        with pytest.raises(ValueError, match="不支持的格式"):
            engine.export_rule_stack(stack, format="json")

    def test_save_and_load_book_rules(self):
        engine = RuleEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg

            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                r1 = Rule(
                    id="B001",
                    category=RuleCategory.STYLE,
                    severity=RuleSeverity.HARD,
                    description="自定义规则1",
                )
                layer = RuleLayer(
                    name="测试书籍",
                    layer_type="book",
                    description="测试",
                    rules={"B001": r1},
                )
                engine.save_book_rules("my_book", layer)
                loaded = engine.get_book_rules("my_book")
                assert "B001" in loaded.rules
                assert loaded.rules["B001"].description == "自定义规则1"
            finally:
                cfg.settings.DATA_DIR = original
                engine._book_rules_cache.clear()

    def test_build_rule_stack_with_extra_genres(self):
        engine = RuleEngine()
        stack = engine.build_rule_stack(
            genre_id="xuanhuan_dongfang",
            extra_genre_ids=["xuanhuan_xifang"],
        )
        assert len(stack.layers) == 3  # universal + main genre + sub genre
        assert stack.stats["total_rules"] > 15


class TestUniversalRules:
    def test_all_universal_rules_have_ids(self):
        for rid, rule in UNIVERSAL_RULES.rules.items():
            assert rule.id == rid
            assert rule.description

    def test_universal_rules_metadata(self):
        assert UNIVERSAL_RULES.metadata["builtin"] is True
        assert UNIVERSAL_RULES.metadata["version"] == "1.0"


class TestRuleLayer:
    def test_empty_layer(self):
        layer = RuleLayer(name="空层", layer_type="book", description="")
        assert layer.rules == {}
        assert layer.metadata == {}

    def test_layer_with_rules(self):
        r1 = Rule(
            id="R1", category=RuleCategory.CONTENT, severity=RuleSeverity.HARD, description="规则1"
        )
        layer = RuleLayer(
            name="测试",
            layer_type="book",
            description="测试",
            rules={"R1": r1},
            metadata={"version": "1"},
        )
        assert len(layer.rules) == 1
        assert layer.metadata["version"] == "1"


class TestSingleton:
    def test_get_rule_engine_singleton(self):
        engine1 = get_rule_engine()
        engine2 = get_rule_engine()
        assert engine1 is engine2
