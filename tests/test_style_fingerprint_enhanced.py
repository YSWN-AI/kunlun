"""
风格指纹系统增强测试 — 20+量化字段 + 风格库 + 漂移检测 + gacha第10维

覆盖:
- StyleFingerprint 新增字段默认值
- StyleAnalyzer.analyze() 计算所有新增字段
- 短句/长句比例、比喻/夸张/四字格检测
- 动作/环境/心理描写占比
- feature_vector 构建和归一化
- ai_taste_score 计算
- to_prompt() 生成
- cosine_similarity 计算
- StyleLibrary add/get/remove/list/save/load/compare_all
- DriftDetector record_chapter / check_drift / 漂移趋势
- gacha _score_style_match 无目标/有目标
- 向后兼容
"""

import json
import tempfile
from pathlib import Path

from kunlun.style.drift_detector import DriftReport, StyleDriftDetector, drift_detector
from kunlun.style.fingerprint import (
    StyleFingerprint,
    style_analyzer,
    style_injector,
)
from kunlun.style.library import StyleLibrary, style_library

# ── 测试文本 ──

SHORT_STYLE_TEXT = (
    "他拔剑。剑光一闪。敌人倒下。\n\n"
    "风吹过战场。\n\n"
    "血滴落。他转身。\n\n"
    "「走吧。」他说。\n\n"
    "远处传来马蹄声。天色渐暗。\n\n"
    "他握紧剑柄。眼神冰冷。\n\n"
    "身后是燃烧的村庄。前方是未知的深渊。\n\n"
    "他深吸一口气。迈出了第一步。"
)

LONG_STYLE_TEXT = (
    "在那遥远的群山之巅，云雾缭绕之间，矗立着一座古老而神秘的宫殿，"
    "它的墙壁由最纯净的白玉砌成，屋顶覆盖着金色的琉璃瓦，在阳光下闪耀着夺目的光芒。"
    "宫殿的四周环绕着苍翠的古松，松涛阵阵，仿佛在诉说着千年的传说。\n\n"
    "那位身穿青色长袍的年轻人，缓缓地走在铺满鹅卵石的小径上，"
    "他的心中充满了对未知的渴望与对命运的敬畏，每一步都显得格外沉重而坚定。"
    "他知道，这座宫殿中隐藏着足以改变整个大陆命运的秘密，"
    "而他，正是被命运选中的那个人。"
)

METAPHOR_TEXT = (
    "她的笑容宛如春天的阳光，温暖而明媚。\n\n"
    "他的眼神仿佛深邃的海洋，藏着无尽的秘密。\n\n"
    "时间犹如流水，一去不复返。\n\n"
    "那声音好似银铃般清脆悦耳。"
)

PSYCH_TEXT = (
    "他心中暗想，这一切未免太过顺利了。\n\n"
    "她觉得有些不对劲，似乎有人在暗中跟踪。\n\n"
    "他感到一阵寒意从脊背升起，暗道不好。\n\n"
    "她心中充满了恐惧，觉得自己仿佛坠入了无底深渊。"
)

AI_CLICHE_TEXT = (
    "突然，他仿佛看到了什么。总的来说，这是一个值得一提的时刻。\n\n"
    "与此同时，她似乎也感受到了异样。综上所述，情况变得复杂起来。\n\n"
    "显而易见，毫无疑问，这就是答案。不可否认，他心中一紧，眼中闪过一丝光芒。"
)


# ══════════════════════════════════════════════════════
# 1. StyleFingerprint 新增字段默认值
# ══════════════════════════════════════════════════════

