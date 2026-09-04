"""
长文本分段生成与去重后处理

解决单次生成长文本时的重复问题：
1. 分段生成：每段800-1000字，传入前文摘要
2. 去重后处理：检测重复段落、重复n-gram并删除
3. 参数自适应：长文本时自动调整repetition_penalty和top_p
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from kunlun.gacha.engine import GachaEngine


@dataclass
class LongTextConfig:
    """长文本生成配置"""

    segment_chars: int = 900  # 每段目标字数
    segment_overlap: int = 100  # 段间重叠字数（用于上下文衔接）
    max_segments: int = 6  # 最大分段数
    summary_chars: int = 300  # 前文摘要字数
    repetition_penalty_long: float = 1.05  # 长文本重复惩罚
    top_p_long: float = 0.9  # 长文本top_p
    temperature_long: float = 0.8  # 长文本温度
    dedup_threshold: float = 0.7  # 段落去重相似度阈值
    min_paragraph_chars: int = 20  # 最短段落地字数


@dataclass
class SegmentResult:
    """单段生成结果"""

    index: int
    text: str
    word_count: int
    elapsed: float
    summary: str = ""


@dataclass
class LongTextResult:
    """长文本生成完整结果"""

    text: str
    segments: list[SegmentResult] = field(default_factory=list)
    total_chars: int = 0
    total_elapsed: float = 0
    dedup_removed: int = 0
    dedup_details: list[str] = field(default_factory=list)


class TextDeduplicator:
    """文本去重器"""

    @staticmethod
    def _normalize(text: str) -> str:
        """标准化文本用于比较"""
        text = re.sub(r"\s+", "", text)
        text = re.sub(r'[，。！？、；：""' "（）【】《》]", "", text)
        return text

    @staticmethod
    def _simhash(text: str, n: int = 4) -> str:
        """计算文本的simhash（简化版，用n-gram频率）"""
        normalized = TextDeduplicator._normalize(text)
        if len(normalized) < n:
            return hashlib.md5(normalized.encode()).hexdigest()
        ngrams = [normalized[i : i + n] for i in range(len(normalized) - n + 1)]
        counter = Counter(ngrams)
        # 取top 10的n-gram拼接作为hash
        top = sorted(counter.items(), key=lambda x: -x[1])[:10]
        key = "".join(ng for ng, _ in top)
        return hashlib.md5(key.encode()).hexdigest()

    @staticmethod
    def _jaccard_similarity(text1: str, text2: str, n: int = 4) -> float:
        """计算两个文本的Jaccard相似度（基于n-gram集合）"""
        norm1 = TextDeduplicator._normalize(text1)
        norm2 = TextDeduplicator._normalize(text2)
        if len(norm1) < n or len(norm2) < n:
            return 0.0
        set1 = set(norm1[i : i + n] for i in range(len(norm1) - n + 1))
        set2 = set(norm2[i : i + n] for i in range(len(norm2) - n + 1))
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def deduplicate_paragraphs(
        text: str,
        threshold: float = 0.7,
        min_chars: int = 20,
    ) -> tuple[str, int, list[str]]:
        """段落级去重

        Args:
            text: 输入文本
            threshold: 相似度阈值（超过则视为重复）
            min_chars: 最短段落地字数

        Returns:
            (去重后文本, 删除段落数, 删除详情列表)
        """
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if len(paragraphs) <= 1:
            return text, 0, []

        kept: list[str] = []
        removed_count = 0
        details: list[str] = []

        for para in paragraphs:
            if len(para) < min_chars:
                kept.append(para)
                continue

            is_duplicate = False
            for kept_para in kept[-10:]:  # 只和最近10段比较
                if len(kept_para) < min_chars:
                    continue
                sim = TextDeduplicator._jaccard_similarity(para, kept_para)
                if sim >= threshold:
                    is_duplicate = True
                    removed_count += 1
                    details.append(f"删除段落(相似度{sim:.2f}): {para[:50]}...")
                    break

            if not is_duplicate:
                kept.append(para)

        result = "\n".join(kept)
        return result, removed_count, details

    @staticmethod
    def deduplicate_ngrams(text: str, n: int = 8, max_repeat: int = 3) -> tuple[str, int]:
        """n-gram级去重（检测连续重复的短语）

        Args:
            text: 输入文本
            n: n-gram大小
            max_repeat: 最大重复次数

        Returns:
            (去重后文本, 删除重复次数)
        """
        if len(text) < n * 2:
            return text, 0

        result = []
        i = 0
        removed = 0

        while i < len(text):
            if i + n <= len(text):
                current = text[i : i + n]
                # 检查接下来是否有重复
                repeat_count = 0
                j = i + n
                while j + n <= len(text) and text[j : j + n] == current:
                    repeat_count += 1
                    j += n

                if repeat_count >= max_repeat:
                    # 只保留一次
                    result.append(current)
                    removed += repeat_count
                    i = j
                    continue

            result.append(text[i])
            i += 1

        return "".join(result), removed


class LongTextGenerator:
    """长文本分段生成器"""

    def __init__(self, engine: GachaEngine, config: LongTextConfig | None = None):
        self.engine = engine
        self.config = config or LongTextConfig()

    def _build_summary(self, text: str, max_chars: int = 300) -> str:
        """构建前文摘要（简化版：取最后几段的关键句）"""
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if not paragraphs:
            return ""

        # 取最后3段，每段取前100字
        summary_parts = []
        for para in paragraphs[-3:]:
            if len(para) > 100:
                summary_parts.append(para[:100] + "...")
            else:
                summary_parts.append(para)

        summary = "\n".join(summary_parts)
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "..."
        return summary

    def _build_segment_prompt(
        self,
        base_prompt: str,
        segment_index: int,
        total_segments: int,
        previous_text: str,
    ) -> str:
        """构建分段生成的prompt"""
        summary = self._build_summary(previous_text, self.config.summary_chars)

        segment_prompt = f"""{base_prompt}

