"""
AI文本统计指纹分析与对抗优化

理论基础（基于业界顶级研究 + AI检测器原理）：
  - Perplexity（困惑度）: AI文本可预测性高 → 低困惑度(5-15)，人类文本不可预测 → 高困惑度(30-150+)
  - Burstiness（突发性）: AI文本句子间困惑度均匀 → 低突发性，人类文本波动大 → 高突发性
  - 句子长度方差: AI文本句子长度均匀，人类文本变化大
  - N-gram 重复度: AI文本有固定的词汇搭配模式
  - 功能词/实词比: AI文本功能词占比偏高
  - 段落结构模板: AI文本开头/结尾遵循固定模式

参考开源项目:
  - Binoculars (GitHub): GPT-2 双模型困惑度检测
  - RoBERTa 分类器: 微调的AI/Human文本分类器
  - humanize-text 的检测反馈循环

用法:
    fingerprint = TextFingerprint()
    result = fingerprint.analyze(text)
    print(f"困惑度: {result.perplexity_score:.1f}, 突发性: {result.burstiness:.3f}")
    optimized = fingerprint.optimize(text, target_burstiness=0.45)
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class FingerprintResult:
    """文本统计指纹分析结果"""

    # 核心指标
    perplexity_score: float = 0.0  # 近似困惑度 (基于bigram/trigram概率)
    burstiness: float = 0.0  # 突发性 (句子间困惑度变异系数)
    sentence_length_cv: float = 0.0  # 句子长度变异系数

    # 辅助指标
    avg_sentence_len: float = 0.0  # 平均句长
    sentence_lengths: list[int] = field(default_factory=list)
    unique_word_ratio: float = 0.0  # 唯一词比例
    function_word_ratio: float = 0.0  # 功能词占比
    ngram_repetition: float = 0.0  # n-gram重复度
    paragraph_structure_score: float = 0.0  # 段落结构模板化程度

    # 判定
    ai_likelihood: float = 0.0  # AI生成可能性 (0-1)
    is_suspicious: bool = False  # 是否可疑
    risk_level: str = "low"  # low / medium / high

    # 详细信息
    per_sentence_scores: list[dict] = field(default_factory=list)
    flagged_segments: list[str] = field(default_factory=list)


@dataclass
class BurstinessProfile:
    """突发性优化配置"""

    target_burstiness: float = 0.45  # 目标突发性 (人类文本通常在0.35-0.60)
    min_sentence_len: int = 3  # 最小句子长度
    max_sentence_len: int = 80  # 最大句子长度（中文）
    target_cv: float = 0.55  # 目标句子长度变异系数
    merge_threshold: int = 6  # 合并短句阈值
    split_threshold: int = 50  # 拆分长句阈值


# ═══════════════════════════════════════════════════════
# 中文功能词列表 (AI文本中占比通常偏高)
# ═══════════════════════════════════════════════════════

CHINESE_FUNCTION_WORDS = {
    "的",
    "了",
    "在",
    "是",
    "有",
    "和",
    "与",
    "或",
    "但",
    "而",
    "也",
    "就",
    "都",
    "还",
    "却",
    "便",
    "才",
    "又",
    "再",
    "更",
    "很",
    "最",
    "太",
    "好",
    "真",
    "多",
    "少",
    "大",
    "小",
    "不",
    "这",
    "那",
    "哪",
    "什么",
    "怎么",
    "怎样",
    "如何",
    "为什么",
    "因为",
    "所以",
    "虽然",
    "但是",
    "如果",
    "即使",
    "除非",
    "只有",
    "可以",
    "应该",
    "必须",
    "可能",
    "能够",
    "需要",
    "会",
    "要",
    "把",
    "被",
    "让",
    "给",
    "对",
    "从",
    "向",
    "往",
    "到",
    "着",
    "过",
    "得",
    "地",
    "之",
    "以",
    "所",
    "则",
    "且",
    "乃",
    "者",
    "乎",
    "哉",
    "焉",
    "耳",
    "矣",
    "一个",
    "一种",
    "一次",
    "一些",
    "一点",
    "一定",
    "一样",
    "这个",
    "那个",
    "这些",
    "那些",
    "这里",
    "那里",
    "这样",
    "那样",
}


class TextFingerprint:
    """
    AI文本统计指纹分析器

    零LLM成本，纯统计计算。
    基于 AI 检测器的核心原理（perplexity、burstiness、句子长度方差）构建。

    使用场景：
      - 生成后检测：评估文本是否会被AI检测器标记
      - 优化前分析：识别需要重写的段落
      - 优化后验证：确认降AI率效果
    """

    def __init__(self):
        # 中文分句正则
        self._sent_pattern = re.compile(r"[^。！？!?\n]+[。！？!?\n]?")
        # 中文分词简单版（按字符类型边界）
        self._word_pattern = re.compile(r"[\u4e00-\u9fff]+|[a-zA-Z]+|[0-9]+|[^\s\w]+")
        # 中文标点
        self._punct_pattern = re.compile(r'[，。！？、；：""' "「」『』（）【】《》—…\\s]")

    def analyze(self, text: str) -> FingerprintResult:
        """完整指纹分析"""
        if not text or len(text) < 50:
            return FingerprintResult()

        result = FingerprintResult()

        # 1. 分句
        sentences = self._split_sentences(text)
        if not sentences:
            return result

        result.sentence_lengths = [len(s) for s in sentences]
        result.avg_sentence_len = sum(result.sentence_lengths) / len(result.sentence_lengths)

        # 2. 句子长度变异系数
        result.sentence_length_cv = self._calc_cv(result.sentence_lengths)

        # 3. 近似困惑度（基于bigram概率分布）
        result.perplexity_score = self._calc_perplexity(text, sentences)

        # 4. 突发性（句子间困惑度变异系数）
        per_sentence_perplexity = []
        for sent in sentences:
            if len(sent) > 3:
                pp = self._calc_perplexity(sent, [sent])
                per_sentence_perplexity.append(pp)

        if per_sentence_perplexity:
            mean_pp = sum(per_sentence_perplexity) / len(per_sentence_perplexity)
            if mean_pp > 0:
                std_pp = math.sqrt(
                    sum((p - mean_pp) ** 2 for p in per_sentence_perplexity)
                    / len(per_sentence_perplexity)
                )
                result.burstiness = std_pp / mean_pp
            else:
                result.burstiness = 0.0

            # 记录每句分数
            for i, pp in enumerate(per_sentence_perplexity):
                result.per_sentence_scores.append(
                    {
                        "index": i,
                        "length": result.sentence_lengths[i]
                        if i < len(result.sentence_lengths)
                        else 0,
                        "perplexity": round(pp, 2),
                    }
                )

        # 5. 唯一词比例
        words = self._tokenize(text)
        if words:
            result.unique_word_ratio = len(set(words)) / len(words)

        # 6. 功能词占比
        if words:
            func_count = sum(1 for w in words if w in CHINESE_FUNCTION_WORDS)
            result.function_word_ratio = func_count / len(words)

        # 7. N-gram 重复度
        result.ngram_repetition = self._calc_ngram_repetition(text)

        # 8. 段落结构模板化
        result.paragraph_structure_score = self._calc_paragraph_structure(text)

        # 9. 综合判定
        result.ai_likelihood, result.is_suspicious, result.risk_level = self._classify(result)

        # 10. 标记可疑段落
        result.flagged_segments = self._find_flagged_segments(
            sentences, result.per_sentence_scores, result
        )

        return result

    def optimize(
        self,
        text: str,
        target_burstiness: float = 0.45,
        target_cv: float = 0.55,
    ) -> tuple[str, dict]:
        """
        统计指纹优化 — 通过句子结构调整降低AI检测指纹。

        Args:
            text: 原始文本
            target_burstiness: 目标突发性 (默认0.45，人类文本范围)
            target_cv: 目标句子长度变异系数 (默认0.55)

        Returns:
            (优化后文本, 变更统计)
        """
        profile = BurstinessProfile(
            target_burstiness=target_burstiness,
            target_cv=target_cv,
        )
        changes = {"merged": 0, "split": 0, "adjusted": 0}

        sentences = self._split_sentences(text)
        if len(sentences) < 3:
            return text, changes

        # 计算当前指标
        lengths = [len(s) for s in sentences]
        current_cv = self._calc_cv(lengths)

        # 策略1: 合并过短的句子（提高突发性）
        if current_cv < target_cv:
            sentences, merge_count = self._merge_short_sentences(
                sentences, profile.merge_threshold, profile.max_sentence_len
            )
            changes["merged"] = merge_count

        # 策略2: 拆分过长的句子（增加长度方差）
        lengths = [len(s) for s in sentences]
        current_cv = self._calc_cv(lengths)
        if current_cv < target_cv:
            sentences, split_count = self._split_long_sentences(sentences, profile.split_threshold)
            changes["split"] = split_count

        # 策略3: 调整段落边界（打断均匀节奏）
        sentences, adj_count = self._adjust_boundaries(sentences)
        changes["adjusted"] = adj_count

        return "".join(sentences), changes

    def compare(self, original: str, humanized: str) -> dict:
        """对比优化前后的指纹变化"""
        before = self.analyze(original)
        after = self.analyze(humanized)

        return {
            "perplexity": {
                "before": round(before.perplexity_score, 2),
                "after": round(after.perplexity_score, 2),
                "delta": round(after.perplexity_score - before.perplexity_score, 2),
            },
            "burstiness": {
                "before": round(before.burstiness, 3),
                "after": round(after.burstiness, 3),
                "delta": round(after.burstiness - before.burstiness, 3),
            },
            "sentence_cv": {
                "before": round(before.sentence_length_cv, 3),
                "after": round(after.sentence_length_cv, 3),
                "delta": round(after.sentence_length_cv - before.sentence_length_cv, 3),
            },
            "ai_likelihood": {
                "before": round(before.ai_likelihood, 3),
                "after": round(after.ai_likelihood, 3),
                "delta": round(after.ai_likelihood - before.ai_likelihood, 3),
                "reduction_pct": round(
                    (before.ai_likelihood - after.ai_likelihood)
                    / max(before.ai_likelihood, 0.001)
                    * 100,
                    1,
                ),
            },
            "risk_level": {
                "before": before.risk_level,
                "after": after.risk_level,
            },
        }

    # ── 内部方法 ──────────────────────────────────────

    def _split_sentences(self, text: str) -> list[str]:
        """分句"""
        raw = self._sent_pattern.findall(text)
        return [s.strip() for s in raw if s.strip()]

    def _tokenize(self, text: str) -> list[str]:
        """简单分词（按字符类型边界）"""
        return [m.group() for m in self._word_pattern.finditer(text)]

    def _calc_cv(self, values: list[int]) -> float:
        """计算变异系数"""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return math.sqrt(variance) / mean

    def _calc_perplexity(self, text: str, _sentences: list[str]) -> float:
        """
        近似困惑度计算（零模型依赖）

        方法: 基于 bigram 条件概率分布估算
        - 字符级别 bigram 频率越高 → 文本越可预测 → 困惑度越低 → AI嫌疑越大
        - 使用 Shannon 熵公式: H = -Σ p(x) * log2(p(x))
        - 困惑度 ≈ 2^H
        """
        if len(text) < 10:
            return 0.0

        # 构建 bigram 频率表
        chars = list(text)
        bigrams = Counter()
        for i in range(len(chars) - 1):
            bigrams[chars[i] + chars[i + 1]] += 1

        total = sum(bigrams.values())
        if total == 0:
            return 0.0

        # 计算熵
        entropy = 0.0
        for count in bigrams.values():
            prob = count / total
            if prob > 0:
                entropy -= prob * math.log2(prob)

        # 困惑度
        perplexity = 2**entropy

        # 归一化到合理范围 (中文文本典型困惑度10-80)
        # 纯AI文本通常在10-25，人类文本在30-80
        return min(perplexity, 80.0)

    def _calc_ngram_repetition(self, text: str) -> float:
        """计算n-gram重复度 (3-gram和4-gram)"""
        chars = list(text)
        if len(chars) < 8:
            return 0.0

        trigrams = [chars[i] + chars[i + 1] + chars[i + 2] for i in range(len(chars) - 2)]

        if not trigrams:
            return 0.0

        total = len(trigrams)
        unique = len(set(trigrams))
        # 重复度 = 1 - 唯一率
        return 1.0 - (unique / total)

    def _calc_paragraph_structure(self, text: str) -> float:
        """
        段落结构模板化程度

        检测AI文本常见的段落模式：
        - 每段长度高度一致
        - 段首/段尾使用固定句式
        - 段与段之间使用相同的过渡词
        """
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if len(paragraphs) < 3:
            return 0.0

        scores = []

        # 1. 段落长度变异系数
        para_lengths = [len(p) for p in paragraphs]
        para_cv = self._calc_cv(para_lengths)
        # 长度越均匀 → 越AI (CV < 0.3)
        if para_cv < 0.3:
            scores.append(1.0 - para_cv / 0.3)
        else:
            scores.append(0.0)

        # 2. 段首模式重复
        openings = [p[:4] if len(p) >= 4 else p for p in paragraphs]
        opening_dup = 1.0 - (len(set(openings)) / len(openings))
        scores.append(opening_dup)

        # 3. 过渡词使用
        transition_words = ["然而", "因此", "此外", "与此同时", "另一方面", "不过", "但是"]
        transition_count = sum(1 for p in paragraphs for tw in transition_words if tw in p)
        if transition_count > len(paragraphs) * 0.5:
            scores.append(1.0)

        return sum(scores) / len(scores) if scores else 0.0

    def _classify(self, result: FingerprintResult) -> tuple[float, bool, str]:
        """
        综合分类判定

        基于多维度信号：
        - 低困惑度 + 低突发性 = 强AI信号
        - 低句子CV + 高功能词比 = 强AI信号
        - 高n-gram重复 + 模板化段落 = 强AI信号
        """
        signals = []

        # 信号1: 困惑度 (越低越AI)
        if result.perplexity_score > 0:
            # 困惑度 < 20 → AI嫌疑
            pp_signal = max(0, 1 - result.perplexity_score / 40)
            signals.append(("perplexity", pp_signal, 0.25))

        # 信号2: 突发性 (越低越AI)
        burst_signal = max(0, 1 - result.burstiness / 0.5)
        signals.append(("burstiness", burst_signal, 0.25))

        # 信号3: 句子长度CV (越低越AI)
        cv_signal = max(0, 1 - result.sentence_length_cv / 0.6)
        signals.append(("sentence_cv", cv_signal, 0.15))

        # 信号4: 功能词占比 (越高越AI)
        func_signal = min(1, result.function_word_ratio / 0.45)
        signals.append(("function_words", func_signal, 0.15))

        # 信号5: n-gram重复 (越高越AI)
        signals.append(("ngram_repeat", result.ngram_repetition, 0.10))

        # 信号6: 段落结构 (越高越AI)
        signals.append(("para_structure", result.paragraph_structure_score, 0.10))

        # 加权求和
        likelihood = sum(s * w for _, s, w in signals)

        is_suspicious = likelihood > 0.5
        if likelihood > 0.7:
            risk_level = "high"
        elif likelihood > 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"

        return likelihood, is_suspicious, risk_level

    def _find_flagged_segments(
        self,
        sentences: list[str],
        per_sentence_scores: list[dict],
        _result: FingerprintResult,
    ) -> list[str]:
        """找出被标记的可疑段落"""
        flagged = []
        for score in per_sentence_scores:
            if score.get("perplexity", 50) < 15:
                idx = score["index"]
                if idx < len(sentences):
                    flagged.append(sentences[idx])
        return flagged[:5]  # 最多5个

    def _merge_short_sentences(
        self, sentences: list[str], threshold: int, max_len: int
    ) -> tuple[list[str], int]:
        """合并过短的句子"""
        result = []
        i = 0
        changes = 0
        while i < len(sentences):
            current = sentences[i]
            # 如果当前句子很短且下一句也很短，合并
            if (
                len(current) <= threshold
                and i + 1 < len(sentences)
                and len(current) + len(sentences[i + 1]) <= max_len
            ):
                # 去除当前句末标点，连接下一句
                merged = current.rstrip("。！？!?\n") + "，" + sentences[i + 1]
                result.append(merged)
                i += 2
                changes += 1
            else:
                result.append(current)
                i += 1
        return result, changes

    def _split_long_sentences(self, sentences: list[str], threshold: int) -> tuple[list[str], int]:
        """拆分过长的句子"""
        result = []
        changes = 0
        for sent in sentences:
            if len(sent) > threshold:
                # 在逗号处分句
                parts = sent.split("，")
                if len(parts) >= 3:
                    # 将后半部分独立成句
                    mid = len(parts) // 2
                    first = "，".join(parts[:mid])
                    second = "，".join(parts[mid:])
                    if not first.endswith(("。", "！", "？")):
                        first += "。"
                    result.append(first)
                    result.append(second)
                    changes += 1
                    continue
            result.append(sent)
        return result, changes

    def _adjust_boundaries(self, sentences: list[str]) -> tuple[list[str], int]:
        """调整句子边界，打破均匀节奏"""
        import random

        if len(sentences) < 5:
            return sentences, 0

        changes = 0
        # 随机选择一些句子，改变其边界
        for i, sent in enumerate(sentences):
            if random.random() < 0.15 and len(sent) > 15:
                # 在句中随机位置插入换行（模拟人类作者的不规则分段）
                pos = random.randint(len(sent) // 3, len(sent) * 2 // 3)
                # 找到最近的逗号位置
                comma_pos = sent.find("，", pos - 5)
                if comma_pos > 0:
                    first = sent[:comma_pos]
                    rest = sent[comma_pos + 1 :]
                    sentences[i] = first + "。"
                    sentences.insert(i + 1, rest)
                    changes += 1

        return sentences, changes


# 全局单例
text_fingerprint = TextFingerprint()
