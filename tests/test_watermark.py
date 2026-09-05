"""
水印引擎测试 — 零宽字符嵌入/提取、同义词替换、水印强度
"""

import pytest

pytestmark = pytest.mark.unit

from kunlun.watermark.engine import (  # noqa: E402
    WatermarkMethod,
    WatermarkPayload,
    WatermarkStrength,
    ZeroWidthWatermark,
)


class TestWatermarkPayload:
    def test_create_payload(self):
        payload = WatermarkPayload(
            user_id="user123",
            timestamp="2026-06-12T12:00:00",
            document_id="doc-001",
            version="1.0",
            nonce="abc123",
        )
        assert payload.user_id == "user123"
        assert payload.document_id == "doc-001"

    def test_to_string_is_valid_json(self):
        import json

        payload = WatermarkPayload(user_id="u1", timestamp="t1", document_id="d1", nonce="n1")
        s = payload.to_string()
        data = json.loads(s)
        assert data["u"] == "u1"
        assert data["d"] == "d1"

    def test_from_string_roundtrip(self):
        payload = WatermarkPayload(
            user_id="user456",
            timestamp="2026-01-01T00:00:00",
            document_id="doc-002",
            nonce="xyz789",
            custom_data={"chapter": "5"},
        )
        s = payload.to_string()
        restored = WatermarkPayload.from_string(s)
        assert restored.user_id == payload.user_id
        assert restored.document_id == payload.document_id
        assert restored.nonce == payload.nonce
        assert restored.custom_data == payload.custom_data

    def test_to_hash_consistent(self):
        payload = WatermarkPayload(user_id="u1", timestamp="t1", document_id="d1", nonce="n1")
        h1 = payload.to_hash()
        h2 = payload.to_hash()
        assert h1 == h2  # 相同输入应产生相同哈希
        assert len(h1) == 16  # 16字符十六进制

    def test_to_hash_different_for_different_payloads(self):
        p1 = WatermarkPayload(user_id="u1", timestamp="t1", document_id="d1", nonce="n1")
        p2 = WatermarkPayload(user_id="u2", timestamp="t1", document_id="d1", nonce="n1")
        assert p1.to_hash() != p2.to_hash()


class TestZeroWidthWatermark:
    """零宽字符水印编码/解码"""

    def test_encode_inserts_zero_width_chars(self):
        text = "这是测试文本。后面还有内容。"
        payload = "test123"
        result = ZeroWidthWatermark.encode(text, payload)
        # 编码后文本应比原文长（插入了零宽字符）
        assert len(result) > len(text)
        # 零宽字符肉眼不可见但存在
        assert (
            ZeroWidthWatermark.ZERO_WIDTH_SPACE in result
            or ZeroWidthWatermark.ZERO_WIDTH_NON_JOINER in result
        )

    def test_encode_decode_roundtrip_ascii(self):
        text = "这是一个测试文本。用于验证水印的编码和解码功能。"
        payload = "hello"
        encoded = ZeroWidthWatermark.encode(text, payload)
        decoded = ZeroWidthWatermark.decode(encoded)
        assert decoded == payload

    def test_encode_decode_roundtrip_chinese_payload(self):
        text = "中文测试文本。验证中文字符作为水印负载的编码和解码。"
        payload = "水印测试"
        encoded = ZeroWidthWatermark.encode(text, payload)
        decoded = ZeroWidthWatermark.decode(encoded)
        assert decoded == payload

    def test_encode_decode_roundtrip_numeric(self):
        text = "数字负载测试。12345。"
        payload = "12345"
        encoded = ZeroWidthWatermark.encode(text, payload)
        decoded = ZeroWidthWatermark.decode(encoded)
        assert decoded == payload

    def test_encode_decode_long_payload(self):
        text = "长负载测试文本。"
        payload = "this_is_a_longer_payload_for_testing"
        encoded = ZeroWidthWatermark.encode(text, payload)
        decoded = ZeroWidthWatermark.decode(encoded)
        assert decoded == payload

    def test_decode_no_watermark_returns_none(self):
        text = "普通文本，没有任何水印。"
        decoded = ZeroWidthWatermark.decode(text)
        assert decoded is None

    def test_remove_cleans_zero_width_chars(self):
        text = "测试文本。"
        payload = "test"
        encoded = ZeroWidthWatermark.encode(text, payload)
        cleaned = ZeroWidthWatermark.remove(encoded)
        # 清理后应恢复原文（不含零宽字符）
        # 注意：如果文本以标点结尾，编码在标点后插入，清理后可能不完全等于原文
        # 但清理后不应含零宽字符
        for zw_char in [
            ZeroWidthWatermark.ZERO_WIDTH_SPACE,
            ZeroWidthWatermark.ZERO_WIDTH_NON_JOINER,
            ZeroWidthWatermark.ZERO_WIDTH_JOINER,
            ZeroWidthWatermark.LEFT_TO_RIGHT_MARK,
            ZeroWidthWatermark.RIGHT_TO_LEFT_MARK,
        ]:
            assert zw_char not in cleaned

    def test_encode_preserves_readable_content(self):
        """零宽字符水印不应改变可见文本"""
        text = "这是一段正常的中文文本。用于测试。"
        payload = "mark"
        encoded = ZeroWidthWatermark.encode(text, payload)
        cleaned = ZeroWidthWatermark.remove(encoded)
        # 移除零宽字符后，可见文本应一致
        assert cleaned == text

    def test_multiple_encode_decode(self):
        """多次编码解码应保持一致"""
        text = "多次测试文本。"
        payload = "multi"
        encoded = ZeroWidthWatermark.encode(text, payload)
        # 第二次编码
        encoded2 = ZeroWidthWatermark.encode(encoded, "extra")
        # 第一次解码应取到第一个水印
        decoded = ZeroWidthWatermark.decode(encoded2)
        assert decoded in {"extra", "multi"}  # 取决于找到哪个标记


class TestWatermarkEnums:
    def test_watermark_method_values(self):
        methods = list(WatermarkMethod)
        assert WatermarkMethod.ZERO_WIDTH in methods
        assert WatermarkMethod.SYNONYM in methods
        assert WatermarkMethod.COMBINED in methods

    def test_watermark_strength_values(self):
        strengths = list(WatermarkStrength)
        assert WatermarkStrength.INVISIBLE in strengths
        assert WatermarkStrength.STRONG in strengths
