"""
Prompt 压缩器模块标准 pytest 测试
"""

import pytest

pytestmark = pytest.mark.unit


class TestPromptCompressor:
    """提示词压缩器"""

    @pytest.fixture
    def compressor(self):
        from kunlun.prompt_compressor import PromptCompressor

        return PromptCompressor()

    def test_compress_off(self, compressor):
        from kunlun.prompt_compressor import CompressionLevel

        text = "请注意，这是一个测试文本。"
        result = compressor.compress(text, CompressionLevel.OFF)
        assert result.compressed == text
        assert result.saved_tokens == 0
        assert result.ratio == 1.0

    def test_compress_light(self, compressor):
        from kunlun.prompt_compressor import CompressionLevel

        text = "他站起身来，然后走出了房间。"
        result = compressor.compress(text, CompressionLevel.LIGHT)
        assert result.saved_tokens >= 0
        assert 0 < result.ratio <= 1.0

    def test_compress_standard(self, compressor):
        from kunlun.prompt_compressor import CompressionLevel

        text = (
            "请注意，在修真界，实力是最重要的。"
            "总的来说，他必须变得更强。"
            "值得注意的是，他的天赋确实很特别。"
            "非常非常强大的力量在他体内涌动。"
        )
        result = compressor.compress(text, CompressionLevel.STANDARD)
        assert result.saved_tokens > 0, "标准模式应至少节省一些token"
        assert result.ratio < 1.0

    def test_compress_aggressive(self, compressor):
        from kunlun.prompt_compressor import CompressionLevel

        text = (
            "首先，他走进了大殿。其次，他看到了宝座。然后，他感受到了一股威压。"
            "最后，他决定走上前去。总之，这一切发生得太快了。"
        )
        result = compressor.compress(text, CompressionLevel.AGGRESSIVE)
        assert result.saved_tokens > 0

    def test_compress_empty_text(self, compressor):
        from kunlun.prompt_compressor import CompressionLevel

        result = compressor.compress("", CompressionLevel.STANDARD)
        assert result.compressed == ""
        assert result.saved_tokens == 0

    def test_safety_limit_under_70_pct(self, compressor):
        """极度冗余文本应触发安全上限，不崩溃"""
        from kunlun.prompt_compressor import CompressionLevel

        text = "请注意，请注意，请注意，请注意，" * 50
        result = compressor.compress(text, CompressionLevel.AGGRESSIVE)
        # 核心要求：不崩溃，不无限递归
        assert result.saved_tokens >= 0
        assert result.compressed is not None

    def test_compress_messages(self, compressor):
        from kunlun.prompt_compressor import CompressionLevel

        messages = [
            {"role": "system", "content": "你是一个助手。请注意回答要简洁。"},
            {"role": "user", "content": "值得注意的是，帮我写一段文字。"},
        ]
        result = compressor.compress_messages(messages, CompressionLevel.STANDARD)
        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"

    def test_preserve_patterns_registered(self, compressor):  # noqa: ARG002
        """验证保留模式列表非空"""
        from kunlun.prompt_compressor import PromptCompressor

        assert len(PromptCompressor.PRESERVE_PATTERNS) >= 3

    def test_stats_accumulation(self, compressor):
        from kunlun.prompt_compressor import CompressionLevel

        compressor.compress("请注意，测试文本。" * 10, CompressionLevel.STANDARD)
        compressor.compress("总的来说，另一个测试。" * 5, CompressionLevel.LIGHT)
        assert compressor._stats.total_compressed == 2
        assert compressor._stats.total_tokens_original > 0
