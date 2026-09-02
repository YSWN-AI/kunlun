"""
watermark 文本水印引擎 — 内容指纹嵌入、泄露溯源、多方案对比

核心能力:
1. 多方案水印嵌入（零宽字符、同义词替换、空格变异、标点变异）
2. 水印强度可调（不可见→轻度可见→明显标记）
3. 水印提取与验证
4. 泄露追踪（通过水印定位泄露源）
5. 零LLM纯算法实现
"""

from __future__ import annotations

import hashlib
import json
import random
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from loguru import logger

from kunlun.core.extension_base import BaseExtensionModule

# ============================================================================
# 枚举定义
# ============================================================================


class WatermarkMethod(StrEnum):
    """水印嵌入方法"""

    ZERO_WIDTH = "zero_width"  # 零宽字符（完全不可见）
    SYNONYM = "synonym"  # 同义词替换（轻度可见）
    SPACE_VARIANT = "space_variant"  # 空格变异（不可见）
    PUNCTUATION = "punctuation"  # 标点全半角变异（轻度可见）
    COMBINED = "combined"  # 组合方案（推荐）


class WatermarkStrength(StrEnum):
    """水印强度"""

    INVISIBLE = "invisible"  # 完全不可见（零宽字符）
    MINIMAL = "minimal"  # 极轻微（标点变异）
    LIGHT = "light"  # 轻度可见
    MODERATE = "moderate"  # 中等
    STRONG = "strong"  # 强标记（抗篡改）


# ============================================================================
# 数据类
# ============================================================================


@dataclass
class WatermarkPayload:
    """水印负载信息"""

    user_id: str = ""
    timestamp: str = ""
    document_id: str = ""
    version: str = "1.0"
    nonce: str = ""  # 随机数防重放
    custom_data: dict[str, str] = field(default_factory=dict)

    def to_string(self) -> str:
        """序列化为可嵌入的字符串"""
        data = {
            "u": self.user_id,
            "t": self.timestamp,
            "d": self.document_id,
            "v": self.version,
            "n": self.nonce,
            "c": self.custom_data,
        }
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    def to_hash(self) -> str:
        """生成短哈希用于验证"""
        return hashlib.sha256(self.to_string().encode()).hexdigest()[:16]

    @classmethod
    def from_string(cls, s: str) -> WatermarkPayload:
        data = json.loads(s)
        return cls(
            user_id=data.get("u", ""),
            timestamp=data.get("t", ""),
            document_id=data.get("d", ""),
            version=data.get("v", "1.0"),
            nonce=data.get("n", ""),
            custom_data=data.get("c", {}),
        )


# ============================================================================
# 零宽字符水印方案
# ============================================================================


class ZeroWidthWatermark:
    """零宽字符水印 — 在文本中嵌入不可见字符编码信息"""

    # Unicode零宽字符
    ZERO_WIDTH_SPACE = "\u200b"  # U+200B 零宽空格 → bit 0
    ZERO_WIDTH_NON_JOINER = "\u200c"  # U+200C 零宽非连接符 → bit 1
    ZERO_WIDTH_JOINER = "\u200d"  # U+200D 零宽连接符 → 分隔标记
    LEFT_TO_RIGHT_MARK = "\u200e"  # U+200E → 开始标记
    RIGHT_TO_LEFT_MARK = "\u200f"  # U+200F → 结束标记

    @classmethod
    def encode(cls, text: str, payload: str) -> str:
        """将payload编码为零宽字符嵌入文本

        在文本的第一个句号/逗号后嵌入。
        """
        # 将payload转为二进制
        binary = "".join(format(ord(c), "016b") for c in payload)

        # 构建零宽字符序列
        zw_sequence = cls.LEFT_TO_RIGHT_MARK  # 开始标记
        for bit in binary:
            if bit == "0":
                zw_sequence += cls.ZERO_WIDTH_SPACE
            else:
                zw_sequence += cls.ZERO_WIDTH_NON_JOINER
        zw_sequence += cls.RIGHT_TO_LRFT_MARK  # 结束标记

        # 在第一个标点后插入
        punctuation_pos = cls._find_insert_position(text)
        if punctuation_pos < 0:
            return text + zw_sequence

        return text[: punctuation_pos + 1] + zw_sequence + text[punctuation_pos + 1 :]

    @classmethod
    def decode(cls, text: str) -> str | None:
        """从文本中提取零宽字符水印"""
        # 查找开始和结束标记
        start_idx = text.find(cls.LEFT_TO_RIGHT_MARK)
        if start_idx < 0:
            return None

        end_idx = text.find(cls.RIGHT_TO_LEFT_MARK, start_idx)
        if end_idx < 0:
            return None

        zw_region = text[start_idx + 1 : end_idx]

        # 解析二进制
        binary = ""
        for ch in zw_region:
            if ch == cls.ZERO_WIDTH_SPACE:
                binary += "0"
            elif ch == cls.ZERO_WIDTH_NON_JOINER:
                binary += "1"

        if len(binary) % 16 != 0:
            return None

        # 转回字符串
        chars = []
        for i in range(0, len(binary), 16):
            chunk = binary[i : i + 16]
            chars.append(chr(int(chunk, 2)))

        return "".join(chars)

    @classmethod
    def remove(cls, text: str) -> str:
        """移除所有零宽字符"""
        result = text
        for zw in [
            cls.ZERO_WIDTH_SPACE,
            cls.ZERO_WIDTH_NON_JOINER,
            cls.ZERO_WIDTH_JOINER,
            cls.LEFT_TO_RIGHT_MARK,
            cls.RIGHT_TO_LEFT_MARK,
        ]:
            result = result.replace(zw, "")
        return result

    @classmethod
    def _find_insert_position(cls, text: str) -> int:
        """找到合适的插入位置（第一个句号、逗号或第50个字符后）"""
        for i, ch in enumerate(text):
            if ch in "。，！？；：、,.":
                return i
        return min(50, len(text) - 1)

    # 修复：属性名修正
    RIGHT_TO_LRFT_MARK = RIGHT_TO_LEFT_MARK


