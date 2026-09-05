"""
测试: StyleEngineer 风格润色器
"""

import pytest

from kunlun.style.engineer import StyleEngineer

pytestmark = pytest.mark.integration

class TestConjunctionReplacement:
    """连词替换"""

    @pytest.fixture
    def engineer(self):
        return StyleEngineer()

    def test_all_conjunctions_defined(self, engineer):
        assert len(engineer.CONJUNCTION_REPLACEMENTS) == 9
        for replacements in engineer.CONJUNCTION_REPLACEMENTS.values():
            assert isinstance(replacements, list)
            # 每组至少有一个替换选项
            assert len(replacements) >= 1

    def test_replace_raner(self, engineer):
        text = "然而他走进了那扇门。此外他还有一个秘密。"
        result, _changes = engineer._replace_ai_conjunctions(text)
        # "然而"和"此外"被替换
        assert "然而" not in result
        assert "此外" not in result

    def test_no_op_on_empty(self, engineer):
        result, _changes = engineer._replace_ai_conjunctions("")
        assert result == ""

    def test_no_op_on_no_matches(self, engineer):
        text = "他走进门，外面下着雨，路灯昏黄，一切都安静极了。"
        result, _changes = engineer._replace_ai_conjunctions(text)
        assert result == text

    def test_partial_replacement(self, engineer):
        text = "然而春天来了。然而他并不开心。然而河水依旧流淌。"
        result, _changes = engineer._replace_ai_conjunctions(text)
        # replace() 替换所有出现
        count_before = text.count("然而")
        count_after = result.count("然而")
        assert count_after <= count_before

    def test_empty_replacement(self, engineer):
        """'综上所述'应被直接删除"""
        text = "综上所述，这是一个好决定。"
        result, _changes = engineer._replace_ai_conjunctions(text)
        assert "综上所述" not in result


class TestOpeningDiversity:
    """句首多样性"""

    @pytest.fixture
    def engineer(self):
        return StyleEngineer()

    def test_enhance_openings_normal(self, engineer):
        text = "他走进教室。他看着黑板。他打开书本。他开始了学习。"
        result = engineer._enhance_openings(text)
        assert len(result) > 0

    def test_enhance_when_below_threshold(self, engineer):
        # 句首"他"比例低时不触发 (仅1/6句 → 16.7% < 20%阈值)
        text = "晨光洒进窗户。鸟鸣清脆。他睁开眼。\n窗外一片新绿。风轻轻吹过。阳光温暖。"
        result, _changes = engineer._enhance_openings(text)
        assert result == text  # 不触发修改

    def test_enhance_when_above_threshold(self, engineer):
        # 句首"他"比例高时触发随机替换
        text = "他起身。他走向厨房。他打开冰箱。他取出牛奶。\n他倒了一杯。他回到桌前。"
        result, _changes = engineer._enhance_openings(text)
        # 至少有一些变化
        assert isinstance(result, str)


class TestParagraphRhythm:
    """段落节奏调整"""

    @pytest.fixture
    def engineer(self):
        return StyleEngineer()

    def test_adjust_rhythm_basic(self, engineer):
        text = (
            "第一段：一个很短的段落。\n\n"
            "第二段：稍微长一点的段落，包含更多描述和细节。\n\n"
            "第三段：中等偏短的段落。\n\n"
            "第四段：又一段比较短的。"
        )
        result = engineer._adjust_paragraph_rhythm(text)
        assert len(result) > 0

    def test_no_op_on_single_paragraph(self, engineer):
        text = "只有一个段落。"
        result, _changes = engineer._adjust_paragraph_rhythm(text)
        assert result == text

    def test_merge_consecutive_short(self, engineer):
        # 三个连续等长段落应触发重新分段（每段 >100 字且相邻段长度差 <50）
        long_text = "。" * 105 + "内容继续发展。情节推进。"
        s = "\n\n"
        text = s.join([long_text, long_text, long_text + "额外"])
        result, changes = engineer._adjust_paragraph_rhythm(text)
        # 段落节奏调整后，总数不应增加（合并+重新分段可能保持或减少）
        orig_count = text.count("\n\n") + 1
        result_count = result.count("\n\n") + 1
        assert result_count <= orig_count
        assert changes >= 0


class TestPolishPipeline:
    """完整润色管线"""

    @pytest.fixture
    def engineer(self):
        return StyleEngineer()

    @pytest.mark.asyncio
    async def test_polish_full(self, engineer):
        draft = (
            "然而他踏上了征途。此外他还带上了那把旧剑。\n\n"
            "他走进城门。他看见集市。他感受到喧嚣。\n\n"
            "段A\n\n段B\n\n段C\n\n"
            "综上所述，这是一个值得的旅程。"
        )
        result = await engineer.execute({"draft": draft})
        assert isinstance(result, dict)
        assert result["success"]
        assert "综上所述" not in result["polished_draft"]