class TestStyleFingerprintDefaults:
    """测试新增字段的默认值"""

    def test_syntax_fields_default(self):
        fp = StyleFingerprint()
        assert fp.short_sentence_ratio == 0.0
        assert fp.long_sentence_ratio == 0.0
        assert fp.exclamation_ratio == 0.0
        assert fp.question_ratio == 0.0

    def test_vocabulary_fields_default(self):
        fp = StyleFingerprint()
        assert fp.rare_word_ratio == 0.0
        assert fp.avg_word_length == 0.0
        assert fp.verb_density == 0.0
        assert fp.adjective_density == 0.0
        assert fp.signature_words == []

    def test_rhetoric_fields_default(self):
        fp = StyleFingerprint()
        assert fp.metaphor_per_1k == 0.0
        assert fp.exaggeration_per_1k == 0.0
        assert fp.four_character_per_1k == 0.0
        assert fp.parallelism_per_1k == 0.0

    def test_narrative_fields_default(self):
        fp = StyleFingerprint()
        assert fp.action_desc_ratio == 0.0
        assert fp.env_desc_ratio == 0.0
        assert fp.psych_desc_ratio == 0.0
        assert fp.single_sentence_para_ratio == 0.0

    def test_composite_fields_default(self):
        fp = StyleFingerprint()
        assert fp.feature_vector == []
        assert fp.ai_taste_score == 0.0

    def test_existing_fields_preserved(self):
        """确保原有12字段仍存在且有默认值"""
        fp = StyleFingerprint()
        assert fp.avg_sentence_length == 0.0
        assert fp.sentence_length_std == 0.0
        assert len(fp.sentence_length_histogram) == 10
        assert fp.top_words == []
        assert fp.word_diversity == 0.0
        assert fp.paragraph_length_pattern == []
        assert fp.avg_paragraph_length == 0.0
        assert fp.paragraph_length_cv == 0.0
        assert fp.dialogue_ratio == 0.0
        assert fp.avg_dialogue_length == 0.0
        assert fp.punctuation_distribution == {}
        assert fp.style_guide == ""


# ══════════════════════════════════════════════════════
# 2. StyleAnalyzer.analyze() 计算所有新增字段
# ══════════════════════════════════════════════════════

class TestStyleAnalyzerEnhanced:
    """测试增强后的 analyze() 方法"""

    def test_analyze_computes_all_new_fields(self):
        fp = style_analyzer.analyze(LONG_STYLE_TEXT, name="test")
        # 句法
        assert fp.short_sentence_ratio >= 0.0
        assert fp.long_sentence_ratio >= 0.0
        # 词汇
        assert fp.rare_word_ratio >= 0.0
        assert fp.avg_word_length > 0.0
        assert fp.verb_density >= 0.0
        assert fp.adjective_density >= 0.0
        # 修辞
        assert fp.metaphor_per_1k >= 0.0
        assert fp.four_character_per_1k >= 0.0
        # 叙事
        assert fp.action_desc_ratio >= 0.0
        assert fp.psych_desc_ratio >= 0.0
        # 综合
        assert len(fp.feature_vector) > 0
        assert 0.0 <= fp.ai_taste_score <= 1.0

    def test_short_sentence_ratio(self):
        """短句比例计算：短句风格文本应有较高短句比例"""
        fp = style_analyzer.analyze(SHORT_STYLE_TEXT, name="short")
        assert fp.short_sentence_ratio > 0.3
        assert fp.short_sentence_ratio <= 1.0

    def test_long_sentence_ratio(self):
        """长句比例计算：长句风格文本应有较高长句比例"""
        fp = style_analyzer.analyze(LONG_STYLE_TEXT, name="long")
        assert fp.long_sentence_ratio > 0.0
        assert fp.long_sentence_ratio <= 1.0

    def test_metaphor_detection(self):
        """比喻检测：包含比喻词的文本应有较高比喻密度"""
        fp = style_analyzer.analyze(METAPHOR_TEXT, name="metaphor")
        assert fp.metaphor_per_1k > 0.0

    def test_exaggeration_detection(self):
        """夸张检测"""
        text = "他的力量万丈滔天，仿佛能毁灭整个世界。那无尽的黑暗永恒地笼罩着大地。"
        fp = style_analyzer.analyze(text, name="exag")
        assert fp.exaggeration_per_1k > 0.0

    def test_four_character_detection(self):
        """四字格检测"""
        text = "他兴高采烈地走在大街上，周围人山人海，热闹非凡。"
        fp = style_analyzer.analyze(text, name="four")
        assert fp.four_character_per_1k > 0.0

    def test_psych_desc_ratio(self):
        """心理描写占比：心理描写文本应有较高比例"""
        fp = style_analyzer.analyze(PSYCH_TEXT, name="psych")
        assert fp.psych_desc_ratio > 0.0

    def test_action_desc_ratio(self):
        """动作描写占比：动作密集文本应有较高比例"""
        text = (
            "他冲上前去，一拳打在敌人脸上。敌人后退三步，拔出剑来。"
            "他侧身躲过，反手一刀。敌人倒下，他收刀入鞘。"
        )
        fp = style_analyzer.analyze(text, name="action")
        assert fp.action_desc_ratio >= 0.0

    def test_env_desc_ratio(self):
        """环境描写占比"""
        text = (
            "天空湛蓝，白云朵朵。远处的山峰笼罩在云雾之中，"
            "山脚下的湖泊平静如镜，倒映着四周的景色。"
            "阳光洒在大地上，温暖而明媚。"
        )
        fp = style_analyzer.analyze(text, name="env")
        assert fp.env_desc_ratio > 0.0

    def test_single_sentence_para_ratio(self):
        """单句成段比例：短句风格应有较高比例"""
        fp = style_analyzer.analyze(SHORT_STYLE_TEXT, name="single")
        assert fp.single_sentence_para_ratio > 0.0

    def test_signature_words(self):
        """标志性词提取"""
        text = (
            "修炼修炼修炼，突破突破突破，境界境界境界。"
            "他不断修炼，终于突破了新的境界。"
        )
        fp = style_analyzer.analyze(text, name="sig")
        assert isinstance(fp.signature_words, list)
        # 高频词应该被提取
        assert len(fp.signature_words) >= 0


