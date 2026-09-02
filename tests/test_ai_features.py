"""AI 特征库测试"""

import pytest

from kunlun.audit.ai_features import (
    AI_FEATURES,
    calculate_ai_score,
    get_feature_names,
    get_features_by_category,
    scan_text,
)

pytestmark = pytest.mark.unit


class TestAIFeatures:
    def test_feature_count(self):
        """至少24个特征"""
        assert len(AI_FEATURES) >= 24, f"只有 {len(AI_FEATURES)} 个特征，期望≥24"

    def test_categories_covered(self):
        """覆盖所有5个分类"""
        cats = {f.category for f in AI_FEATURES}
        for expected in ("词汇", "句法", "结构", "修辞", "格式"):
            assert expected in cats, f"缺少分类: {expected}"

    def test_human_text_low_score(self):
        """人类叙事文本的AI特征得分应为中等以上"""
        text = (
            "放我出去！王林拼命砸门，拳头砸在铁板上发出沉闷的响声。"
            "没人应。走廊里只有他自己的回音，一遍遍地回荡。"
            "他靠着墙滑坐下来，大口大口喘着粗气。手上的血已经干了，指甲缝里全是灰。"
            "有人叫他。他猛地抬头，看见铁门上开了一个巴掌大的小窗。"
            "你他妈谁啊？王林撑着墙站起来。"
            "那张脸咧嘴笑了——救你出去的人。别废话，退后。"
            "铁锁哗啦一声掉在地上。门开了。走廊里的灯光刺得他睁不开眼。"
            "那人说完转身就走，步伐很快。王林顾不上多想，拔腿跟了上去。"
            "他不知道这人是谁，也不知道要去哪。但他知道，留下来就是死路一条。"
        )
        score = calculate_ai_score(text)
        assert score > 0.3, f"人类叙事文本应得分>0.3，实际 {score}"

    def test_ai_text_high_score(self):
        """AI写作文本应得分接近0"""
        text = (
            "首先，值得注意的是，这个故事的发展过程具有一定的复杂性。"
            "因此，我们需要从多个角度来进行分析。"
            "此外，人物性格的塑造也值得我们深入探讨。"
            "综上所述，这个故事展现出了丰富的内涵。"
            "总的来说，这是一个值得细细品味的作品。"
        ) * 10  # 重复10次以达到最低长度要求
        score = calculate_ai_score(text)
        assert score < 0.5, f"AI文本得分应<0.5，实际 {score}"

    def test_scan_text(self):
        """扫描应返回特征命中列表"""
        hits = scan_text("值得注意的是，综上所述，这确实是一个问题。")
        assert len(hits) > 0
        names = [h["name"] for h in hits]
        assert "A5_总结词" in names or "A4_递进连词" in names

    def test_get_features_by_category(self):
        vocab = get_features_by_category("词汇")
        assert len(vocab) >= 5

    def test_get_feature_names(self):
        names = get_feature_names()
        assert len(names) >= 24