【当前进度】第 {segment_index + 1}/{total_segments} 段
【每段要求】约 {self.config.segment_chars} 字

【前文摘要】
{summary if summary else "（开篇，无前文）"}

【写作要求】
1. 紧接前文继续，不要重复前文内容
2. 每段要有新的情节推进，不要原地踏步
3. 避免重复使用相同的句式和描写
4. 自然过渡，不要出现"接下来"、"然后"等生硬连接
5. 直接输出正文，不要输出标题或说明

请继续写作："""
        return segment_prompt

    async def generate(
        self,
        prompt: str,
        model: str = "",
        target_chars: int = 3000,
        temperature: float | None = None,
    ) -> LongTextResult:
        """生成长文本

        Args:
            prompt: 基础prompt
            model: 模型名称
            target_chars: 目标总字数
            temperature: 温度（None则用配置默认值）

        Returns:
            LongTextResult
        """
        cfg = self.config
        total_segments = min(
            max(1, target_chars // cfg.segment_chars),
            cfg.max_segments,
        )

        logger.info(
            f"LongTextGenerator: 生成长文本，目标{target_chars}字，"
            f"分{total_segments}段，每段约{cfg.segment_chars}字"
        )

        segments: list[SegmentResult] = []
        full_text = ""
        total_elapsed = 0.0

        for i in range(total_segments):
            segment_prompt = self._build_segment_prompt(
                base_prompt=prompt,
                segment_index=i,
                total_segments=total_segments,
                previous_text=full_text,
            )

            # 段落温度自适应（微笑曲线：开篇稳→发展升→高潮放→结尾收）
            seg_temp = self._get_segment_temperature(i, total_segments, temperature)

            messages = [{"role": "user", "content": segment_prompt}]

            import time

            start = time.time()
            try:
                result = await self.engine.chat(
                    messages=messages,
                    model=model,
                    temperature=seg_temp,
                    max_tokens=int(cfg.segment_chars * 2),  # token≈字*2
                )
                elapsed = time.time() - start
                segment_text = result.get("content", "").strip()

                # 清理可能的标题和说明
                segment_text = self._clean_segment(segment_text)

                segments.append(
                    SegmentResult(
                        index=i,
                        text=segment_text,
                        word_count=len(segment_text),
                        elapsed=elapsed,
                        summary=self._build_summary(segment_text, 100),
                    )
                )

                full_text += "\n" + segment_text if full_text else segment_text
                total_elapsed += elapsed

                logger.info(
                    f"  第{i + 1}/{total_segments}段完成: {len(segment_text)}字, {elapsed:.1f}秒"
                )

            except Exception as e:
                logger.error(f"  第{i + 1}段生成失败: {e}")
                segments.append(
                    SegmentResult(
                        index=i,
                        text=f"[第{i + 1}段生成失败: {e}]",
                        word_count=0,
                        elapsed=time.time() - start,
                    )
                )

        # 后处理去重
        logger.info("LongTextGenerator: 执行后处理去重...")
        dedup_text, removed_count, details = TextDeduplicator.deduplicate_paragraphs(
            full_text,
            threshold=cfg.dedup_threshold,
            min_chars=cfg.min_paragraph_chars,
        )

        # n-gram去重
        dedup_text, ngram_removed = TextDeduplicator.deduplicate_ngrams(dedup_text)
        total_removed = removed_count + ngram_removed

        logger.info(f"LongTextGenerator: 去重完成，删除{total_removed}处重复")

        return LongTextResult(
            text=dedup_text,
            segments=segments,
            total_chars=len(dedup_text),
            total_elapsed=total_elapsed,
            dedup_removed=total_removed,
            dedup_details=details,
        )

    @staticmethod
    def _get_segment_temperature(index: int, total: int, base_temp: float | None = None) -> float:
        """段落温度自适应（微笑曲线）

        开篇/设定段: 0.70（保逻辑、锚定人设）
        过渡段: 0.75（稳推进）
        高潮/中段: 0.85（放开创作张力）
        结尾段: 0.75（保闭环）
        """
        if total <= 1:
            return base_temp if base_temp is not None else 0.78
        ratio = index / (total - 1)
        if ratio < 0.25:
            return 0.70
        if ratio < 0.5:
            return 0.75
        if ratio < 0.75:
            return 0.85
        return 0.75

    @staticmethod
    def _clean_segment(text: str) -> str:
        """清理分段文本（去除标题、说明等）"""
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            # 跳过标题行（以"第X章"、"###"开头）
            if re.match(r"^第[一二三四五六七八九十\d]+[章节]", stripped):
                continue
            if stripped.startswith("#") or stripped.startswith("【"):
                continue
            # 跳过说明性文字
            if any(kw in stripped for kw in ["以下是", "继续写作", "正文如下", "字数统计"]):
                continue
            cleaned.append(line)
        return "\n".join(cleaned).strip()