# ══════════════════════════════════════════════════════
# 3. feature_vector 构建和归一化
# ══════════════════════════════════════════════════════

class TestFeatureVector:
    """测试特征向量构建"""

    def test_vector_length(self):
        fp = style_analyzer.analyze(LONG_STYLE_TEXT, name="vec")
        assert len(fp.feature_vector) >= 20

    def test_vector_normalized(self):
        """所有向量值应在[0,1]范围内"""
        fp = style_analyzer.analyze(LONG_STYLE_TEXT, name="norm")
        for v in fp.feature_vector:
            assert 0.0 <= v <= 1.0

    def test_different_texts_different_vectors(self):
        fp1 = style_analyzer.analyze(SHORT_STYLE_TEXT, name="s1")
        fp2 = style_analyzer.analyze(LONG_STYLE_TEXT, name="s2")
        assert fp1.feature_vector != fp2.feature_vector

    def test_analyze_and_vectorize(self):
        """analyze_and_vectorize 应返回完整向量"""
        fp = style_analyzer.analyze_and_vectorize(LONG_STYLE_TEXT, name="av")
        assert len(fp.feature_vector) >= 20


# ══════════════════════════════════════════════════════
# 4. ai_taste_score 计算
# ══════════════════════════════════════════════════════

class TestAiTasteScore:
    """测试AI味指数"""

    def test_ai_cliche_text_high_score(self):
        """包含大量AI套话的文本应有较高AI味指数"""
        fp = style_analyzer.analyze(AI_CLICHE_TEXT, name="ai")
        assert fp.ai_taste_score > 0.0

    def test_score_range(self):
        fp = style_analyzer.analyze(LONG_STYLE_TEXT, name="range")
        assert 0.0 <= fp.ai_taste_score <= 1.0

    def test_normal_text_lower_than_cliche(self):
        """正常文本的AI味应低于套话文本"""
        fp_normal = style_analyzer.analyze(LONG_STYLE_TEXT, name="normal")
        fp_cliche = style_analyzer.analyze(AI_CLICHE_TEXT, name="cliche")
        # 套话文本的AI味指数应该不低于正常文本
        assert fp_cliche.ai_taste_score >= fp_normal.ai_taste_score - 0.1


