"""写作质量看板测试"""

import pytest

from kunlun.quality import QualityDashboard

pytestmark = pytest.mark.unit


class TestQualityDashboard:
    def test_analyze_short_text(self):
        """短文本应返回中性结果"""
        report = QualityDashboard.analyze_chapter("短", chapter=1)
        assert report.quality_rating == "文本过短"

    def test_analyze_empty_text(self):
        report = QualityDashboard.analyze_chapter("", chapter=1)
        assert report.quality_rating == "文本过短"

    def test_analyze_quality_text(self):
        """高质量文本应得分较高"""
        draft = (
            "王林一脚踹开房门。张虎拍案而起：“谁让你进来的？”\n\n"
            "王林把U盘扔在桌上：“自己听。”\n\n"
            "张虎盯着U盘，脸色变了。他伸手去拿，手指在颤抖。\n\n"
            "“这东西你从哪里弄来的？”\n\n"
            "“若要人不知，除非己莫为。”王林转身就走。"
        )
        report = QualityDashboard.analyze_chapter(draft, chapter=1)
        assert report.overall_score > 0
        assert report.quality_rating in ("优秀", "良好", "一般", "较差")

    def test_analyze_ai_text(self):
        """AI风格文本得分应较低"""
        draft = (
            "首先，值得注意的是，这个故事的发展过程具有一定的复杂性。"
            "因此，我们需要从多个角度来进行分析。"
        ) * 30
        report = QualityDashboard.analyze_chapter(draft, chapter=2)
        assert report.ai_score < 0.5

    def test_analyze_with_token_usage(self):
        """Token使用率应影响报告"""
        report = QualityDashboard.analyze_chapter("测试文本。" * 30, chapter=3, token_usage=0.95)
        assert report.token_budget_usage == 0.95
        assert len(report.warnings) > 0

    def test_to_dict(self):
        """报告可序列化为dict"""
        report = QualityDashboard.analyze_chapter("测试" * 50, chapter=4)
        d = report.to_dict()
        assert "quality_rating" in d
        assert "overall_score" in d
        assert "issues" in d

    def test_compare_chapters(self):
        """批量比较功能"""
        drafts = {
            1: "高质量文本。" * 20,
            2: "首先，值得注意的是。" * 30,
        }
        results = QualityDashboard.compare_chapters(drafts)
        assert len(results) == 2
        assert 1 in results
        assert 2 in results
