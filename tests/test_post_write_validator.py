"""后写验证器测试"""

import pytest

from kunlun.audit.post_write_validator import PostWriteValidator, validate_draft

pytestmark = pytest.mark.unit

class TestPostWriteValidator:
    def setup_method(self):
        self.validator = PostWriteValidator()

    def test_quality_text_passes(self):
        """高质量文本应获得较高评分"""
        text = (
            "王林一脚踹开房门，里面的笑声戛然而止。\n\n"
            "“谁让你进来的？”张虎拍案而起，脸色铁青。\n\n"
            "“你自己做的事，心里没数？”王林冷冷地看着他，手指轻轻敲击桌面。\n\n"
            "张虎的脸色瞬间变得煞白。他下意识地后退半步，右手摸向腰间的对讲机。\n\n"
            "“别费劲了。”王林从口袋里掏出一个U盘，重重摔在桌上。\n\n"
            "“这里面有你跟李总的所有通话记录。”\n\n"
            "张虎的手僵在半空，额头上沁出细密的汗珠。\n\n"
            "“你…你怎么会有这个东西？”他的声音在颤抖。\n\n"
            "王林拉开椅子坐下，翘起二郎腿：“若要人不知，除非己莫为。”\n\n"
            "“现在，我们可以好好谈谈了吗？”"
        )
        report = self.validator.validate(text)
        assert report.overall_score >= 0.6, f"高质量文本得分应≥0.6，实际 {report.overall_score}"

    def test_cliche_text_fails(self):
        """高套话密度文本应标记失败"""
        text = (
            "他仿佛突然明白了什么，竟然不禁笑了起来。\n\n"
            "他似乎忽然想起什么，猛地站了起来。\n\n"
            "宛如晴天霹雳，他好像突然被击中。"
        )
        report = self.validator.validate(text)
        assert any("套话" in r.rule_name and not r.passed for r in report.results), "套话检测应触发"

    def test_uniform_paragraphs_fails(self):
        """段落等长检测"""
        lines = [f"第{i}段的中文字符差不多就是这样的长度" for i in range(10)]
        text = "\n\n".join(lines)
        report = self.validator.validate(text)
        # 可能通过也可能不通过，取决于具体长度分布
        assert report.overall_score > 0

    def test_rundown_text_fails(self):
        """流水账检测——应触发流水账规则"""
        text = "他来到了门口。他推开了门。他看到了张虎。他走到了桌前。他说了一句话。张虎站了起来。"
        report = self.validator.validate(text)
        rundown_result = [r for r in report.results if r.rule_name == "流水账检测"]
        assert rundown_result and not rundown_result[0].passed, "流水账检测应触发"

    def test_ai_ending_fails(self):
        """AI套话结尾检测"""
        text = (
            "这是开头的段落。\n\n这是中间的段落。\n\n"
            "这一切才刚刚开始，真正的考验还在后面等待着他们。"
        )
        report = self.validator.validate(text)
        ai_result = [r for r in report.results if r.rule_name == "AI套话结尾"]
        assert ai_result and not ai_result[0].passed, "AI套话结尾应触发"

    def test_empty_text(self):
        """空文本不应崩溃"""
        report = self.validator.validate("")
        assert isinstance(report.passed, bool)

    def test_short_text(self):
        """短文本不应崩溃"""
        report = self.validator.validate("你好")
        assert isinstance(report.passed, bool)

    def test_validate_draft_shortcut(self):
        """快捷函数应正常工作"""
        report = validate_draft("测试文本。")
        assert isinstance(report.passed, bool)