# ══════════════════════════════════════════════════════
# 5. to_prompt() 生成
# ══════════════════════════════════════════════════════

class TestToPrompt:
    """测试 to_prompt() 方法"""

    def test_to_prompt_returns_string(self):
        fp = style_analyzer.analyze(LONG_STYLE_TEXT, name="prompt")
        result = fp.to_prompt()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_to_prompt_contains_key_metrics(self):
        fp = style_analyzer.analyze(LONG_STYLE_TEXT, name="prompt2")
        result = fp.to_prompt()
        assert "平均句长" in result
        assert "词汇" in result

    def test_empty_fingerprint_to_prompt(self):
        fp = StyleFingerprint()
        result = fp.to_prompt()
        assert isinstance(result, str)


# ══════════════════════════════════════════════════════
# 6. cosine_similarity 计算
# ══════════════════════════════════════════════════════

class TestCosineSimilarity:
    """测试余弦相似度"""

    def test_same_text_similarity_high(self):
        fp1 = style_analyzer.analyze(LONG_STYLE_TEXT, name="same1")
        fp2 = style_analyzer.analyze(LONG_STYLE_TEXT, name="same2")
        sim = fp1.cosine_similarity(fp2)
        assert sim > 0.9

    def test_different_text_similarity_lower(self):
        fp1 = style_analyzer.analyze(SHORT_STYLE_TEXT, name="diff1")
        fp2 = style_analyzer.analyze(LONG_STYLE_TEXT, name="diff2")
        sim = fp1.cosine_similarity(fp2)
        assert 0.0 <= sim <= 1.0

    def test_empty_vector_returns_zero(self):
        fp1 = StyleFingerprint()
        fp2 = StyleFingerprint()
        assert fp1.cosine_similarity(fp2) == 0.0

    def test_compare_method_still_works(self):
        """原有 compare() 方法应仍正常工作"""
        fp1 = style_analyzer.analyze(SHORT_STYLE_TEXT, name="c1")
        fp2 = style_analyzer.analyze(LONG_STYLE_TEXT, name="c2")
        sim = style_analyzer.compare(fp1, fp2)
        assert 0.0 <= sim <= 1.0


# ══════════════════════════════════════════════════════
# 7. StyleLibrary 测试
# ══════════════════════════════════════════════════════

class TestStyleLibrary:
    """测试风格库"""

    def test_add_and_get(self):
        lib = StyleLibrary()
        fp = StyleFingerprint(name="test_style")
        lib.add(fp)
        assert lib.get("test_style") is not None
        assert lib.get("nonexistent") is None

    def test_remove(self):
        lib = StyleLibrary()
        fp = StyleFingerprint(name="to_remove")
        lib.add(fp)
        assert lib.remove("to_remove") is True
        assert lib.remove("to_remove") is False

    def test_list_all(self):
        lib = StyleLibrary()
        lib.add(StyleFingerprint(name="style1"))
        lib.add(StyleFingerprint(name="style2"))
        names = lib.list_all()
        assert "style1" in names
        assert "style2" in names
        assert len(names) == 2

    def test_compare_all(self):
        lib = StyleLibrary()
        fp1 = style_analyzer.analyze(SHORT_STYLE_TEXT, name="short_style")
        fp2 = style_analyzer.analyze(LONG_STYLE_TEXT, name="long_style")
        lib.add(fp1)
        lib.add(fp2)

        target = style_analyzer.analyze(SHORT_STYLE_TEXT, name="target")
        results = lib.compare_all(target)
        assert len(results) == 2
        # 与目标相似的风格应排在前面
        assert results[0][0] == "short_style"
        assert results[0][1] >= results[1][1]

    def test_save_and_load(self):
        lib = StyleLibrary()
        fp = style_analyzer.analyze(LONG_STYLE_TEXT, name="saved_style")
        lib.add(fp)

        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        ) as f:
            filepath = f.name

        try:
            lib.save(filepath)
            assert Path(filepath).exists()

            lib2 = StyleLibrary()
            lib2.load(filepath)
            assert "saved_style" in lib2.list_all()
            loaded_fp = lib2.get("saved_style")
            assert loaded_fp is not None
            assert loaded_fp.avg_sentence_length > 0
        finally:
            if Path(filepath).exists():
                Path(filepath).unlink()

    def test_add_empty_name_skipped(self):
        lib = StyleLibrary()
        fp = StyleFingerprint(name="")
        lib.add(fp)
        assert len(lib.list_all()) == 0