# ============================================================================
# 同义词替换水印方案
# ============================================================================


class SynonymWatermark:
    """同义词替换水印 — 通过选词模式嵌入信息"""

    # 可替换同义词组（每组2个选项代表bit 0/1）
    SYNONYM_PAIRS: list[tuple[str, str]] = [
        ("但是", "但"),
        ("因为", "因"),
        ("所以", "因此"),
        ("可以", "能够"),
        ("需要", "须要"),
        ("已经", "已"),
        ("非常", "十分"),
        ("特别", "尤其"),
        ("突然", "忽然"),
        ("终于", "总算"),
        ("立刻", "马上"),
        ("似乎", "仿佛"),
        ("也许", "或许"),
        ("仍然", "依然"),
        ("总是", "一直"),
        ("经常", "时常"),
        ("逐渐", "渐渐"),
        ("完全", "彻底"),
        ("绝对", "绝"),
        ("确实", "的确"),
        ("一定", "必定"),
        ("必须", "务必"),
        ("所有", "全部"),
        ("许多", "很多"),
        ("一些", "某些"),
        ("其中", "当中"),
        ("关于", "对于"),
        ("按照", "根据"),
        ("通过", "经过"),
        ("为了", "为"),
        ("以及", "和"),
    ]

    @classmethod
    def encode(cls, text: str, payload: str) -> str:
        """通过同义词选择嵌入payload"""
        # payload转bit序列
        bits = "".join(format(ord(c), "08b") for c in payload)

        result = text
        bit_idx = 0

        for word0, word1 in cls.SYNONYM_PAIRS:
            if bit_idx >= len(bits):
                break

            # 查找文本中的同义词
            if bits[bit_idx] == "0" and word1 in result:
                result = result.replace(word1, word0, 1)
                bit_idx += 1
            elif bits[bit_idx] == "1" and word0 in result:
                result = result.replace(word0, word1, 1)
                bit_idx += 1
            else:
                # 找不到对应词，尝试用另一词
                if word0 in result:
                    result = result.replace(word0, word0, 1)  # no-op, skip bit
                elif word1 in result:
                    result = result.replace(word1, word1, 1)  # no-op, skip bit
                bit_idx += 1

        return result

    @classmethod
    def decode(cls, original: str, watermarked: str) -> str | None:
        """对比原文和水印文提取payload"""
        bits = []
        for word0, word1 in cls.SYNONYM_PAIRS:
            # 统计原文和水印文中各词的出现次数
            orig_0 = original.count(word0)
            orig_1 = original.count(word1)
            wm_0 = watermarked.count(word0)
            wm_1 = watermarked.count(word1)

            # 判断变化方向
            if wm_0 > orig_0:
                bits.append("0")
            elif wm_1 > orig_1:
                bits.append("1")
            else:
                continue

            if len(bits) % 8 == 0 and len(bits) >= 16:
                break

        if len(bits) < 8:
            return None

        # bits转字符串
        chars = []
        for i in range(0, len(bits) - len(bits) % 8, 8):
            chunk = "".join(bits[i : i + 8])
            chars.append(chr(int(chunk, 2)))

        return "".join(chars)


