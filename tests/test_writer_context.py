"""
测试Writer上下文动态压缩 (Writer Context ReIO)
"""
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

from kunlun.writer_context import (
    ChapterMemory,
    ChapterRanker,
    ContextAssembler,
    ContextAssembly,
    ContextBudgetType,
    RetentionPriority,
    SnippetExtractor,
    WriterContextManager,
    get_writer_context_manager,
)


class TestRetentionPriority:
    def test_enum_values(self):
        assert RetentionPriority.CRITICAL.value == "critical"
        assert RetentionPriority.HIGH.value == "high"
        assert RetentionPriority.MEDIUM.value == "medium"
        assert RetentionPriority.LOW.value == "low"
        assert RetentionPriority.EXPIRED.value == "expired"


class TestChapterMemory:
    def test_default_values(self):
        mem = ChapterMemory(chapter=1)
        assert mem.chapter == 1
        assert mem.full_text == ""
        assert mem.word_count == 0
        assert mem.key_snippets == []
        assert mem.entities_mentioned == []
        assert mem.foreshadowing_planted == []
        assert mem.foreshadowing_resolved == []
        assert mem.retention == RetentionPriority.MEDIUM
        assert mem.surprise_score == 0.0
        assert mem.emotion_peak is False

    def test_with_data(self):
        mem = ChapterMemory(
            chapter=5, full_text="测试章节内容", word_count=2000,
            key_snippets=["片段1", "片段2"], entities_mentioned=["主角", "张三"],
            plot_threads=["主线"], foreshadowing_planted=["伏笔1"],
            retention=RetentionPriority.HIGH, surprise_score=0.8,
            emotion_peak=True, chapter_title="高潮",
        )
        assert mem.word_count == 2000
        assert len(mem.key_snippets) == 2
        assert "主角" in mem.entities_mentioned
        assert len(mem.foreshadowing_planted) == 1
        assert mem.retention == RetentionPriority.HIGH


class TestSnippetExtractor:
    def test_extract_empty_text(self):
        mem = SnippetExtractor.extract("", 1)
        assert mem.chapter == 1
        assert mem.word_count == 0
        assert mem.key_snippets == []

    def test_extract_short_text(self):
        mem = SnippetExtractor.extract("这是一个简单的测试段落，没有特殊内容。", 1)
        assert mem.chapter == 1
        assert mem.word_count > 0
        assert mem.retention in [RetentionPriority.LOW, RetentionPriority.MEDIUM]

    def test_extract_conflict_text(self):
        text = (
            "主角遭遇围攻，敌人从四面八方杀来。战斗异常激烈，鲜血染红了大地。"
            "敌人发动致命一击，主角重伤倒地。但就在这危急时刻，主角突然突破！"
            "阴谋被揭露，背叛者终于现出原形。"
        ) * 3
        mem = SnippetExtractor.extract(text, 3)
        assert mem.key_snippets  # 应提取到冲突相关片段
        assert mem.retention in [RetentionPriority.MEDIUM, RetentionPriority.HIGH, RetentionPriority.CRITICAL]

    def test_extract_pleasure_text(self):
        text = (
            "众人震惊地看着主角突破到新境界。主角一拳打出，碾压所有对手。"
            "这个消息轰动全城，主角一朝成名！所有人都为他的逆袭而欢呼。"
            "这是主角的又一次打脸，对手们颜面无存。"
        ) * 3
        mem = SnippetExtractor.extract(text, 5)
        assert mem.key_snippets  # 应提取到爽点相关片段
        assert mem.retention in [RetentionPriority.MEDIUM, RetentionPriority.HIGH, RetentionPriority.CRITICAL]

    def test_extract_emotion_peak(self):
        text = "主角仰天长啸，欣喜若狂地发现自己获得了无上机缘。"
        mem = SnippetExtractor.extract(text, 10)
        assert mem.emotion_peak is True

    def test_extract_foreshadowing(self):
        text = "主角隐隐感到一丝不安，似乎有什么不妙的事情即将发生。他当时还不知道这意味着什么。"
        mem = SnippetExtractor.extract(text, 2)
        assert len(mem.foreshadowing_planted) >= 1

    def test_extract_surprise(self):
        text = "主角竟然发现了一个惊人的秘密，原来他的师父居然是隐藏的大反派！"
        mem = SnippetExtractor.extract(text, 7)
        assert mem.surprise_score > 0


class TestChapterRanker:
    def test_rank_empty(self):
        result = ChapterRanker.rank(5, {})
        assert result == []

    def test_rank_basic(self):
        mem1 = ChapterMemory(
            chapter=1, word_count=500,
            entities_mentioned=["主角", "张三"],
            retention=RetentionPriority.MEDIUM,
        )
        mem2 = ChapterMemory(
            chapter=4, word_count=600,
            entities_mentioned=["主角"],
            retention=RetentionPriority.HIGH,
            emotion_peak=True,
        )
        memories = {1: mem1, 4: mem2}
        ranked = ChapterRanker.rank(5, memories, current_entities=["主角"])
        assert len(ranked) == 2
        assert ranked[0][0] == 4

    def test_rank_with_plot_threads(self):
        mem = ChapterMemory(
            chapter=2, word_count=400,
            plot_threads=["主线", "支线1"],
            retention=RetentionPriority.MEDIUM,
        )
        ranked = ChapterRanker.rank(3, {2: mem}, current_plot_threads=["主线"])
        assert len(ranked) == 1
        assert ranked[0][1] > 0