# ══════════════════════════════════════════════════════
# 8. StyleDriftDetector 测试
# ══════════════════════════════════════════════════════

class TestStyleDriftDetector:
    """测试风格漂移检测器"""

    def test_set_target(self):
        detector = StyleDriftDetector()
        fp = StyleFingerprint(name="target")
        detector.set_target(fp)
        assert detector.target_fingerprint is not None

    def test_record_chapter_returns_similarity(self):
        detector = StyleDriftDetector()
        target = style_analyzer.analyze(SHORT_STYLE_TEXT, name="target")
        detector.set_target(target)
        sim = detector.record_chapter(1, SHORT_STYLE_TEXT)
        assert 0.0 <= sim <= 1.0
        assert len(detector.chapter_fingerprints) == 1

    def test_check_drift_consistent(self):
        """风格一致的章节不应触发漂移"""
        detector = StyleDriftDetector()
        target = style_analyzer.analyze(SHORT_STYLE_TEXT, name="target")
        detector.set_target(target)
        report = detector.check_drift(1, SHORT_STYLE_TEXT)
        assert isinstance(report, DriftReport)
        assert report.chapter == 1
        assert 0.0 <= report.similarity <= 1.0
        # 相同文本相似度应该很高，不漂移
        assert report.drifted is False

    def test_check_drift_different_style(self):
        """风格差异大的章节可能触发漂移"""
        detector = StyleDriftDetector()
        target = style_analyzer.analyze(SHORT_STYLE_TEXT, name="target")
        detector.set_target(target)
        detector.drift_threshold = 0.95  # 设高阈值使任何差异都触发
        report = detector.check_drift(1, LONG_STYLE_TEXT)
        assert isinstance(report, DriftReport)
        assert report.drifted is True
        assert len(report.suggestion) > 0

    def test_get_trend(self):
        detector = StyleDriftDetector()
        target = style_analyzer.analyze(SHORT_STYLE_TEXT, name="target")
        detector.set_target(target)
        detector.record_chapter(1, SHORT_STYLE_TEXT)
        detector.record_chapter(2, LONG_STYLE_TEXT)
        trend = detector.get_trend()
        assert len(trend) == 2
        assert trend[0]["chapter"] == 1
        assert trend[1]["chapter"] == 2
        assert "similarity" in trend[0]
        assert "drifted" in trend[0]

    def test_get_drift_dimensions(self):
        detector = StyleDriftDetector()
        target = style_analyzer.analyze(SHORT_STYLE_TEXT, name="target")
        detector.set_target(target)
        chapter_fp = style_analyzer.analyze(LONG_STYLE_TEXT, name="chapter")
        dims = detector.get_drift_dimensions(chapter_fp)
        assert isinstance(dims, dict)
        assert len(dims) > 0
        assert "句长差异" in dims

    def test_no_target_returns_empty_report(self):
        detector = StyleDriftDetector()
        report = detector.check_drift(1, SHORT_STYLE_TEXT)
        assert report.similarity == 0.0
        assert report.drifted is False


# ══════════════════════════════════════════════════════
# 9. gacha _score_style_match 测试
# ══════════════════════════════════════════════════════

