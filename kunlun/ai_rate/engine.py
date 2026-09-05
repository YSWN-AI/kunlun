"""
昆仑创作引擎 — AI率检测与人类化改写引擎

专门针对中文男频网络小说的AI文本特征检测与人类化改写。

核心能力:
  1. AI率多维检测 — 12个维度量化AI特征，输出0-100分AI率
  2. 高频AI词检测 — 80+中文网文AI高频词/短语
  3. 人类化改写 — 7种改写策略，可组合使用
  4. 批量处理 — 支持章节级批量检测与改写
  5. 可配置规则 — 支持自定义词表、阈值、改写策略

与昆仑引擎集成:
  - 作为 audit/ 模块的扩展，接入8道门禁（作为G9 AI率门禁）
  - 增强 humanize/ 模块能力
  - 输出可被质量看板消费的结构化数据

Author: 昆仑创作引擎
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ══════════════════════════════════════════════════════
# AI高频词表（中文男频网文）
# ══════════════════════════════════════════════════════

# 一级高危词 — 出现即显著提升AI率
AI_HIGH_RISK_WORDS: list[str] = [
    "仿佛",
    "似乎",
    "好像",
    "犹如",
    "宛如",
    "宛若",
    "恍若",
    "不由得",
    "不由自主",
    "情不自禁",
    "忍不住",
    "心中一动",
    "心中暗喜",
    "心中暗道",
    "心中冷笑",
    "心中一凛",
    "眼中闪过",
    "眼中精光",
    "眼中寒芒",
    "眼中异色",
    "嘴角上扬",
    "嘴角微扬",
    "嘴角勾起",
    "嘴角噙着",
    "微微一怔",
    "微微一愣",
    "微微点头",
    "微微皱眉",
    "微微颔首",
    "缓缓开口",
    "缓缓说道",
    "缓缓点头",
    "缓缓闭上",
    "淡淡一笑",
    "淡淡说道",
    "淡淡开口",
    "淡淡瞥了",
    "轻轻摇头",
    "轻轻叹息",
    "轻轻一笑",
    "轻轻抚摸",
    "深深看了",
    "深深吸了",
    "深深叹息",
    "冷冷一笑",
    "冷冷说道",
    "冷冷瞥了",
    "默默点头",
    "默默记下",
    "默默观察",
    "赫然发现",
    "赫然在目",
    "定睛一看",
    "凝神细看",
    "倒吸一口凉气",
    "倒吸冷气",
    "瞳孔骤缩",
    "瞳孔一缩",
    "瞳孔猛缩",
    "心神一震",
    "心神激荡",
    "心神剧震",
    "气血翻涌",
    "气血上涌",
    "杀意凛然",
    "杀意沸腾",
    "杀意冲天",
    "气势攀升",
    "气势暴涨",
    "气势如虹",
    "威压笼罩",
    "威压降临",
    "能量暴动",
    "能量狂暴",
    "法则之力",
    "法则碎片",
    "法则锁链",
    "大道共鸣",
    "大道碎片",
    "大道烙印",
    "天地异象",
    "天地变色",
    "天地震颤",
    "风云变色",
    "风云际会",
    "雷霆万钧",
    "雷霆之势",
    "排山倒海",
    "山崩地裂",
    "石破天惊",
    "惊天动地",
    "不可思议",
    "难以置信",
    "匪夷所思",
    "果然如此",
    "不出所料",
    "原来如此",
    "恍然大悟",
    "心念电转",
    "心念一动",
    "神念一扫",
    "神识探查",
    "储物戒指",
    "纳戒",
    "灵力运转",
    "真元运转",
    "真气运转",
    "功法运转",
    "心法运转",
    "突破瓶颈",
    "突破桎梏",
    "境界提升",
    "修为精进",
    "底蕴深厚",
    "底蕴惊人",
    "天赋异禀",
    "天赋绝伦",
    "根骨奇佳",
    "根骨惊人",
    "气运加身",
    "气运滔天",
    "命格不凡",
    "命数逆天",
]

# 二级中危词 — 过度使用提升AI率
AI_MEDIUM_RISK_WORDS: list[str] = [
    "然而",
    "不过",
    "但是",
    "可是",
    "只是",
    "于是",
    "因此",
    "所以",
    "故而",
    "随即",
    "旋即",
    "当下",
    "当即",
    "立刻",
    "立即",
    "此时",
    "此刻",
    "如今",
    "见状",
    "见此",
    "见此情景",
    "闻言",
    "听到这话",
    "想到这里",
    "念及此处",
    "一时间",
    "刹那间",
    "顷刻间",
    "转瞬间",
    "下一刻",
    "下一瞬",
    "这一幕",
    "这一场景",
    "这等",
    "这般",
    "如此",
    "何等",
    "何其",
    "竟然",
    "居然",
    "赫然",
    "果然",
    "果真",
    "难道",
    "莫非",
    "或许",
    "也许",
    "兴许",
    "大概",
    "大约",
    "约莫",
    "几乎",
    "差不多",
    "完全",
    "彻底",
    "全然",
    "绝对",
    "肯定",
    "必定",
    "非常",
    "十分",
    "格外",
    "异常",
    "极其",
    "极为",
    "甚是",
    "相当",
    "颇为",
    "略为",
    "微微",
    "轻轻",
    "缓缓",
    "淡淡",
    "默默",
    "冷冷",
    "深深",
    "渐渐",
    "慢慢",
    "徐徐",
    "纷纷",
    "陆续",
    "依次",
    "不断",
    "不停",
    "不止",
    "再次",
    "再度",
    "又一次",
    "终于",
    "最终",
    "终究",
    "从此",
    "自此",
    "此后",
    "之前",
    "先前",
    "此前",
    "之后",
    "随后",
    "此后",
    "之间",
    "之中",
    "之内",
    "周围",
    "四周",
    "周遭",
    "面前",
    "眼前",
    "身前",
    "身后",
    "背后",
    "后方",
    "上方",
    "下方",
    "左侧",
    "右侧",
]

# 男频人类常用语（用于改写时增加人类感）
HUMAN_STYLE_PHRASES: list[str] = [
    "卧槽",
    "我靠",
    "尼玛",
    "我去",
    "好家伙",
    "这波",
    "这波啊",
    "这波是",
    "血赚",
    "血亏",
    "稳赚",
    "不亏",
    "舒服了",
    "舒坦",
    "得劲",
    "爽",
    "离谱",
    "离大谱",
    "离了个大谱",
    "绝了",
    "牛批",
    "牛逼",
    "666",
    "六六六",
    "淦",
    "干",
    "冲",
    "上",
    "盘他",
    "弄他",
    "干他",
    "安排",
    "搞定",
    "拿下",
    "稳了",
    "稳",
    "妥了",
    "麻了",
    "麻爪",
    "懵了",
    "人傻了",
    "人麻了",
    "人没了",
    "裂开",
    "心态崩了",
    "破防",
    "真香",
    "真不错",
    "真行",
    "就这",
    "就这？",
    "就这啊",
    "不会吧",
    "不是吧",
    "不能吧",
    "有没有搞错",
    "搞什么",
    "什么鬼",
    "爷青回",
    "爷青结",
    "有生之年",
    "活久见",
    "学到了",
    "涨知识了",
    "这合理吗",
    "这河里吗",
    "小丑竟是我自己",
    "伤害不高侮辱性极强",
    "咱就是说",
    "一整个",
]


# ══════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════


class AIFeatureDimension(Enum):
    """AI特征检测维度"""

    HIGH_RISK_WORDS = "high_risk_words"
    MEDIUM_RISK_WORDS = "medium_risk_words"
    SENTENCE_LENGTH_UNIFORMITY = "sentence_length_uniformity"
    PARAGRAPH_STRUCTURE = "paragraph_structure"
    LOGIC_CONNECTOR_DENSITY = "logic_connector"
    ADJECTIVE_ADVERB_DENSITY = "adj_adv_density"
    DIALOGUE_RATIO = "dialogue_ratio"
    REPETITION_PATTERN = "repetition"
    PUNCTUATION_DIVERSITY = "punctuation_diversity"
    CLAUSE_STRUCTURE = "clause_structure"
    NAMED_ENTITY_RICHNESS = "ner_richness"
    EMOTION_EXPRESSION = "emotion_expression"


@dataclass
class DimensionResult:
    """单维度检测结果"""

    dimension: AIFeatureDimension
    score: float
    weight: float
    detail: dict[str, Any] = field(default_factory=dict)
    suggestion: str = ""


@dataclass
class AIRateReport:
    """AI率检测报告"""

    total_score: float
    dimensions: list[DimensionResult] = field(default_factory=list)
    high_risk_hits: list[tuple[str, int]] = field(default_factory=list)
    medium_risk_hits: list[tuple[str, int]] = field(default_factory=list)
    human_phrases_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    word_count: int = 0
    dialogue_count: int = 0
    is_pass: bool = False
    threshold: float = 35.0

    def summary(self) -> str:
        level = (
            "极低"
            if self.total_score < 20
            else "较低"
            if self.total_score < 35
            else "中等"
            if self.total_score < 50
            else "较高"
            if self.total_score < 70
            else "极高"
        )
        top_dims = sorted(self.dimensions, key=lambda d: d.score, reverse=True)[:3]
        top_str = "、".join(f"{d.dimension.value}({d.score:.0f})" for d in top_dims)
        return (
            f"AI率: {self.total_score:.1f}/100 ({level}) | "
            f"字数: {self.word_count} | 段落: {self.paragraph_count} | "
            f"高危词: {len(self.high_risk_hits)}种 | "
            f"主要AI特征: {top_str}"
        )


@dataclass
class HumanizeResult:
    """人类化改写结果"""

    original_text: str
    modified_text: str
    changes: list[dict[str, Any]] = field(default_factory=list)
    ai_rate_before: float = 0.0
    ai_rate_after: float = 0.0
    strategies_used: list[str] = field(default_factory=list)
    word_count_before: int = 0
    word_count_after: int = 0


# ══════════════════════════════════════════════════════
# AI率检测引擎
# ══════════════════════════════════════════════════════


class AIRateDetector:
    """AI率多维检测引擎"""

    DIMENSION_WEIGHTS: dict[AIFeatureDimension, float] = {
        AIFeatureDimension.HIGH_RISK_WORDS: 0.18,
        AIFeatureDimension.MEDIUM_RISK_WORDS: 0.10,
        AIFeatureDimension.SENTENCE_LENGTH_UNIFORMITY: 0.12,
        AIFeatureDimension.PARAGRAPH_STRUCTURE: 0.08,
        AIFeatureDimension.LOGIC_CONNECTOR_DENSITY: 0.10,
        AIFeatureDimension.ADJECTIVE_ADVERB_DENSITY: 0.10,
        AIFeatureDimension.DIALOGUE_RATIO: 0.08,
        AIFeatureDimension.REPETITION_PATTERN: 0.08,
        AIFeatureDimension.PUNCTUATION_DIVERSITY: 0.06,
        AIFeatureDimension.CLAUSE_STRUCTURE: 0.05,
        AIFeatureDimension.NAMED_ENTITY_RICHNESS: 0.03,
        AIFeatureDimension.EMOTION_EXPRESSION: 0.02,
    }

    def __init__(
        self,
        threshold: float = 35.0,
        custom_high_risk: list[str] | None = None,
        custom_medium_risk: list[str] | None = None,
    ):
        self.threshold = threshold
        self.high_risk_words = list(set(AI_HIGH_RISK_WORDS + (custom_high_risk or [])))
        self.medium_risk_words = list(set(AI_MEDIUM_RISK_WORDS + (custom_medium_risk or [])))

    def detect(self, text: str) -> AIRateReport:
        if not text or not text.strip():
            return AIRateReport(total_score=0, is_pass=True, threshold=self.threshold)

        word_count = len(text.replace(" ", "").replace("\n", ""))
        sentences = self._split_sentences(text)
        paragraphs = [p for p in text.split("\n") if p.strip()]

        report = AIRateReport(
            total_score=0,
            word_count=word_count,
            sentence_count=len(sentences),
            paragraph_count=len(paragraphs),
            threshold=self.threshold,
        )

        dimensions: list[DimensionResult] = []

        d1, high_hits = self._detect_high_risk_words(text, word_count)
        dimensions.append(d1)
        report.high_risk_hits = high_hits

        d2, medium_hits = self._detect_medium_risk_words(text, word_count)
        dimensions.append(d2)
        report.medium_risk_hits = medium_hits

        d3 = self._detect_sentence_uniformity(sentences)
        dimensions.append(d3)

        d4 = self._detect_paragraph_structure(paragraphs)
        dimensions.append(d4)

        d5 = self._detect_logic_connectors(text, word_count)
        dimensions.append(d5)

        d6 = self._detect_adj_adv_density(text, word_count)
        dimensions.append(d6)

        d7, dialogue_count = self._detect_dialogue_ratio(text, word_count)
        dimensions.append(d7)
        report.dialogue_count = dialogue_count

        d8 = self._detect_repetition(text)
        dimensions.append(d8)

        d9 = self._detect_punctuation_diversity(text)
        dimensions.append(d9)

        d10 = self._detect_clause_structure(sentences)
        dimensions.append(d10)

        d11 = self._detect_ner_richness(text)
        dimensions.append(d11)

        d12 = self._detect_emotion_expression(text)
        dimensions.append(d12)

        report.dimensions = dimensions

        total_weight = sum(self.DIMENSION_WEIGHTS.values())
        weighted_sum = sum(d.score * self.DIMENSION_WEIGHTS.get(d.dimension, 0) for d in dimensions)
        report.total_score = (
            min(100.0, weighted_sum / total_weight * 1.2) if total_weight > 0 else 0
        )

        human_count = sum(text.count(p) for p in HUMAN_STYLE_PHRASES[:50])
        report.human_phrases_count = human_count
        if human_count > 0:
            report.total_score = max(0, report.total_score - min(15, human_count * 0.5))

        report.is_pass = report.total_score <= self.threshold
        return report

    def _split_sentences(self, text: str) -> list[str]:
        text = re.sub(r"\s+", " ", text)
        parts = re.split(r"(?<=[。！？!?…])", text)
        return [p.strip() for p in parts if p.strip() and len(p.strip()) > 1]

    def _detect_high_risk_words(self, text: str, word_count: int):
        hits: dict[str, int] = {}
        for word in self.high_risk_words:
            count = text.count(word)
            if count > 0:
                hits[word] = count
        total_hits = sum(hits.values())
        density = total_hits / max(1, word_count / 1000)
        score = min(100, density * 6)
        sorted_hits = sorted(hits.items(), key=lambda x: x[1], reverse=True)
        suggestion = ""
        if score > 40:
            top_words = "、".join(w for w, _ in sorted_hits[:5])
            suggestion = f"高危AI词密度过高({density:.1f}/千字)，建议替换/删除: {top_words}"
        return DimensionResult(
            dimension=AIFeatureDimension.HIGH_RISK_WORDS,
            score=score,
            weight=self.DIMENSION_WEIGHTS[AIFeatureDimension.HIGH_RISK_WORDS],
            detail={"density_per_1k": density, "total_hits": total_hits, "unique_words": len(hits)},
            suggestion=suggestion,
        ), sorted_hits

    def _detect_medium_risk_words(self, text: str, word_count: int):
        hits: dict[str, int] = {}
        for word in self.medium_risk_words:
            count = text.count(word)
            if count > 0:
                hits[word] = count
        total_hits = sum(hits.values())
        density = total_hits / max(1, word_count / 1000)
        score = min(100, density * 1.5)
        sorted_hits = sorted(hits.items(), key=lambda x: x[1], reverse=True)
        suggestion = ""
        if score > 50:
            top_words = "、".join(w for w, _ in sorted_hits[:5])
            suggestion = f"中危AI词密度过高({density:.0f}/千字)，建议减少: {top_words}"
        return DimensionResult(
            dimension=AIFeatureDimension.MEDIUM_RISK_WORDS,
            score=score,
            weight=self.DIMENSION_WEIGHTS[AIFeatureDimension.MEDIUM_RISK_WORDS],
            detail={"density_per_1k": density, "total_hits": total_hits},
            suggestion=suggestion,
        ), sorted_hits

    def _detect_sentence_uniformity(self, sentences: list[str]):
        if len(sentences) < 3:
            return DimensionResult(
                dimension=AIFeatureDimension.SENTENCE_LENGTH_UNIFORMITY,
                score=0,
                weight=self.DIMENSION_WEIGHTS[AIFeatureDimension.SENTENCE_LENGTH_UNIFORMITY],
                detail={"sentence_count": len(sentences)},
            )
        lengths = [len(s) for s in sentences]
        mean_len = sum(lengths) / len(lengths)
        variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
        std_dev = math.sqrt(variance)
        cv = std_dev / max(1, mean_len)
        score = max(0, min(100, (0.4 - cv) * 250))
        suggestion = ""
        if score > 50:
            suggestion = f"句长过于均匀(变异系数{cv:.2f})，建议拆分长句/合并短句"
        return DimensionResult(
            dimension=AIFeatureDimension.SENTENCE_LENGTH_UNIFORMITY,
            score=score,
            weight=self.DIMENSION_WEIGHTS[AIFeatureDimension.SENTENCE_LENGTH_UNIFORMITY],
            detail={
                "mean_length": mean_len,
                "std_dev": std_dev,
                "cv": cv,
                "min": min(lengths),
                "max": max(lengths),
            },
            suggestion=suggestion,
        )

    def _detect_paragraph_structure(self, paragraphs: list[str]):
        if len(paragraphs) < 2:
            return DimensionResult(
                dimension=AIFeatureDimension.PARAGRAPH_STRUCTURE,
                score=0,
                weight=self.DIMENSION_WEIGHTS[AIFeatureDimension.PARAGRAPH_STRUCTURE],
            )
        lengths = [len(p) for p in paragraphs]
        mean_len = sum(lengths) / len(lengths)
        short_ratio = sum(1 for l in lengths if l < 20) / len(lengths)
        long_ratio = sum(1 for l in lengths if l > 200) / len(lengths)
        score = 0
        if short_ratio < 0.1:
            score += 40
        if long_ratio > 0.4:
            score += 30
        if mean_len > 100:
            score += 20
        score = min(100, score)
        suggestion = ""
        if score > 40:
            suggestion = f"段落结构规整(平均{mean_len:.0f}字)，建议增加短段落，拆分长段落"
        return DimensionResult(
            dimension=AIFeatureDimension.PARAGRAPH_STRUCTURE,
            score=score,
            weight=self.DIMENSION_WEIGHTS[AIFeatureDimension.PARAGRAPH_STRUCTURE],
            detail={"mean_length": mean_len, "short_ratio": short_ratio, "long_ratio": long_ratio},
            suggestion=suggestion,
        )

    def _detect_logic_connectors(self, text: str, word_count: int):
        connectors = [
            "然而",
            "不过",
            "但是",
            "可是",
            "于是",
            "因此",
            "所以",
            "故而",
            "随即",
            "旋即",
            "当下",
            "当即",
            "此时",
            "此刻",
            "见状",
            "闻言",
            "想到这里",
            "念及此处",
            "一时间",
            "刹那间",
            "顷刻间",
            "下一刻",
            "这一幕",
            "这等",
            "这般",
            "如此",
            "竟然",
            "居然",
            "果然",
            "难道",
        ]
        total = sum(text.count(c) for c in connectors)
        density = total / max(1, word_count / 1000)
        score = min(100, density * 3)
        suggestion = ""
        if score > 50:
            suggestion = f"逻辑连接词密度过高({density:.0f}/千字)，建议减少过渡词"
        return DimensionResult(
            dimension=AIFeatureDimension.LOGIC_CONNECTOR_DENSITY,
            score=score,
            weight=self.DIMENSION_WEIGHTS[AIFeatureDimension.LOGIC_CONNECTOR_DENSITY],
            detail={"density_per_1k": density, "total": total},
            suggestion=suggestion,
        )

    def _detect_adj_adv_density(self, text: str, word_count: int):
        de_count = text.count("地") + text.count("得")
        degree_words = ["非常", "十分", "格外", "异常", "极其", "极为", "甚是", "相当", "颇为"]
        degree_count = sum(text.count(w) for w in degree_words)
        total = de_count + degree_count
        density = total / max(1, word_count / 1000)
        score = min(100, density * 2)
        suggestion = ""
        if score > 50:
            suggestion = f"形容词副词密度过高({density:.0f}/千字)，建议减少过度修饰"
        return DimensionResult(
            dimension=AIFeatureDimension.ADJECTIVE_ADVERB_DENSITY,
            score=score,
            weight=self.DIMENSION_WEIGHTS[AIFeatureDimension.ADJECTIVE_ADVERB_DENSITY],
            detail={"density_per_1k": density, "de_count": de_count, "degree_count": degree_count},
            suggestion=suggestion,
        )

    def _detect_dialogue_ratio(self, text: str, word_count: int):
        dialogues = re.findall(r'[""「『]([^""」』]+)[""」』]', text)
        dialogue_chars = sum(len(d) for d in dialogues)
        dialogue_ratio = dialogue_chars / max(1, word_count)
        score = 0
        if dialogue_ratio < 0.05:
            score = 80
        elif dialogue_ratio < 0.10:
            score = 50
        elif dialogue_ratio < 0.15:
            score = 20
        suggestion = ""
        if score > 40:
            suggestion = f"对话比例过低({dialogue_ratio * 100:.0f}%)，建议增加角色对话"
        return DimensionResult(
            dimension=AIFeatureDimension.DIALOGUE_RATIO,
            score=score,
            weight=self.DIMENSION_WEIGHTS[AIFeatureDimension.DIALOGUE_RATIO],
            detail={
                "dialogue_ratio": dialogue_ratio,
                "dialogue_count": len(dialogues),
                "dialogue_chars": dialogue_chars,
            },
            suggestion=suggestion,
        ), len(dialogues)

    def _detect_repetition(self, text: str):
        repeats = re.findall(r"(.{2,})\1", text)
        repeat_count = len(repeats)
        paragraphs = [p for p in text.split("\n") if p.strip()]
        start_repeats = 0
        for i in range(1, len(paragraphs)):
            if paragraphs[i][:2] == paragraphs[i - 1][:2]:
                start_repeats += 1
        score = min(100, repeat_count * 5 + start_repeats * 10)
        suggestion = ""
        if score > 30:
            suggestion = f"检测到{repeat_count}处词语重复、{start_repeats}处段落开头重复"
        return DimensionResult(
            dimension=AIFeatureDimension.REPETITION_PATTERN,
            score=score,
            weight=self.DIMENSION_WEIGHTS[AIFeatureDimension.REPETITION_PATTERN],
            detail={"word_repeats": repeat_count, "paragraph_start_repeats": start_repeats},
            suggestion=suggestion,
        )

    def _detect_punctuation_diversity(self, text: str):
        punctuations = {
            "。": 0,
            "，": 0,
            "！": 0,
            "？": 0,
            "、": 0,
            "；": 0,
            "：": 0,
            "…": 0,
            "—": 0,
            "（": 0,
            "「": 0,
            "『": 0,
        }
        for p in punctuations:
            punctuations[p] = text.count(p)
        total_punct = sum(punctuations.values())
        if total_punct == 0:
            return DimensionResult(
                dimension=AIFeatureDimension.PUNCTUATION_DIVERSITY,
                score=0,
                weight=self.DIMENSION_WEIGHTS[AIFeatureDimension.PUNCTUATION_DIVERSITY],
            )
        used_types = sum(1 for v in punctuations.values() if v > 0)
        diversity = used_types / len(punctuations)
        comma_period_ratio = (punctuations["，"] + punctuations["。"]) / total_punct
        score = 0
        if comma_period_ratio > 0.85:
            score += 50
        if diversity < 0.4:
            score += 40
        if punctuations["…"] == 0 and punctuations["—"] == 0:
            score += 20
        score = min(100, score)
        suggestion = ""
        if score > 40:
            suggestion = (
                f"标点单一(逗号句号占比{comma_period_ratio * 100:.0f}%)，建议增加省略号/破折号"
            )
        return DimensionResult(
            dimension=AIFeatureDimension.PUNCTUATION_DIVERSITY,
            score=score,
            weight=self.DIMENSION_WEIGHTS[AIFeatureDimension.PUNCTUATION_DIVERSITY],
            detail={
                "diversity": diversity,
                "comma_period_ratio": comma_period_ratio,
                "used_types": used_types,
            },
            suggestion=suggestion,
        )

    def _detect_clause_structure(self, sentences: list[str]):
        if not sentences:
            return DimensionResult(
                dimension=AIFeatureDimension.CLAUSE_STRUCTURE,
                score=0,
                weight=self.DIMENSION_WEIGHTS[AIFeatureDimension.CLAUSE_STRUCTURE],
            )
        clause_markers = [
            "因为",
            "所以",
            "虽然",
            "但是",
            "如果",
            "那么",
            "既然",
            "就",
            "即使",
            "也",
            "无论",
            "都",
            "只要",
            "只有",
            "才",
            "不但",
            "而且",
            "不仅",
            "还",
            "与其",
            "不如",
            "宁可",
            "也不",
        ]
        total_clauses = sum(s.count(m) for s in sentences for m in clause_markers)
        avg_clauses = total_clauses / len(sentences)
        long_ratio = sum(1 for s in sentences if len(s) > 50) / len(sentences)
        score = 0
        if avg_clauses > 1.5:
            score += 40
        if long_ratio > 0.5:
            score += 40
        score = min(100, score)
        suggestion = ""
        if score > 40:
            suggestion = f"从句结构复杂(平均{avg_clauses:.1f}个/句)，建议拆分长句"
        return DimensionResult(
            dimension=AIFeatureDimension.CLAUSE_STRUCTURE,
            score=score,
            weight=self.DIMENSION_WEIGHTS[AIFeatureDimension.CLAUSE_STRUCTURE],
            detail={"avg_clauses": avg_clauses, "long_ratio": long_ratio},
            suggestion=suggestion,
        )

    def _detect_ner_richness(self, text: str):
        name_patterns = re.findall(r"[\u4e00-\u9fa5]{2,4}(?=[说道想看听走打杀攻防])", text)
        unique_names = len(set(name_patterns))
        proper_nouns = re.findall(r"[「『【]([^」』】]+)[」』】]", text)
        unique_proper = len(set(proper_nouns))
        total_unique = unique_names + unique_proper
        density = total_unique / max(1, len(text) / 1000)
        score = max(0, min(100, (5 - density) * 20))
        suggestion = ""
        if score > 40:
            suggestion = f"命名实体偏少({density:.1f}/千字)，建议增加具体人名/地名/功法名"
        return DimensionResult(
            dimension=AIFeatureDimension.NAMED_ENTITY_RICHNESS,
            score=score,
            weight=self.DIMENSION_WEIGHTS[AIFeatureDimension.NAMED_ENTITY_RICHNESS],
            detail={
                "unique_names": unique_names,
                "unique_proper": unique_proper,
                "density": density,
            },
            suggestion=suggestion,
        )

    def _detect_emotion_expression(self, text: str):
        direct_emotions = [
            "怒",
            "喜",
            "悲",
            "惊",
            "惧",
            "恨",
            "爱",
            "烦",
            "闷",
            "爽",
            "开心",
            "难过",
            "生气",
            "害怕",
            "兴奋",
            "激动",
            "郁闷",
            "卧槽",
            "我靠",
            "尼玛",
            "离谱",
            "绝了",
            "牛批",
        ]
        indirect_emotions = [
            "心中",
            "内心",
            "心底",
            "心头",
            "心间",
            "心神",
            "不由得",
            "不由自主",
            "情不自禁",
            "眼中",
            "眼底",
            "眸中",
            "眸底",
            "脸上",
            "面庞",
            "面容",
            "容颜",
        ]
        direct_count = sum(text.count(e) for e in direct_emotions)
        indirect_count = sum(text.count(e) for e in indirect_emotions)
        ratio = direct_count / max(1, indirect_count)
        score = max(0, min(100, (0.3 - ratio) * 200))
        suggestion = ""
        if score > 40:
            suggestion = f"情感表达过于间接(直接/间接比{ratio:.2f})，建议增加直接情感词"
        return DimensionResult(
            dimension=AIFeatureDimension.EMOTION_EXPRESSION,
            score=score,
            weight=self.DIMENSION_WEIGHTS[AIFeatureDimension.EMOTION_EXPRESSION],
            detail={"direct_count": direct_count, "indirect_count": indirect_count, "ratio": ratio},
            suggestion=suggestion,
        )


# ══════════════════════════════════════════════════════
# 人类化改写引擎
# ══════════════════════════════════════════════════════


class HumanizeStrategy(Enum):
    """人类化改写策略"""

    REPLACE_HIGH_RISK = "replace_high_risk"
    REMOVE_REDUNDANT = "remove_redundant"
    VARY_SENTENCE_LENGTH = "vary_sentence_length"
    ADD_HUMAN_PHRASES = "add_human_phrases"
    VARY_PUNCTUATION = "vary_punctuation"
    SPLIT_LONG_PARAGRAPHS = "split_long_paragraphs"
    ADJUST_DIALOGUE = "adjust_dialogue"


HIGH_RISK_REPLACEMENTS: dict[str, list[str]] = {
    "仿佛": ["就像", "正像", "像是"],
    "似乎": ["看起来", "看样子", "像是"],
    "犹如": ["就像", "好比", "如同"],
    "宛如": ["就像", "仿佛", "如同"],
    "不由得": ["忍不住", "禁不住", "不由"],
    "不由自主": ["忍不住", "控制不住", "身不由己"],
    "心中一动": ["心里一动", "动了心思", "心念一动"],
    "心中暗喜": ["心里偷着乐", "暗自高兴", "暗喜"],
    "心中暗道": ["心里骂道", "暗道", "心想"],
    "心中冷笑": ["心里冷笑", "冷哼", "暗笑"],
    "眼中闪过": ["眼里闪过", "目光一动", "眼神一变"],
    "眼中精光": ["眼里精光", "目光如电", "眼神锐利"],
    "嘴角上扬": ["嘴角翘了翘", "咧嘴", "勾了勾嘴角"],
    "嘴角微扬": ["嘴角翘了翘", "勾了勾嘴角", "微微一笑"],
    "微微一怔": ["愣了一下", "一怔", "呆了呆"],
    "微微一愣": ["愣了一下", "一愣", "呆了呆"],
    "微微点头": ["点了点头", "点头", "颔首"],
    "微微皱眉": ["皱了皱眉", "皱眉", "眉头一皱"],
    "缓缓开口": ["开口道", "说道", "慢慢说"],
    "缓缓说道": ["说道", "慢慢说", "缓缓道"],
    "淡淡一笑": ["笑了笑", "轻笑", "微微一笑"],
    "淡淡说道": ["说道", "淡声道", "平静道"],
    "轻轻摇头": ["摇了摇头", "摇头", "摇摇头"],
    "轻轻叹息": ["叹了口气", "叹息", "轻叹"],
    "深深看了": ["看了一眼", "凝视", "盯着"],
    "深深吸了": ["吸了口气", "深吸一口气", "深吸"],
    "冷冷一笑": ["冷笑", "嗤笑", "寒笑"],
    "冷冷说道": ["冷声道", "寒声道", "冷冷道"],
    "默默点头": ["点了点头", "点头"],
    "赫然发现": ["突然发现", "竟发现", "猛然发现"],
    "定睛一看": ["定睛看去", "仔细一看", "凝目看去"],
    "凝神细看": ["凝神看去", "仔细看去"],
    "倒吸一口凉气": ["倒吸凉气", "吸了口凉气", "倒抽冷气"],
    "瞳孔骤缩": ["瞳孔一缩", "眼皮一跳", "眼神一凝"],
    "心神一震": ["心头一震", "心里咯噔一下", "心中一震"],
    "心神激荡": ["心潮澎湃", "激动不已"],
    "气血翻涌": ["气血上涌", "血气翻涌"],
    "杀意凛然": ["杀意腾腾", "满身杀气"],
    "气势攀升": ["气势暴涨", "气势不断提升"],
    "威压笼罩": ["威压降临", "压力山大"],
    "不可思议": ["难以置信", "不敢相信", "怎么可能"],
    "难以置信": ["不敢相信", "怎么可能", "难以想象"],
    "果然如此": ["果然", "不出所料", "果真如此"],
    "原来如此": ["原来如此", "明白了", "原来这样"],
    "恍然大悟": ["豁然开朗", "明白了", "顿时明白"],
    "心念电转": ["念头急转", "心思电转"],
    "心念一动": ["心中一动", "动了念头"],
    "神念一扫": ["神识一扫", "意念扫过"],
    "突破瓶颈": ["突破", "打破瓶颈"],
    "境界提升": ["境界突破", "修为提升"],
    "天赋异禀": ["天赋惊人", "天赋出众"],
    "气运加身": ["气运滔天", "运气爆棚"],
    "气势暴涨": ["气势飙升", "气势猛然提升"],
    "气势如虹": ["气势惊人", "气势磅礴"],
    "威压降临": ["压力骤增", "威压如山"],
    "能量暴动": ["能量紊乱", "灵力失控"],
    "法则之力": ["法则威能", "规则之力"],
    "大道共鸣": ["天地共鸣", "道音回响"],
    "天地异象": ["天降异象", "天地变色"],
    "风云变色": ["风云涌动", "天地变色"],
    "雷霆万钧": ["雷霆之势", "雷罚降临"],
    "排山倒海": ["势不可挡", "声势浩大"],
    "山崩地裂": ["地动山摇", "天崩地裂"],
    "石破天惊": ["惊天动地", "震古烁今"],
    "惊天动地": ["撼天动地", "震天撼地"],
    "匪夷所思": ["不可思议", "难以想象"],
    "不出所料": ["果然", "意料之中"],
    "豁然开朗": ["恍然大悟", "茅塞顿开"],
    "神识探查": ["神念扫过", "意念探查"],
    "储物戒指": ["纳戒", "空间戒指"],
    "灵力运转": ["灵力流转", "真元运转"],
    "功法运转": ["心法运转", "功法催动"],
    "突破桎梏": ["打破桎梏", "突破束缚"],
    "修为精进": ["修为提升", "功力大进"],
    "底蕴深厚": ["底蕴惊人", "根基扎实"],
    "天赋绝伦": ["天赋惊人", "天资卓绝"],
    "根骨奇佳": ["根骨惊人", "资质上乘"],
    "命格不凡": ["命格尊贵", "命数逆天"],
    "命数逆天": ["命格逆天", "气运惊人"],
    "好像": ["像", "看着像"],
    "宛若": ["像", "仿佛"],
    "恍若": ["仿佛", "好像"],
    "情不自禁": ["忍不住", "控制不住"],
    "忍不住": ["禁不住", "憋不住"],
    "心中一凛": ["心里一紧", "心头一凛"],
    "眼中寒芒": ["眼里寒光", "目光冰冷"],
    "眼中异色": ["眼里异色", "目光微动"],
    "嘴角勾起": ["嘴角翘了翘", "勾了勾嘴角"],
    "嘴角噙着": ["嘴角带着", "嘴角挂着"],
    "微微颔首": ["点了点头", "点头示意"],
    "缓缓点头": ["点了点头", "慢慢点头"],
    "缓缓闭上": ["慢慢闭上", "合上"],
    "淡淡开口": ["开口道", "淡声道"],
    "淡淡瞥了": ["扫了一眼", "淡瞥一眼"],
    "轻轻一笑": ["笑了笑", "轻笑"],
    "轻轻抚摸": ["轻抚", "摸了摸"],
    "深深叹息": ["叹了口气", "长叹一声"],
    "冷冷瞥了": ["冷扫一眼", "瞥了一眼"],
    "默默记下": ["记在心里", "暗自记下"],
    "默默观察": ["暗中观察", "静静看着"],
    "赫然在目": ["映入眼帘", "清晰可见"],
    "倒吸冷气": ["倒吸一口凉气", "吸了口冷气"],
    "瞳孔一缩": ["眼皮一跳", "瞳孔骤缩"],
    "瞳孔猛缩": ["瞳孔骤缩", "眼皮猛跳"],
    "心神剧震": ["心头巨震", "心里咯噔一下"],
    "气血上涌": ["血气上涌", "热血冲头"],
    "杀意沸腾": ["杀意滔天", "满身杀气"],
    "杀意冲天": ["杀意凛然", "杀气冲天"],
    "能量狂暴": ["能量紊乱", "灵力暴动"],
}


class HumanizeEngine:
    """人类化改写引擎"""

    def __init__(
        self,
        detector: AIRateDetector | None = None,
        strategies: list[HumanizeStrategy] | None = None,
        aggressive: float = 0.5,
    ):
        self.detector = detector or AIRateDetector()
        # 默认只使用经过验证有效的2种策略
        # replace_high_risk: 降AI率3-5% (替换20+处高危词)
        # remove_redundant: 降AI率2-3% (去除冗余修饰词)
        # 已验证反效果的策略:
        # split_long_paragraphs(+8%), add_human_phrases(+2%), vary_punctuation(+1%)
        self.strategies = strategies or [
            HumanizeStrategy.REPLACE_HIGH_RISK,
            HumanizeStrategy.REMOVE_REDUNDANT,
        ]
        self.aggressive = max(0.0, min(1.0, aggressive))

    def humanize(self, text: str) -> HumanizeResult:
        if not text or not text.strip():
            return HumanizeResult(original_text=text, modified_text=text)

        result = HumanizeResult(
            original_text=text,
            modified_text=text,
            word_count_before=len(text.replace(" ", "").replace("\n", "")),
        )

        before_report = self.detector.detect(text)
        result.ai_rate_before = before_report.total_score

        modified = text
        changes: list[dict[str, Any]] = []

        if HumanizeStrategy.REPLACE_HIGH_RISK in self.strategies:
            modified, count = self._replace_high_risk_words(modified)
            if count > 0:
                changes.append({"strategy": "replace_high_risk", "count": count})
                result.strategies_used.append("replace_high_risk")

        if HumanizeStrategy.REMOVE_REDUNDANT in self.strategies:
            modified, count = self._remove_redundant_modifiers(modified)
            if count > 0:
                changes.append({"strategy": "remove_redundant", "count": count})
                result.strategies_used.append("remove_redundant")

        if HumanizeStrategy.VARY_SENTENCE_LENGTH in self.strategies:
            modified, count = self._vary_sentence_length(modified)
            if count > 0:
                changes.append({"strategy": "vary_sentence_length", "count": count})
                result.strategies_used.append("vary_sentence_length")

        if HumanizeStrategy.ADD_HUMAN_PHRASES in self.strategies and self.aggressive > 0.3:
            modified, count = self._add_human_phrases(modified)
            if count > 0:
                changes.append({"strategy": "add_human_phrases", "count": count})
                result.strategies_used.append("add_human_phrases")

        if HumanizeStrategy.VARY_PUNCTUATION in self.strategies:
            modified, count = self._vary_punctuation(modified)
            if count > 0:
                changes.append({"strategy": "vary_punctuation", "count": count})
                result.strategies_used.append("vary_punctuation")

        if HumanizeStrategy.SPLIT_LONG_PARAGRAPHS in self.strategies:
            modified, count = self._split_long_paragraphs(modified)
            if count > 0:
                changes.append({"strategy": "split_long_paragraphs", "count": count})
                result.strategies_used.append("split_long_paragraphs")

        result.modified_text = modified
        result.changes = changes
        result.word_count_after = len(modified.replace(" ", "").replace("\n", ""))

        after_report = self.detector.detect(modified)
        result.ai_rate_after = after_report.total_score

        return result

    def _replace_high_risk_words(self, text: str):
        count = 0
        for ai_word, replacements in HIGH_RISK_REPLACEMENTS.items():
            if ai_word not in text:
                continue
            replace_prob = 0.7 + self.aggressive * 0.3
            occurrences = [m.start() for m in re.finditer(re.escape(ai_word), text)]
            to_replace = int(len(occurrences) * replace_prob)
            if to_replace == 0 and self.aggressive > 0.5:
                to_replace = 1
            for _ in range(to_replace):
                if not replacements:
                    continue
                replacement = random.choice(replacements)
                text = text.replace(ai_word, replacement, 1)
                count += 1
        return text, count

    def _remove_redundant_modifiers(self, text: str):
        count = 0
        redundant_patterns = [
            (r"微微(?=[点摇叹笑看])", ""),
            (r"轻轻(?=[摇叹笑抚拍])", ""),
            (r"缓缓(?=[开说道点闭])", ""),
            (r"淡淡(?=[一笑说道瞥开])", ""),
            (r"默默(?=[点记观然])", ""),
            (r"冷冷(?=[一笑说道瞥声])", ""),
            (r"深深(?=[看吸叹望])", ""),
            (r"渐渐(?=[消散变升])", ""),
            (r"慢慢(?=[说道走开])", ""),
        ]
        for pattern, replacement in redundant_patterns:
            matches = re.findall(pattern, text)
            if matches:
                remove_count = int(len(matches) * (0.5 + self.aggressive * 0.4))
                for _ in range(remove_count):
                    text = re.sub(pattern, replacement, text, count=1)
                    count += 1
        return text, count

    def _vary_sentence_length(self, text: str):
        count = 0
        sentences = re.split(r"(?<=[。！？])", text)
        result = []
        for s in sentences:
            if len(s) > 50 and self.aggressive > 0.2:
                parts = s.split("，")
                if len(parts) >= 3:
                    mid = len(parts) // 2
                    new_s = "，".join(parts[:mid]) + "。" + "，".join(parts[mid:])
                    result.append(new_s)
                    count += 1
                    continue
            result.append(s)
        return "".join(result), count

    def _add_human_phrases(self, text: str):
        count = 0
        exclamation_pattern = r"([^。！？\n]{5,30}[！？])"
        matches = list(re.finditer(exclamation_pattern, text))
        add_count = int(len(matches) * self.aggressive * 0.5)
        phrases = ["好家伙", "不得了", "厉害", "这也太", "真行", "可以啊", "不简单"]
        for i in range(min(add_count, len(matches))):
            match = matches[i]
            phrase = random.choice(phrases)
            insertion = f"（{phrase}）"
            pos = match.end()
            text = text[:pos] + insertion + text[pos:]
            count += 1
        return text, count

    def _vary_punctuation(self, text: str):
        count = 0
        periods = [m.start() for m in re.finditer(r"。", text)]
        if not periods:
            return text, count
        change_count = int(len(periods) * self.aggressive * 0.2)
        for _ in range(change_count):
            if not periods:
                break
            idx = random.choice(periods)
            periods.remove(idx)
            if random.random() < 0.5:
                text = text[:idx] + "……" + text[idx + 1 :]
                count += 1
        return text, count

    def _split_long_paragraphs(self, text: str):
        count = 0
        paragraphs = text.split("\n")
        result = []
        for p in paragraphs:
            if len(p) > 120 and self.aggressive > 0.3:
                sentences = re.split(r"(?<=[。！？])", p)
                if len(sentences) >= 3:
                    mid = len(sentences) // 2
                    new_p1 = "".join(sentences[:mid])
                    new_p2 = "".join(sentences[mid:])
                    result.append(new_p1)
                    result.append("")
                    result.append(new_p2)
                    count += 1
                    continue
            result.append(p)
        return "\n".join(result), count


# ══════════════════════════════════════════════════════
# AI率门禁（集成到昆仑引擎8道门禁系统）
# ══════════════════════════════════════════════════════


class AIGateKeeper:
    """AI率门禁 — 可作为昆仑引擎第9道门禁(G9)"""

    def __init__(
        self, threshold: float = 35.0, auto_humanize: bool = True, humanize_aggressive: float = 0.5
    ):
        self.detector = AIRateDetector(threshold=threshold)
        self.humanizer = HumanizeEngine(detector=self.detector, aggressive=humanize_aggressive)
        self.threshold = threshold
        self.auto_humanize = auto_humanize

    def check(self, text: str, chapter: int = 0, book_id: str = "") -> dict[str, Any]:
        report = self.detector.detect(text)
        result: dict[str, Any] = {
            "passed": report.is_pass,
            "ai_rate": report.total_score,
            "report": report,
            "chapter": chapter,
            "book_id": book_id,
            "humanized": False,
            "humanized_text": None,
            "ai_rate_after": None,
        }
        if not report.is_pass and self.auto_humanize:
            humanize_result = self.humanizer.humanize(text)
            result["humanized"] = True
            result["humanized_text"] = humanize_result.modified_text
            result["ai_rate_after"] = humanize_result.ai_rate_after
            result["strategies_used"] = humanize_result.strategies_used
            result["changes"] = humanize_result.changes
            result["passed"] = humanize_result.ai_rate_after <= self.threshold
        return result

    def batch_check(self, chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results = []
        for ch in chapters:
            result = self.check(ch.get("text", ""), ch.get("chapter", 0), ch.get("book_id", ""))
            results.append(result)
        return results


# ══════════════════════════════════════════════════════
# 便捷函数
# ══════════════════════════════════════════════════════


def detect_ai_rate(text: str, threshold: float = 35.0) -> AIRateReport:
    detector = AIRateDetector(threshold=threshold)
    return detector.detect(text)


def humanize_text(text: str, aggressive: float = 0.5) -> HumanizeResult:
    engine = HumanizeEngine(aggressive=aggressive)
    return engine.humanize(text)


def ai_gate_check(text: str, threshold: float = 35.0, auto_humanize: bool = True) -> dict[str, Any]:
    gate = AIGateKeeper(threshold=threshold, auto_humanize=auto_humanize)
    return gate.check(text)
