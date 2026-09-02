"""
测试Story Bible统一管理模块
"""
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

from kunlun.story_bible.engine import (
    BibleEntry,
    BibleParser,
    BibleSection,
    ChapterBibleChange,
    CodexQueryResult,
    StoryBible,
    WorkflowPlan,
    WorkflowStage,
    get_story_bible,
)


class TestBibleSection:
    def test_sections(self):
        assert BibleSection.AUTHOR_INTENT.value == "author_intent"
        assert BibleSection.CURRENT_FOCUS.value == "current_focus"
        assert BibleSection.BOOK_RULES.value == "book_rules"
        assert BibleSection.STORY_BIBLE.value == "story_bible"


class TestWorkflowStage:
    def test_stages(self):
        assert WorkflowStage.IDEA.value == "idea"
        assert WorkflowStage.OUTLINE.value == "outline"
        assert WorkflowStage.BEATS.value == "beats"
        assert WorkflowStage.DRAFT.value == "draft"
        assert WorkflowStage.REVISE.value == "revise"


class TestBibleEntry:
    def test_defaults(self):
        entry = BibleEntry(
            key="char_zhangsan", section=BibleSection.STORY_BIBLE,
            entry_type="character", raw_line="[char_zhangsan]: 主角",
        )
        assert entry.key == "char_zhangsan"
        assert entry.parsed_fields == {}
        assert entry.tags == []
        assert entry.chapter_relevance == {}

    def test_with_fields(self):
        entry = BibleEntry(
            key="rule_001", section=BibleSection.BOOK_RULES,
            entry_type="rule", raw_line="- 必须包含爽点",
            parsed_fields={"header": "核心规则", "content": "必须包含爽点"},
            tags=["core"], created_at=12345678.0,
        )
        assert entry.parsed_fields["content"] == "必须包含爽点"
        assert "core" in entry.tags
        assert entry.created_at == 12345678.0


class TestBibleParser:
    def test_parse_empty(self):
        entries = BibleParser.parse_section("", BibleSection.STORY_BIBLE)
        assert entries == []

    def test_parse_header(self):
        text = "# 角色\n## 主角\n[char_zhangsan]: 张三，修炼天才"
        entries = BibleParser.parse_section(text, BibleSection.STORY_BIBLE)
        assert len(entries) >= 1
        entity_entry = [e for e in entries if e.key == "char_zhangsan"]
        assert len(entity_entry) == 1
        assert entity_entry[0].entry_type == "char"
        assert entity_entry[0].parsed_fields["header"] == "角色"
        assert entity_entry[0].parsed_fields["subheader"] == "主角"

    def test_parse_field(self):
        text = "## 力量体系\n**修炼境界**: 练气/筑基/金丹/元婴"
        entries = BibleParser.parse_section(text, BibleSection.STORY_BIBLE)
        fields = [e for e in entries if e.entry_type == "field"]
        assert len(fields) >= 1
        assert fields[0].parsed_fields["label"] == "修炼境界"
        assert "练气/筑基/金丹/元婴" in fields[0].parsed_fields["value"]

    def test_parse_list_item(self):
        text = "- 必须包含战斗场景"
        entries = BibleParser.parse_section(text, BibleSection.BOOK_RULES)
        assert len(entries) == 1
        assert entries[0].entry_type == "rule"
        assert entries[0].raw_line == "- 必须包含战斗场景"

    def test_parse_numbered_item(self):
        text = "1. 主角必须每次都赢"
        entries = BibleParser.parse_section(text, BibleSection.BOOK_RULES)
        assert len(entries) >= 1

    def test_parse_paragraph(self):
        text = "这是一段没有特殊标记的普通段落文本。"
        entries = BibleParser.parse_section(text, BibleSection.AUTHOR_INTENT)
        assert len(entries) >= 1
        assert entries[0].entry_type == "paragraph"