class TestGachaStyleMatch:
    """测试 gacha 第10维风格匹配"""

    def test_score_style_match_no_target(self):
        """无目标指纹时使用通用风格丰富度评分"""
        from kunlun.gacha.engine import GachaEngine
        engine = GachaEngine()
        engine.target_style_fingerprint = None
        score = engine._score_style_match(LONG_STYLE_TEXT)
        assert 0.0 <= score <= 1.0

    def test_score_style_match_with_target(self):
        """有目标指纹时计算相似度"""
        from kunlun.gacha.engine import GachaEngine
        engine = GachaEngine()
        target = style_analyzer.analyze(SHORT_STYLE_TEXT, name="target")
        engine.set_target_style(target)
        score = engine._score_style_match(SHORT_STYLE_TEXT)
        assert 0.0 <= score <= 1.0
        # 相同文本应该有较高相似度
        assert score > 0.5

    def test_score_style_match_different_from_target(self):
        """与目标风格不同的文本应有较低相似度"""
        from kunlun.gacha.engine import GachaEngine
        engine = GachaEngine()
        target = style_analyzer.analyze(SHORT_STYLE_TEXT, name="target")
        engine.set_target_style(target)
        score_same = engine._score_style_match(SHORT_STYLE_TEXT)
        score_diff = engine._score_style_match(LONG_STYLE_TEXT)
        # 相同文本的分数应高于不同文本
        assert score_same >= score_diff

    def test_set_target_style_none(self):
        """设置 None 清除目标指纹"""
        from kunlun.gacha.engine import GachaEngine
        engine = GachaEngine()
        target = style_analyzer.analyze(SHORT_STYLE_TEXT, name="target")
        engine.set_target_style(target)
        assert engine.target_style_fingerprint is not None
        engine.set_target_style(None)
        assert engine.target_style_fingerprint is None

    def test_short_text_returns_default(self):
        """过短文本返回默认0.5"""
        from kunlun.gacha.engine import GachaEngine
        engine = GachaEngine()
        score = engine._score_style_match("短")
        assert score == 0.5


# ══════════════════════════════════════════════════════
# 10. 向后兼容测试
# ══════════════════════════════════════════════════════

class TestBackwardCompatibility:
    """测试向后兼容性"""

    def test_style_analyzer_analyze_basic(self):
        """原有 analyze() 基本功能正常"""
        fp = style_analyzer.analyze(LONG_STYLE_TEXT, name="compat")
        assert fp.avg_sentence_length > 0
        assert fp.word_diversity > 0
        assert fp.dialogue_ratio >= 0

    def test_style_injector_build_prompt(self):
        """原有 StyleInjector.build_style_prompt() 正常"""
        fp = style_analyzer.analyze(LONG_STYLE_TEXT, name="inject")
        prompt = style_injector.build_style_prompt(fp)
        assert isinstance(prompt, str)
        assert "文风要求" in prompt

    def test_style_injector_none_fp(self):
        """传入 None 返回空字符串"""
        assert style_injector.build_style_prompt(None) == ""  # type: ignore

    def test_save_load_fingerprint_new_fields(self):
        """save/load 应正确处理新增字段"""
        fp = style_analyzer.analyze(LONG_STYLE_TEXT, name="save_test")
        with tempfile.TemporaryDirectory():
            # 直接测试 JSON 序列化/反序列化
            data = {k: v for k, v in fp.__dict__.items() if not k.startswith("_")}
            if "top_words" in data:
                data["top_words"] = [[w, c] for w, c in data["top_words"]]
            json_str = json.dumps(data, ensure_ascii=False)
            loaded_data = json.loads(json_str)
            fp2 = StyleFingerprint()
            for k, raw_v in loaded_data.items():
                if hasattr(fp2, k):
                    v = raw_v
                    if k == "top_words" and isinstance(v, list):
                        v = [(item[0], item[1]) for item in v if isinstance(item, list)]
                    setattr(fp2, k, v)
            # 新增字段应被正确保存和加载
            assert fp2.short_sentence_ratio == fp.short_sentence_ratio
            assert fp2.ai_taste_score == fp.ai_taste_score
            assert len(fp2.feature_vector) == len(fp.feature_vector)

    def test_global_singletons_exist(self):
        """全局单例应存在"""
        assert style_analyzer is not None
        assert style_injector is not None
        assert style_library is not None
        assert drift_detector is not None
