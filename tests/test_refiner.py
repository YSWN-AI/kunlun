"""文本精炼引擎测试"""

import pytest

from kunlun.style.refiner import TextRefiner, analyze_text, refine_text

pytestmark = pytest.mark.unit


class TestTextRefiner:
    def setup_method(self):
        self.refiner = TextRefiner()

    def test_analyze_normal_text(self):
        text = "王林推开门，张虎坐在椅子上喝茶。"
        report = self.refiner.analyze(text)
        assert report.total_fixes >= 0

    def test_analyze_cliche_heavy(self):
        text = "他淡淡地说：“好的。”然后缓缓地点了点头。眼神坚定无比。"
        report = self.refiner.analyze(text)
        assert report.total_fixes >= 2

    def test_refine_removes_cliches(self):
        text = "他淡淡地说：“好的。”"
        refined, report = self.refiner.refine(text)
        assert "淡淡地" not in refined
        assert report.total_fixes >= 1

    def test_empty_text(self):
        refined, _report = self.refiner.refine("")
        assert refined == ""

    def test_get_stats(self):
        stats = self.refiner.get_stats("他淡淡地说：“好的。”")
        assert "total_issues" in stats

    def test_analyze_text_shortcut(self):
        report = analyze_text("测试文本")
        assert report.original_length > 0

    def test_refine_text_shortcut(self):
        refined, _report = refine_text("他淡淡地说：“好的。”")
        assert "淡淡地" not in refined

    def test_punctuation_cleanup(self):
        refined, _report = self.refiner.refine("他说。。然后走了。。")
        assert "。。" not in refined