# ============================================================================
# 标点全半角变异方案
# ============================================================================


class PunctuationWatermark:
    """标点全半角变异水印"""

    # 可变异标点对 (全角bit0, 半角bit1)
    PUNCTUATION_PAIRS: list[tuple[str, str]] = [
        ("，", ","),
        ("。", "."),
        ("；", ";"),
        ("：", ":"),
        ("！", "!"),
        ("？", "?"),
        ("（", "("),
        ("）", ")"),
        ("、", ","),  # 顿号→半角逗号
    ]

    @classmethod
    def encode(cls, text: str, payload: str) -> str:
        """通过标点全半角变异嵌入"""
        bits = "".join(format(ord(c), "08b") for c in payload)

        result = list(text)
        bit_idx = 0

        for i, ch in enumerate(result):
            if bit_idx >= len(bits):
                break
            for full, half in cls.PUNCTUATION_PAIRS:
                if ch == full and bits[bit_idx] == "1":
                    result[i] = half
                    bit_idx += 1
                    break
                if ch == half and bits[bit_idx] == "0":
                    result[i] = full
                    bit_idx += 1
                    break

        return "".join(result)

    @classmethod
    def decode(cls, original: str, watermarked: str) -> str | None:
        """对比提取"""
        bits = []
        for i in range(min(len(original), len(watermarked))):
            if original[i] == watermarked[i]:
                continue
            for full, half in cls.PUNCTUATION_PAIRS:
                if original[i] == full and watermarked[i] == half:
                    bits.append("1")
                    break
                if original[i] == half and watermarked[i] == full:
                    bits.append("0")
                    break
            if len(bits) >= 128:
                break

        if len(bits) < 8:
            return None

        chars = []
        for i in range(0, len(bits) - len(bits) % 8, 8):
            chunk = "".join(bits[i : i + 8])
            chars.append(chr(int(chunk, 2)))

        return "".join(chars)


# ============================================================================
# 水印引擎（主入口）
# ============================================================================