class TestStoryBible:
    def test_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                bible = StoryBible("test_bible")
                assert bible.book_id == "test_bible"
                assert bible.bible_cache_dir.exists()
                assert bible.story_dir is not None
            finally:
                cfg.settings.DATA_DIR = original

    def test_parse_all_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                bible = StoryBible("test_parse")
                result = bible.parse_all()
                assert isinstance(result, dict)
                for section in BibleSection:
                    assert result[section] == []
            finally:
                cfg.settings.DATA_DIR = original

    def test_get_overview_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                bible = StoryBible("test_overview")
                overview = bible.get_overview()
                assert overview["book_id"] == "test_overview"
                assert overview["stats"]["total_entries"] == 0
                assert "sections" in overview
            finally:
                cfg.settings.DATA_DIR = original

    def test_codex_query(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                bible = StoryBible("test_codex")
                result = bible.codex_query("角色")
                assert isinstance(result, CodexQueryResult)
                assert result.query == "角色"
            finally:
                cfg.settings.DATA_DIR = original

    def test_get_chapter_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                bible = StoryBible("test_ch_context")
                context = bible.get_chapter_context(1)
                assert context["chapter"] == 1
                assert "book_rules_active" in context
                assert "relevant_entities" in context
            finally:
                cfg.settings.DATA_DIR = original

    def test_create_workflow_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                bible = StoryBible("test_wf")
                plan = bible.create_workflow_plan(
                    "一个少年踏上修炼之路", genre="东方玄幻", target_chapters=200,
                )
                assert isinstance(plan, WorkflowPlan)
                assert plan.stage == WorkflowStage.IDEA
                assert plan.book_id == "test_wf"
                assert plan.total_chapters_planned == 200
                assert plan.genre == "东方玄幻"
            finally:
                cfg.settings.DATA_DIR = original

    def test_save_and_load_workflow_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                bible = StoryBible("test_wf_save")
                plan = bible.create_workflow_plan("测试创意")
                plan.outline_summary = ["第一章大纲", "第二章大纲"]
                plan.chapter_beats = {1: ["节拍1", "节拍2"]}
                bible.save_workflow_plan(plan)

                loaded = bible.load_workflow_plan()
                assert loaded is not None
                assert loaded.idea == "测试创意"
                assert loaded.outline_summary == ["第一章大纲", "第二章大纲"]
                assert loaded.chapter_beats == {1: ["节拍1", "节拍2"]}
            finally:
                cfg.settings.DATA_DIR = original

    def test_load_workflow_plan_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                bible = StoryBible("test_no_wf")
                assert bible.load_workflow_plan() is None
            finally:
                cfg.settings.DATA_DIR = original

    def test_advance_workflow_stage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                bible = StoryBible("test_advance")
                plan = bible.create_workflow_plan("测试")
                bible.advance_workflow_stage(plan, WorkflowStage.DRAFT)
                assert plan.stage == WorkflowStage.DRAFT

                loaded = bible.load_workflow_plan()
                assert loaded.stage == WorkflowStage.DRAFT
            finally:
                cfg.settings.DATA_DIR = original

    def test_initialize_bible_from_template(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                bible = StoryBible("test_template")
                result = bible.initialize_bible_from_template("xuanhuan_dongfang")
                assert "东方玄幻" in result
                assert "修炼境界" in result

                overview = bible.get_overview()
                assert overview["stats"]["total_entries"] > 0
            finally:
                cfg.settings.DATA_DIR = original

    def test_templates_exist(self):
        assert "xuanhuan_dongfang" in StoryBible.TEMPLATES
        assert "xianxia_xiuzhen" in StoryBible.TEMPLATES

    def test_export_codex_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                bible = StoryBible("test_export")
                bible.initialize_bible_from_template("xuanhuan_dongfang")
                exported = bible.export_codex_json()
                assert exported["book_id"] == "test_export"
                assert "entries" in exported
            finally:
                cfg.settings.DATA_DIR = original

    def test_export_for_context_injection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                bible = StoryBible("test_inject")
                bible.initialize_bible_from_template("xuanhuan_dongfang")
                result = bible.export_for_context_injection(max_entries=10)
                assert isinstance(result, str)
                assert len(result) > 0
            finally:
                cfg.settings.DATA_DIR = original


class TestWorkflowPlan:
    def test_defaults(self):
        plan = WorkflowPlan(book_id="mybook", stage=WorkflowStage.IDEA)
        assert plan.book_id == "mybook"
        assert plan.stage == WorkflowStage.IDEA
        assert plan.idea == ""
        assert plan.outline_summary == []
        assert plan.chapter_beats == {}
        assert plan.total_chapters_planned == 0


class TestCodexQueryResult:
    def test_defaults(self):
        result = CodexQueryResult(query="测试")
        assert result.query == "测试"
        assert result.matched_entries == []
        assert result.related_sections == []
        assert result.summary == ""


class TestChapterBibleChange:
    def test_defaults(self):
        change = ChapterBibleChange(
            chapter=1, section=BibleSection.STORY_BIBLE,
        )
        assert change.added == []
        assert change.modified == []
        assert change.removed == []
        assert change.summary == ""


class TestSingleton:
    def test_get_story_bible(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                b1 = get_story_bible("singleton_book")
                b2 = get_story_bible("singleton_book")
                assert b1 is b2
            finally:
                cfg.settings.DATA_DIR = original
                import kunlun.story_bible.engine as sbe_mod
                if "singleton_book" in sbe_mod._bibles:
                    del sbe_mod._bibles["singleton_book"]
