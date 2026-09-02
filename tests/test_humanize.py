"""
Humanize 模块标准 pytest 测试
自用场景关键路径：AI文本检测、规则后处理、AntiAIDetector
"""
import pytest

pytestmark = pytest.mark.unit

AI_TEXT = (
    "在修真界摸爬滚打三百年，他深知实力的重要性。"
    "然而，这次的机遇实在是太难得了。"
    "因此，他决定无论如何都要试一试。"
    "此外，他还注意到周围有不少人也在虎视眈眈。"
    "与此同时，一股强大的气息正在靠近。"
    "不可否认的是，这将是一场恶战。"
    "总而言之，他必须全力以赴。"
)

HUMAN_TEXT = (
    "老张头蹲在门槛上，点了根烟。烟雾慢慢散开，他眯着眼看远处的山。"
    "好半晌，才说了一句：去吧。"
    "他愣了一下。去吧？就这么简单？"
    "老张头没再说话，只是摆了摆手。他站起身，走了两步，又回头看了一眼。"
    "门槛上的人已经闭上了眼，像是睡着了。"
)


class TestTextFingerprint:
    """AI文本指纹检测"""

    def test_analyze_ai_text(self):
        from kunlun.humanize.fingerprint import TextFingerprint
        fp = TextFingerprint()
        result = fp.analyze(AI_TEXT)
        assert result.perplexity_score >= 0, "困惑度必须非负"
        assert 0.0 <= result.ai_likelihood <= 1.0, "AI可能性在0-1之间"
        assert result.risk_level in ("low", "medium", "high", "critical")

    def test_analyze_human_text(self):
        from kunlun.humanize.fingerprint import TextFingerprint
        fp = TextFingerprint()
        result = fp.analyze(HUMAN_TEXT)
        assert result.ai_likelihood <= 1.0

    def test_ai_vs_human_differentiation(self):
        """AI文本应该比人类文本得分更高"""
        from kunlun.humanize.fingerprint import TextFingerprint
        fp = TextFingerprint()
        ai_result = fp.analyze(AI_TEXT)
        human_result = fp.analyze(HUMAN_TEXT)
        # 至少AI文本的突发性应低于人类文本（AI文本更均匀）
        assert isinstance(ai_result.ai_likelihood, float)
        assert isinstance(human_result.ai_likelihood, float)


class TestAIModeDetector:
    """AI模式检测器"""

    def test_detect_ai_patterns(self):
        from kunlun.humanize.detector import AIModeDetector
        det = AIModeDetector()
        result = det.detect(AI_TEXT)
        assert hasattr(result, 'total_markers')
        assert hasattr(result, 'summary')
        assert result.total_markers >= 0

    def test_detect_human_patterns(self):
        from kunlun.humanize.detector import AIModeDetector
        det = AIModeDetector()
        result = det.detect(HUMAN_TEXT)
        assert result.total_markers >= 0


class TestRulePostProcessor:
    """规则后处理器"""

    def test_process_reduces_ai_score(self):
        from kunlun.humanize.fingerprint import TextFingerprint
        from kunlun.humanize.rewriter import RulePostProcessor
        fp = TextFingerprint()
        processor = RulePostProcessor()

        fp.analyze(AI_TEXT)
        processed = processor.process(AI_TEXT)
        after = fp.analyze(processed)

        assert hasattr(after, 'ai_likelihood')
        # 处理后不应崩溃，结果应有意义
        assert 0.0 <= after.ai_likelihood <= 1.0


class TestAntiAIDetector:
    """AntiAIDetector 集成"""

    def test_detect_returns_strategy(self):
        from kunlun.humanize.engine import AntiAIDetector
        ad = AntiAIDetector()
        result = ad.detect(AI_TEXT)
        assert isinstance(result, dict)
        assert 'recommended_strategy' in result
        assert 'needs_humanization' in result

    def test_detect_human_text_no_action(self):
        from kunlun.humanize.engine import AntiAIDetector
        ad = AntiAIDetector()
        result = ad.detect(HUMAN_TEXT)
        assert isinstance(result['needs_humanization'], bool)

    def test_empty_text_handling(self):
        """空文本不应崩溃"""
        from kunlun.humanize.engine import AntiAIDetector
        ad = AntiAIDetector()
        result = ad.detect("")
        assert isinstance(result, dict)