class TestContextAssembler:
    def test_init(self):
        assembler = ContextAssembler()
        assert assembler.max_chars == 8000
        assert assembler.max_tokens_est == 3000

    def test_initialize_with_custom_budget(self):
        assembler = ContextAssembler(max_chars=4000, max_tokens_est=1500)
        assert assembler.max_chars == 4000

    def test_assemble_empty(self):
        assembler = ContextAssembler(max_chars=2000)
        result = assembler.assemble(1, {}, "hint")
        assert isinstance(result, ContextAssembly)
        assert result.target_chapter == 1
        assert "hint" in result.assembled_text

    def test_assemble_with_memories(self):
        text_para = "这是一段足够长的测试文本。" * 50
        mem1 = ChapterMemory(
            chapter=1, full_text=text_para,
            key_snippets=["关键片段A"], retention=RetentionPriority.CRITICAL,
            emotion_peak=True, foreshadowing_planted=["伏笔1"],
        )
        mem2 = ChapterMemory(
            chapter=2, full_text=text_para,
            key_snippets=["片段B"], retention=RetentionPriority.HIGH,
        )
        mem3 = ChapterMemory(
            chapter=3, full_text=text_para,
            key_snippets=["片段C"], retention=RetentionPriority.LOW,
        )
        memories = {1: mem1, 2: mem2, 3: mem3}
        assembler = ContextAssembler(max_chars=10000)
        result = assembler.assemble(4, memories)
        assert result.target_chapter == 4
        assert result.total_chars > 0
        assert isinstance(result.stats, dict)

    def test_assemble_for_budget(self):
        mem = ChapterMemory(
            chapter=1, full_text="测试文本" * 20,
            key_snippets=["片段"], retention=RetentionPriority.HIGH,
        )
        assembler = ContextAssembler()
        result = assembler.assemble_for_budget(
            2, {1: mem}, _budget_type=ContextBudgetType.CHARACTERS, budget_value=1000,
        )
        assert isinstance(result, ContextAssembly)

    def test_context_assembly_fields(self):
        assembly = ContextAssembly(target_chapter=5)
        assert assembly.full_text_chapters == []
        assert assembly.summary_chapters == []
        assert assembly.dropped_chapters == []
        assert assembly.assembled_text == ""


class TestWriterContextManager:
    def test_init_with_temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                mgr = WriterContextManager("test_book")
                assert mgr.book_id == "test_book"
                assert mgr.context_dir.exists()
            finally:
                cfg.settings.DATA_DIR = original

    def test_register_chapter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                mgr = WriterContextManager("test_book")
                text = "主角踏入了修炼之门，开始了他漫长的修行之路。"
                mem = mgr.register_chapter(1, text)
                assert mem.chapter == 1
                assert mem.word_count == len(text)
                assert isinstance(mem, ChapterMemory)
            finally:
                cfg.settings.DATA_DIR = original

    def test_build_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                mgr = WriterContextManager("test_book2")
                text = "这是一个充满冲突的激烈战斗场景。" * 30
                mgr.register_chapter(1, text, entities=["主角"], plot_threads=["主线"])
                ctx = mgr.build_context(2, "写作提示", max_chars=5000)
                assert isinstance(ctx, ContextAssembly)
                assert ctx.target_chapter == 2
                assert "写作提示" in ctx.assembled_text
            finally:
                cfg.settings.DATA_DIR = original

    def test_mark_chapters_expired(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                mgr = WriterContextManager("test_book3")
                mgr.register_chapter(1, "第一章内容")
                mgr.mark_chapters_expired([1])
                mem = mgr.get_memory(1)
                assert mem.retention == RetentionPriority.EXPIRED
            finally:
                cfg.settings.DATA_DIR = original

    def test_get_memory_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                mgr = WriterContextManager("test_book4")
                assert mgr.get_memory(999) is None
            finally:
                cfg.settings.DATA_DIR = original

    def test_get_statistics_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                mgr = WriterContextManager("test_book5")
                stats = mgr.get_statistics()
                assert stats["total_chapters"] == 0
            finally:
                cfg.settings.DATA_DIR = original

    def test_get_statistics_with_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                mgr = WriterContextManager("test_book6")
                mgr.register_chapter(1, "内容1")
                mgr.register_chapter(2, "内容2" * 50)
                stats = mgr.get_statistics()
                assert stats["total_chapters"] == 2
                assert "by_priority" in stats
                assert stats["avg_word_count"] > 0
            finally:
                cfg.settings.DATA_DIR = original

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                mgr1 = WriterContextManager("test_book_persist")
                mgr1.register_chapter(1, "第一章内容测试", entities=["主角"])
                assert mgr1.get_memory(1) is not None

                mgr2 = WriterContextManager("test_book_persist")
                mem = mgr2.get_memory(1)
                assert mem is not None
                assert mem.chapter == 1
            finally:
                cfg.settings.DATA_DIR = original
                import kunlun.writer_context.__init__ as wc_mod
                wc_mod._managers.clear()


class TestSingleton:
    def test_get_writer_context_manager(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import kunlun.config as cfg
            original = cfg.settings.DATA_DIR
            cfg.settings.DATA_DIR = Path(tmpdir)

            try:
                mgr1 = get_writer_context_manager("singleton_book")
                mgr2 = get_writer_context_manager("singleton_book")
                assert mgr1 is mgr2

                mgr3 = get_writer_context_manager("other_book")
                assert mgr1 is not mgr3
            finally:
                cfg.settings.DATA_DIR = original
                import kunlun.writer_context.__init__ as wc_mod
                if "singleton_book" in wc_mod._managers:
                    del wc_mod._managers["singleton_book"]
                if "other_book" in wc_mod._managers:
                    del wc_mod._managers["other_book"]