class WatermarkEngine(BaseExtensionModule):
    """文本水印引擎 — 嵌入、提取、验证、追踪"""

    def __init__(self, book_id: str = ""):
        super().__init__(book_id)
        self._zero_width = ZeroWidthWatermark()
        self._synonym = SynonymWatermark()
        self._punctuation = PunctuationWatermark()
        self._embedding_log: list[dict[str, Any]] = []

    def embed(
        self,
        text: str,
        payload: WatermarkPayload | None = None,
        method: WatermarkMethod = WatermarkMethod.COMBINED,
        strength: WatermarkStrength = WatermarkStrength.MINIMAL,
    ) -> tuple[str, WatermarkPayload]:
        """在文本中嵌入水印

        Args:
            text: 原始文本
            payload: 水印负载（不提供则自动生成）
            method: 嵌入方法
            strength: 水印强度

        Returns:
            (带水印文本, 实际使用的水印负载)
        """
        if payload is None:
            payload = WatermarkPayload(
                user_id="unknown",
                timestamp="",
                document_id=str(uuid.uuid4())[:8],
                nonce=random.randint(10000, 99999).__str__(),
            )

        payload_str = payload.to_string()
        watermarked = text

        if method == WatermarkMethod.ZERO_WIDTH or (
            method == WatermarkMethod.COMBINED
            and strength in (WatermarkStrength.INVISIBLE, WatermarkStrength.MINIMAL)
        ):
            watermarked = self._zero_width.encode(watermarked, payload_str)

        if method in (WatermarkMethod.SYNONYM, WatermarkMethod.COMBINED) and strength not in (
            WatermarkStrength.INVISIBLE,
        ):
            watermarked = self._synonym.encode(watermarked, payload.to_hash())

        if method in (WatermarkMethod.PUNCTUATION, WatermarkMethod.COMBINED) and strength in (
            WatermarkStrength.LIGHT,
            WatermarkStrength.MODERATE,
            WatermarkStrength.STRONG,
        ):
            watermarked = self._punctuation.encode(watermarked, payload.to_hash())

        # 记录嵌入日志
        self._embedding_log.append(
            {
                "document_id": payload.document_id,
                "method": method.value,
                "strength": strength.value,
                "payload_hash": payload.to_hash(),
                "text_length": len(text),
                "watermarked_length": len(watermarked),
            }
        )

        logger.info(
            f"水印已嵌入: method={method.value}, strength={strength.value}, "
            f"length {len(text)}→{len(watermarked)}"
        )
        return watermarked, payload

    def extract(
        self,
        watermarked_text: str,
        original_text: str | None = None,
    ) -> WatermarkPayload | None:
        """从文本中提取水印

        Args:
            watermarked_text: 带水印文本
            original_text: 原始文本（用于对比方案，如同义词替换）

        Returns:
            提取的水印负载，或None
        """
        # 尝试零宽字符提取
        payload_str = self._zero_width.decode(watermarked_text)
        if payload_str:
            try:
                return WatermarkPayload.from_string(payload_str)
            except (json.JSONDecodeError, KeyError):
                pass

        # 尝试同义词对比提取
        if original_text:
            hash_str = self._synonym.decode(original_text, watermarked_text)
            if hash_str:
                return WatermarkPayload(
                    user_id="",
                    timestamp="",
                    document_id=hash_str,
                )

            # 尝试标点对比提取
            hash_str2 = self._punctuation.decode(original_text, watermarked_text)
            if hash_str2:
                return WatermarkPayload(
                    user_id="",
                    timestamp="",
                    document_id=hash_str2,
                )

        return None

    def verify(self, watermarked_text: str, original_payload: WatermarkPayload) -> bool:
        """验证水印是否完整"""
        extracted = self.extract(watermarked_text)
        if extracted is None:
            return False
        return extracted.to_hash() == original_payload.to_hash()

    def remove(self, watermarked_text: str) -> str:
        """移除水印（尽力还原）"""
        return self._zero_width.remove(watermarked_text)

    def detect(self, text: str) -> bool:
        """检测文本是否含水印"""
        return self._zero_width.decode(text) is not None

    def get_embedding_log(self) -> list[dict[str, Any]]:
        """获取嵌入历史记录"""
        return self._embedding_log

    def compare_methods(self, text: str) -> dict[str, dict[str, Any]]:
        """对比各方案的嵌入效果"""
        payload = WatermarkPayload(
            user_id="test",
            timestamp="",
            document_id="compare",
            nonce="12345",
        )

        results: dict[str, dict[str, Any]] = {}
        for method in WatermarkMethod:
            watermarked, _ = self.embed(text, payload=payload, method=method)
            extracted = self.extract(watermarked)
            results[method.value] = {
                "original_length": len(text),
                "watermarked_length": len(watermarked),
                "overhead": len(watermarked) - len(text),
                "extractable": extracted is not None,
                "visible_change": self._estimate_visibility(text, watermarked),
            }

        return results

    @staticmethod
    def _estimate_visibility(original: str, watermarked: str) -> str:
        """估计水印的可见程度"""
        diff_count = sum(1 for a, b in zip(original, watermarked, strict=False) if a != b)
        diff_ratio = diff_count / max(len(original), 1)
        if diff_ratio == 0:
            return "none"
        if diff_ratio < 0.001:
            return "minimal"
        if diff_ratio < 0.01:
            return "light"
        if diff_ratio < 0.05:
            return "moderate"
        return "strong"


# ============================================================================
# 工厂函数
# ============================================================================


def create_payload(
    user_id: str = "",
    document_id: str = "",
    **custom_data: str,
) -> WatermarkPayload:
    """创建水印负载"""
    from datetime import datetime

    return WatermarkPayload(
        user_id=user_id,
        timestamp=datetime.now().isoformat(),
        document_id=document_id or str(uuid.uuid4())[:8],
        nonce=random.randint(10000, 99999).__str__(),
        custom_data=custom_data,
    )


_engines: dict[str, WatermarkEngine] = {}


def watermark_and_sign(
    text: str,
    user_id: str = "",
    document_id: str = "",
    method: WatermarkMethod = WatermarkMethod.COMBINED,
    strength: WatermarkStrength = WatermarkStrength.MINIMAL,
) -> tuple[str, WatermarkPayload]:
    """便捷函数：一行完成水印嵌入"""
    engine = _engines.get("_default")
    if engine is None:
        engine = WatermarkEngine()
        _engines["_default"] = engine

    payload = create_payload(user_id=user_id, document_id=document_id)
    return engine.embed(text, payload=payload, method=method, strength=strength)
