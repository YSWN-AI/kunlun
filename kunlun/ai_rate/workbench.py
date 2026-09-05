"""
昆仑创作引擎 — 降AI工作台核心逻辑

12维度AI率分析 + 8种改写策略，纯规则+词表实现，离线可用、零成本。
复用 kunlun.ai_rate.engine 的 AIRateDetector 和 HIGH_RISK_REPLACEMENTS。

核心函数:
  - analyze_text(text) -> AiAnalysisResult       12维度分析
  - humanize_with_strategy(text, strategies)      按策略改写
  - batch_process(texts, strategies)               批量处理
  - compare_before_after(original, rewritten)      前后对比
"""
# mypy: ignore-errors

from __future__ import annotations

import difflib
import math
import random
import re
from collections import Counter

from kunlun.ai_rate.models import (
    AiAnalysisResult,
    CompareResult,
    DiffSegment,
    DimensionInfo,
    DimensionScore,
    EditRecord,
    HumanizeResult,
    RiskPhrase,
    StrategyInfo,
)

# ═══════════════════════════════════════════════════════════════════════════
# 词表与常量
# ═══════════════════════════════════════════════════════════════════════════

# 维度权重（总和=1.0）
DIMENSION_WEIGHTS: dict[str, float] = {
    "vocab_repetition": 0.10,
    "sentence_monotony": 0.10,
    "connector_overuse": 0.08,
    "adjective_piling": 0.08,
    "adverb_abuse": 0.08,
    "template_expression": 0.10,
    "emotion_pattern": 0.06,
    "dialogue_tag_monotony": 0.06,
    "paragraph_structure": 0.08,
    "logic_word_density": 0.08,
    "formal_writing": 0.06,
    "rhetoric_poverty": 0.12,
}

DIMENSION_LABELS: dict[str, str] = {
    "vocab_repetition": "词汇重复率",
    "sentence_monotony": "句式单调性",
    "connector_overuse": "连接词过度",
    "adjective_piling": "形容词堆砌",
    "adverb_abuse": "副词滥用",
    "template_expression": "模板化表达",
    "emotion_pattern": "情感词模式化",
    "dialogue_tag_monotony": "对话标签单一",
    "paragraph_structure": "段落结构规整",
    "logic_word_density": "逻辑词密集",
    "formal_writing": "书面语过重",
    "rhetoric_poverty": "修辞贫乏",
}

DIMENSION_DESCRIPTIONS: dict[str, str] = {
    "vocab_repetition": "检测高频词重复使用情况，重复率越高AI特征越明显",
    "sentence_monotony": "检测句长方差和开头词重复，句式单一为AI典型特征",
    "connector_overuse": "检测因此/然而/此外等过渡词频率，过度使用显AI",
    "adjective_piling": "检测形容词密度，堆砌修饰语为AI写作通病",
    "adverb_abuse": "检测非常/十分/极其等程度副词滥用情况",
    "template_expression": "检测综上所述/值得注意的是等模板化套话",
    "emotion_pattern": "检测情感表达是否单一化、模式化",
    "dialogue_tag_monotony": "检测说道/问道等对话标签重复使用",
    "paragraph_structure": "检测段落长度是否过于均匀规整",
    "logic_word_density": "检测因为/所以/虽然/但是等逻辑词密度",
    "formal_writing": "检测过于正式的书面表达（之/其/此/乃等）",
    "rhetoric_poverty": "检测比喻/拟人/排比等修辞手法占比，修辞贫乏显AI",
}

# 连接词（过渡词）
CONNECTOR_WORDS: list[str] = [
    "因此",
    "然而",
    "此外",
    "另外",
    "同时",
    "总之",
    "综上",
    "由此",
    "进而",
    "继而",
    "再者",
    "况且",
    "何况",
    "乃至",
    "甚至",
    "尤其",
    "特别",
    "仅仅",
    "只不过",
    "与此同时",
    "不仅如此",
    "与此同时",
    "综上所述",
    "由此可见",
    "总而言之",
    "换言之",
    "也就是说",
    "换句话说",
    "另一方面",
    "除此之外",
]

# 模板化套话
TEMPLATE_PHRASES: list[str] = [
    "综上所述",
    "值得注意的是",
    "总而言之",
    "由此可见",
    "不难看出",
    "众所周知",
    "不言而喻",
    "毫无疑问",
    "毋庸置疑",
    "不可否认",
    "显而易见",
    "总的来说",
    "概括来说",
    "简而言之",
    "换言之",
    "也就是说",
    "换句话说",
    "由此可见",
    "从某种意义上说",
    "在一定程度上",
    "不可忽视的是",
    "需要指出的是",
    "必须承认",
    "事实证明",
    "研究表明",
    "数据显示",
    "据统计",
    "据了解",
    "据悉",
    "据报道",
]

# 程度副词
DEGREE_ADVERBS: list[str] = [
    "非常",
    "十分",
    "极其",
    "格外",
    "异常",
    "相当",
    "颇为",
    "略为",
    "极度",
    "万分",
    "无比",
    "尤为",
    "甚为",
    "极为",
    "分外",
    "越加",
    "愈发",
    "愈加",
    "越发",
    "最为",
    "更",
    "最",
    "太",
    "好",
    "真",
]

# 情感模式化短语（AI常用间接情感表达）
EMOTION_PATTERN_PHRASES: list[str] = [
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
    "缓缓开口",
    "缓缓说道",
    "淡淡一笑",
    "淡淡说道",
    "轻轻摇头",
    "轻轻叹息",
    "深深看了",
    "深深吸了",
    "冷冷一笑",
    "冷冷说道",
    "默默点头",
    "赫然发现",
    "定睛一看",
    "倒吸一口凉气",
    "瞳孔骤缩",
    "心神一震",
    "气血翻涌",
    "杀意凛然",
    "气势攀升",
    "威压笼罩",
    "不可思议",
    "难以置信",
    "果然如此",
    "原来如此",
    "恍然大悟",
]

# 对话标签
DIALOGUE_TAGS: list[str] = [
    "说道",
    "问道",
    "答道",
    "喊道",
    "叫道",
    "喝道",
    "怒道",
    "笑道",
    "冷笑",
    "冷哼",
    "低语",
    "喃喃",
    "嘀咕",
    "嘟囔",
    "应声",
    "接口",
    "插嘴",
    "打断",
    "开口",
    "回道",
    "答曰",
    "言",
    "曰",
    "说",
]

# 多样化对话标签替换池
DIALOGUE_TAG_VARIANTS: dict[str, list[str]] = {
    "说道": ["开口道", "缓声道", "沉声道", "淡声道", "平静道", "出声道"],
    "问道": ["追问", "询问", "质疑", "好奇道", "疑惑道", "挑眉道"],
    "答道": ["回道", "应声", "答曰", "坦言", "如实道", "郑重道"],
    "喊道": ["大叫", "高呼", "嘶吼", "咆哮", "厉喝", "暴喝"],
    "怒道": ["怒斥", "厉声", "沉喝", "火道", "炸毛道", "气冲冲道"],
    "笑道": ["轻笑", "莞尔", "哂笑", "揶揄道", "打趣道", "笑眯眯道"],
}

# 逻辑词
LOGIC_WORDS: list[str] = [
    "因为",
    "所以",
    "虽然",
    "但是",
    "如果",
    "那么",
    "既然",
    "即使",
    "无论",
    "只要",
    "只有",
    "不但",
    "而且",
    "不仅",
    "与其",
    "不如",
    "宁可",
    "于是",
    "因此",
    "故而",
    "因而",
    "从而",
    "以致",
    "以至",
]

# 书面语→口语替换映射
FORMAL_TO_COLLOQUIAL: dict[str, str] = {
    "之": "的",
    "其": "他",
    "此": "这",
    "乃": "是",
    "则": "就",
    "亦": "也",
    "且": "而且",
    "故": "所以",
    "然": "但是",
    "若": "如果",
    "如": "像",
    "于": "在",
    "以": "用",
    "为": "是",
    "所": "所",
    "者": "的人",
    "矣": "了",
    "焉": "了",
    "乎": "吗",
    "而已": "罢了",
    "尚且": "还",
    "况且": "再说",
    "乃至": "甚至",
    "并非": "不是",
    "予以": "给以",
    "加以": "进行",
    "进行": "做",
    "给予": "给",
    "对于": "对",
    "关于": "关于",
    "由于": "因为",
    "基于": "根据",
    "鉴于": "考虑到",
    "截至": "到",
    "致力于": "努力",
    "大幅度": "大幅",
    "全方位": "全面",
    "深层次": "深入",
    "高质量": "优质",
    "高水平": "高水准",
}

# 口语化语气词
ORAL_PARTICLES: list[str] = ["啊", "呢", "吧", "嘛", "啦", "哟", "哦", "呗", "嘞"]

# 比喻/拟人修辞标记词
RHETORIC_MARKERS: list[str] = [
    "像",
    "如",
    "仿佛",
    "似乎",
    "犹如",
    "宛如",
    "宛若",
    "好似",
    "好比",
    "如同",
    "恰似",
    "宛如",
    "犹如",
    "仿佛",
    "似乎",
    "一般",
    "一样",
    "似的",
    "般",
    "宛若",
    "恍若",
]

# 冗余修饰前缀（副词+动词模式）
REDUNDANT_MODIFIERS: list[tuple[str, str]] = [
    ("微微", "[点摇叹笑看皱眉颔首]"),
    ("轻轻", "[摇叹笑抚拍摸]"),
    ("缓缓", "[开说道点闭走]"),
    ("淡淡", "[一笑说道瞥开口]"),
    ("默默", "[点记观然看]"),
    ("冷冷", "[一笑说道瞥声喝]"),
    ("深深", "[看吸叹望吸]"),
    ("渐渐", "[消散变升远去]"),
    ("慢慢", "[说道走开转]"),
    ("静静", "[看立站等想]"),
    ("暗暗", "[想道记发誓]"),
    ("偷偷", "[看瞄摸摸走]"),
]

# ═══════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════


def _split_sentences(text: str) -> list[str]:
    """按中文句末标点切分句子。"""
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[。！？!?…])", text)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) > 1]


def _split_paragraphs(text: str) -> list[str]:
    """按换行切分段落，过滤空段落。"""
    return [p.strip() for p in text.split("\n") if p.strip()]


def _find_all_positions(text: str, phrase: str) -> list[tuple[int, int]]:
    """查找短语在文本中的所有位置，返回 (start, end) 列表。"""
    positions: list[tuple[int, int]] = []
    start = 0
    while True:
        idx = text.find(phrase, start)
        if idx == -1:
            break
        positions.append((idx, idx + len(phrase)))
        start = idx + 1
    return positions


def _score_level(score: float) -> str:
    """根据分数返回风险等级。"""
    if score < 30:
        return "low"
    if score < 60:
        return "medium"
    return "high"


def _overall_level(score: float) -> str:
    """根据总体AI率返回等级。"""
    if score < 20:
        return "very_low"
    if score < 35:
        return "low"
    if score < 50:
        return "medium"
    if score < 70:
        return "high"
    return "very_high"


def _word_count(text: str) -> int:
    """计算中文字数（去除空白和换行）。"""
    return len(text.replace(" ", "").replace("\n", "").replace("\t", ""))


# ═══════════════════════════════════════════════════════════════════════════
# 12维度分析器
# ═══════════════════════════════════════════════════════════════════════════


class AiWorkbenchAnalyzer:
    """12维度AI率分析器，纯规则实现。"""

    def __init__(self) -> None:
        self.risk_phrases: list[RiskPhrase] = []

    def analyze(self, text: str) -> AiAnalysisResult:
        """执行12维度分析。"""
        if not text or not text.strip():
            return AiAnalysisResult(
                overall_score=0,
                level="very_low",
                dimensions=[],
                risk_phrases=[],
                summary="文本为空",
            )

        self.risk_phrases = []
        wc = _word_count(text)
        sentences = _split_sentences(text)
        paragraphs = _split_paragraphs(text)

        dimensions: list[DimensionScore] = []
        dimensions.append(self._dim_vocab_repetition(text, wc))
        dimensions.append(self._dim_sentence_monotony(text, sentences))
        dimensions.append(self._dim_connector_overuse(text, wc))
        dimensions.append(self._dim_adjective_piling(text, wc))
        dimensions.append(self._dim_adverb_abuse(text, wc))
        dimensions.append(self._dim_template_expression(text, wc))
        dimensions.append(self._dim_emotion_pattern(text, wc))
        dimensions.append(self._dim_dialogue_tag_monotony(text, wc))
        dimensions.append(self._dim_paragraph_structure(text, paragraphs))
        dimensions.append(self._dim_logic_word_density(text, wc))
        dimensions.append(self._dim_formal_writing(text, wc))
        dimensions.append(self._dim_rhetoric_poverty(text, wc, sentences))

        # 加权总分
        total_weight = sum(DIMENSION_WEIGHTS.values())
        weighted = sum(d.score * DIMENSION_WEIGHTS.get(d.name, 0) for d in dimensions)
        overall = min(100.0, weighted / total_weight * 1.15) if total_weight > 0 else 0

        # 生成摘要
        top_dims = sorted(dimensions, key=lambda d: d.score, reverse=True)[:3]
        top_str = "、".join(f"{d.label}({d.score:.0f})" for d in top_dims)
        level = _overall_level(overall)
        level_cn = {
            "very_low": "极低",
            "low": "较低",
            "medium": "中等",
            "high": "较高",
            "very_high": "极高",
        }[level]
        summary = (
            f"AI率: {overall:.1f}/100 ({level_cn}) | "
            f"字数: {wc} | 句子: {len(sentences)} | 段落: {len(paragraphs)} | "
            f"风险短语: {len(self.risk_phrases)}处 | "
            f"主要AI特征: {top_str}"
        )

        return AiAnalysisResult(
            overall_score=round(overall, 1),
            level=level,
            dimensions=dimensions,
            risk_phrases=self.risk_phrases,
            summary=summary,
            word_count=wc,
            sentence_count=len(sentences),
            paragraph_count=len(paragraphs),
        )

    def _add_risk(
        self, text: str, phrase: str, dimension: str, reason: str, severity: str = "medium"
    ) -> None:
        """添加风险短语（自动查找所有位置）。"""
        for start, end in _find_all_positions(text, phrase):
            self.risk_phrases.append(
                RiskPhrase(
                    text=phrase,
                    start=start,
                    end=end,
                    dimension=dimension,
                    reason=reason,
                    severity=severity,
                )
            )

    # ── 维度1: 词汇重复率 ──
    def _dim_vocab_repetition(self, text: str, wc: int) -> DimensionScore:
        # 提取2-4字词，统计重复
        words: list[str] = []
        for length in (2, 3, 4):
            for i in range(len(text) - length + 1):
                w = text[i : i + length]
                if re.match(r"^[\u4e00-\u9fa5]{" + str(length) + r"}$", w):
                    words.append(w)
        counter = Counter(words)
        repeated = {w: c for w, c in counter.items() if c >= 3}
        repeat_count = sum(c - 1 for c in repeated.values())
        density = repeat_count / max(1, wc / 1000)
        score = min(100, density * 8)

        suggestions: list[str] = []
        if score > 40:
            top = sorted(repeated.items(), key=lambda x: x[1], reverse=True)[:5]
            suggestions.append(f"高频重复词: {'、'.join(f'{w}({c}次)' for w, c in top)}")
            suggestions.append("建议使用同义词替换或调整句式避免重复")
            for w, c in list(repeated.items())[:10]:
                if c >= 4:
                    self._add_risk(text, w, "vocab_repetition", f"重复出现{c}次", "medium")

        return DimensionScore(
            name="vocab_repetition",
            label=DIMENSION_LABELS["vocab_repetition"],
            score=round(score, 1),
            level=_score_level(score),
            suggestions=suggestions,
            detail={"repeat_density_per_1k": round(density, 1), "repeated_words": len(repeated)},
        )

    # ── 维度2: 句式单调性 ──
    def _dim_sentence_monotony(self, _text: str, sentences: list[str]) -> DimensionScore:
        if len(sentences) < 3:
            return DimensionScore(
                name="sentence_monotony",
                label=DIMENSION_LABELS["sentence_monotony"],
                score=0,
                level="low",
                detail={"sentence_count": len(sentences)},
            )

        lengths = [len(s) for s in sentences]
        mean_len = sum(lengths) / len(lengths)
        variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
        std_dev = math.sqrt(variance)
        cv = std_dev / max(1, mean_len)

        # 开头词重复检测
        openings = [s[:2] for s in sentences if len(s) >= 2]
        opening_counter = Counter(openings)
        opening_repeats = sum(c - 1 for c in opening_counter.values() if c >= 2)

        score = max(0, min(100, (0.35 - cv) * 250 + opening_repeats * 8))

        suggestions: list[str] = []
        if score > 40:
            suggestions.append(f"句长变异系数{cv:.2f}，建议长短句交替使用")
            if opening_repeats > 0:
                top_open = opening_counter.most_common(3)
                suggestions.append(f"开头重复: {'、'.join(f'{w}({c}次)' for w, c in top_open)}")

        return DimensionScore(
            name="sentence_monotony",
            label=DIMENSION_LABELS["sentence_monotony"],
            score=round(score, 1),
            level=_score_level(score),
            suggestions=suggestions,
            detail={
                "mean_length": round(mean_len, 1),
                "std_dev": round(std_dev, 1),
                "cv": round(cv, 3),
                "opening_repeats": opening_repeats,
            },
        )

    # ── 维度3: 连接词过度 ──
    def _dim_connector_overuse(self, text: str, wc: int) -> DimensionScore:
        total = 0
        found: list[str] = []
        for w in CONNECTOR_WORDS:
            c = text.count(w)
            if c > 0:
                total += c
                found.append(w)
                if c >= 2:
                    self._add_risk(text, w, "connector_overuse", f"过渡词出现{c}次", "low")
        density = total / max(1, wc / 1000)
        score = min(100, density * 4)

        suggestions: list[str] = []
        if score > 40:
            suggestions.append(f"过渡词密度{density:.1f}/千字，建议减少因此/然而/此外等")
            suggestions.append("可通过分句或隐含逻辑关系替代显性连接词")

        return DimensionScore(
            name="connector_overuse",
            label=DIMENSION_LABELS["connector_overuse"],
            score=round(score, 1),
            level=_score_level(score),
            suggestions=suggestions,
            detail={
                "density_per_1k": round(density, 1),
                "total_connectors": total,
                "types": len(found),
            },
        )

    # ── 维度4: 形容词堆砌 ──
    def _dim_adjective_piling(self, text: str, wc: int) -> DimensionScore:
        # "的"字密度 + 连续形容词模式
        de_count = text.count("的")
        # 检测 "XX的XX的XX" 模式（连续修饰）
        pile_pattern = re.findall(r"[\u4e00-\u9fa5]{1,4}的[\u4e00-\u9fa5]{1,4}的", text)
        pile_count = len(pile_pattern)
        # 检测 "非常XX的" "十分XX的" 等程度+形容+的
        degree_de = re.findall(
            r"(?:非常|十分|极其|格外|异常|相当|颇为)[\u4e00-\u9fa5]{1,3}的", text
        )
        degree_de_count = len(degree_de)

        total = de_count + pile_count * 3 + degree_de_count * 2
        density = total / max(1, wc / 1000)
        score = min(100, density * 3)

        suggestions: list[str] = []
        if score > 40:
            de_density = de_count / max(1, wc / 1000)
            suggestions.append(f"的字密度{de_density:.1f}/千字，存在{pile_count}处连续修饰")
            suggestions.append("建议减少形容词叠加，用动词和细节替代修饰语")
            for pat in pile_pattern[:5]:
                self._add_risk(text, pat, "adjective_piling", "连续形容词修饰", "low")

        return DimensionScore(
            name="adjective_piling",
            label=DIMENSION_LABELS["adjective_piling"],
            score=round(score, 1),
            level=_score_level(score),
            suggestions=suggestions,
            detail={
                "de_count": de_count,
                "pile_count": pile_count,
                "degree_de_count": degree_de_count,
                "density_per_1k": round(density, 1),
            },
        )

    # ── 维度5: 副词滥用 ──
    def _dim_adverb_abuse(self, text: str, wc: int) -> DimensionScore:
        total = 0
        for w in DEGREE_ADVERBS:
            c = text.count(w)
            if c > 0:
                total += c
                if c >= 3:
                    self._add_risk(text, w, "adverb_abuse", f"程度副词出现{c}次", "medium")
        density = total / max(1, wc / 1000)
        score = min(100, density * 5)

        suggestions: list[str] = []
        if score > 40:
            top = sorted(
                ((w, text.count(w)) for w in DEGREE_ADVERBS if text.count(w) > 0),
                key=lambda x: x[1],
                reverse=True,
            )[:5]
            top_str = "、".join(f"{w}({c})" for w, c in top)
            suggestions.append(f"程度副词密度{density:.1f}/千字: {top_str}")
            suggestions.append("建议用具体描写替代程度副词，如'非常快'→'快如闪电'")

        return DimensionScore(
            name="adverb_abuse",
            label=DIMENSION_LABELS["adverb_abuse"],
            score=round(score, 1),
            level=_score_level(score),
            suggestions=suggestions,
            detail={"density_per_1k": round(density, 1), "total_adverbs": total},
        )

    # ── 维度6: 模板化表达 ──
    def _dim_template_expression(self, text: str, wc: int) -> DimensionScore:
        total = 0
        for phrase in TEMPLATE_PHRASES:
            c = text.count(phrase)
            if c > 0:
                total += c
                self._add_risk(text, phrase, "template_expression", "模板化套话", "high")
        density = total / max(1, wc / 1000)
        score = min(100, density * 15 + total * 5)

        suggestions: list[str] = []
        if score > 30:
            suggestions.append(f"检测到{total}处模板化套话，建议全部删除或改写")
            suggestions.append("AI生成文本高频使用综上所述/值得注意的是等套话，人类写作极少使用")

        return DimensionScore(
            name="template_expression",
            label=DIMENSION_LABELS["template_expression"],
            score=round(score, 1),
            level=_score_level(score),
            suggestions=suggestions,
            detail={"total_phrases": total, "density_per_1k": round(density, 1)},
        )

    # ── 维度7: 情感词模式化 ──
    def _dim_emotion_pattern(self, text: str, wc: int) -> DimensionScore:
        total = 0
        for phrase in EMOTION_PATTERN_PHRASES:
            c = text.count(phrase)
            if c > 0:
                total += c
                if c >= 2:
                    self._add_risk(text, phrase, "emotion_pattern", "AI模式化情感表达", "medium")
        density = total / max(1, wc / 1000)
        score = min(100, density * 10)

        suggestions: list[str] = []
        if score > 40:
            suggestions.append(f"模式化情感表达密度{density:.1f}/千字")
            suggestions.append("建议用动作/细节/对话传达情感，减少心中XX/眼中XX等间接表达")

        return DimensionScore(
            name="emotion_pattern",
            label=DIMENSION_LABELS["emotion_pattern"],
            score=round(score, 1),
            level=_score_level(score),
            suggestions=suggestions,
            detail={"density_per_1k": round(density, 1), "total_patterns": total},
        )

    # ── 维度8: 对话标签单一 ──
    def _dim_dialogue_tag_monotony(self, text: str, _wc: int) -> DimensionScore:
        tag_counts: dict[str, int] = {}
        for tag in DIALOGUE_TAGS:
            c = len(re.findall(re.escape(tag) + r"(?=[，。！？\s\"」』])", text))
            if c > 0:
                tag_counts[tag] = c
        total_tags = sum(tag_counts.values())
        if total_tags == 0:
            return DimensionScore(
                name="dialogue_tag_monotony",
                label=DIMENSION_LABELS["dialogue_tag_monotony"],
                score=0,
                level="low",
                detail={"total_tags": 0},
            )

        # 计算标签多样性（辛普森指数的倒数）
        unique_tags = len(tag_counts)
        top_tag = max(tag_counts, key=tag_counts.get)
        top_ratio = tag_counts[top_tag] / total_tags

        score = 0
        if top_ratio > 0.6:
            score += (top_ratio - 0.6) * 200
        if unique_tags <= 2 and total_tags >= 3:
            score += 30
        score = min(100, score)

        suggestions: list[str] = []
        if score > 30:
            suggestions.append(f"对话标签'{top_tag}'占比{top_ratio * 100:.0f}%，过于单一")
            suggestions.append("建议使用笑道/冷哼/低语/喃喃等多样化标签")
            if tag_counts.get("说道", 0) >= 2:
                self._add_risk(text, "说道", "dialogue_tag_monotony", "对话标签单一", "low")

        return DimensionScore(
            name="dialogue_tag_monotony",
            label=DIMENSION_LABELS["dialogue_tag_monotony"],
            score=round(score, 1),
            level=_score_level(score),
            suggestions=suggestions,
            detail={
                "total_tags": total_tags,
                "unique_tags": unique_tags,
                "top_tag": top_tag,
                "top_ratio": round(top_ratio, 2),
            },
        )

    # ── 维度9: 段落结构规整 ──
    def _dim_paragraph_structure(self, _text: str, paragraphs: list[str]) -> DimensionScore:
        if len(paragraphs) < 2:
            return DimensionScore(
                name="paragraph_structure",
                label=DIMENSION_LABELS["paragraph_structure"],
                score=0,
                level="low",
                detail={"paragraph_count": len(paragraphs)},
            )

        lengths = [len(p) for p in paragraphs]
        mean_len = sum(lengths) / len(lengths)
        variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
        std_dev = math.sqrt(variance)
        cv = std_dev / max(1, mean_len)

        short_ratio = sum(1 for l in lengths if l < 20) / len(lengths)
        long_ratio = sum(1 for l in lengths if l > 200) / len(lengths)

        score = 0
        if cv < 0.3:
            score += (0.3 - cv) * 200
        if short_ratio < 0.1:
            score += 25
        if long_ratio > 0.4:
            score += 25
        score = min(100, score)

        suggestions: list[str] = []
        if score > 40:
            suggestions.append(f"段落长度变异系数{cv:.2f}，平均{mean_len:.0f}字，结构过于规整")
            suggestions.append("建议增加1-3句的短段落，拆分超过200字的长段落")

        return DimensionScore(
            name="paragraph_structure",
            label=DIMENSION_LABELS["paragraph_structure"],
            score=round(score, 1),
            level=_score_level(score),
            suggestions=suggestions,
            detail={
                "mean_length": round(mean_len, 1),
                "cv": round(cv, 3),
                "short_ratio": round(short_ratio, 2),
                "long_ratio": round(long_ratio, 2),
            },
        )

    # ── 维度10: 逻辑词密集 ──
    def _dim_logic_word_density(self, text: str, wc: int) -> DimensionScore:
        total = 0
        for w in LOGIC_WORDS:
            c = text.count(w)
            if c > 0:
                total += c
                if c >= 3:
                    self._add_risk(text, w, "logic_word_density", f"逻辑词出现{c}次", "low")
        density = total / max(1, wc / 1000)
        score = min(100, density * 4)

        suggestions: list[str] = []
        if score > 40:
            suggestions.append(f"逻辑词密度{density:.1f}/千字，建议减少因为/所以/虽然/但是")
            suggestions.append("可通过语序调整隐含逻辑关系，不必每处都用显性逻辑词")

        return DimensionScore(
            name="logic_word_density",
            label=DIMENSION_LABELS["logic_word_density"],
            score=round(score, 1),
            level=_score_level(score),
            suggestions=suggestions,
            detail={"density_per_1k": round(density, 1), "total_logic_words": total},
        )

    # ── 维度11: 书面语过重 ──
    def _dim_formal_writing(self, text: str, wc: int) -> DimensionScore:
        total = 0
        formal_chars = ["之", "其", "此", "乃", "则", "亦", "且", "故", "然", "若", "矣", "焉"]
        for ch in formal_chars:
            c = text.count(ch)
            if c > 0:
                total += c
        # 多字书面语
        formal_phrases = [
            "并非",
            "予以",
            "加以",
            "给予",
            "对于",
            "由于",
            "基于",
            "鉴于",
            "致力于",
            "大幅度",
        ]
        phrase_count = sum(text.count(p) for p in formal_phrases)
        total += phrase_count * 2

        density = total / max(1, wc / 1000)
        score = min(100, density * 3)

        suggestions: list[str] = []
        if score > 40:
            suggestions.append(f"书面语密度{density:.1f}/千字，建议替换为口语化表达")
            suggestions.append("之→的、其→他/它、此→这、乃→是、亦→也")

        return DimensionScore(
            name="formal_writing",
            label=DIMENSION_LABELS["formal_writing"],
            score=round(score, 1),
            level=_score_level(score),
            suggestions=suggestions,
            detail={"density_per_1k": round(density, 1), "total_formal": total},
        )

    # ── 维度12: 修辞贫乏 ──
    def _dim_rhetoric_poverty(self, text: str, wc: int, sentences: list[str]) -> DimensionScore:
        # 比喻标记
        metaphor_count = sum(text.count(m) for m in RHETORIC_MARKERS)
        # 排比检测：连续3句以上相同开头或相同句式
        parallel_count = 0
        if len(sentences) >= 3:
            for i in range(len(sentences) - 2):
                if (
                    sentences[i][:1] == sentences[i + 1][:1] == sentences[i + 2][:1]
                    and len(sentences[i][:1]) > 0
                ):
                    parallel_count += 1
        # 拟人检测（较难，用"XX的XX" + 动词模式粗略估计）
        _person_re = (
            r"[\u4e00-\u9fa5]{2,4}(?:的|地)?"
            r"(?:微笑|叹息|低语|怒吼|奔跑|沉睡|苏醒|哭泣|欢笑)"
        )
        personification_patterns = re.findall(_person_re, text)
        personification_count = len(personification_patterns)

        total_rhetoric = metaphor_count + parallel_count * 3 + personification_count * 2
        density = total_rhetoric / max(1, wc / 1000)

        # 修辞越少分越高（AI特征）
        if density < 2:
            score = 80
        elif density < 5:
            score = 50
        elif density < 10:
            score = 25
        else:
            score = 10

        suggestions: list[str] = []
        if score > 40:
            suggestions.append(f"修辞密度仅{density:.1f}/千字，比喻/拟人/排比严重不足")
            suggestions.append("建议在描写场景和人物时注入比喻（像/如/仿佛）和拟人手法")

        return DimensionScore(
            name="rhetoric_poverty",
            label=DIMENSION_LABELS["rhetoric_poverty"],
            score=round(score, 1),
            level=_score_level(score),
            suggestions=suggestions,
            detail={
                "metaphor_count": metaphor_count,
                "parallel_count": parallel_count,
                "personification_count": personification_count,
                "density_per_1k": round(density, 1),
            },
        )


# ═══════════════════════════════════════════════════════════════════════════
# 8种改写策略执行器
# ═══════════════════════════════════════════════════════════════════════════


class AiWorkbenchHumanizer:
    """按指定策略改写文本，记录修改映射。"""

    def __init__(self, aggressive: float = 0.6) -> None:
        self.aggressive = max(0.0, min(1.0, aggressive))
        self.analyzer = AiWorkbenchAnalyzer()

    def humanize(self, text: str, strategies: list[str]) -> HumanizeResult:
        """按策略列表依次执行改写。"""
        if not text or not text.strip():
            return HumanizeResult(original_text=text, rewritten_text=text)

        before = self.analyzer.analyze(text)
        modified = text
        edit_records: list[EditRecord] = []
        used: list[str] = []

        strategy_map = {
            "replace_high_risk": self._strategy_replace_high_risk,
            "remove_redundancy": self._strategy_remove_redundancy,
            "restructure_sentence": self._strategy_restructure_sentence,
            "diversify_dialogue": self._strategy_diversify_dialogue,
            "add_oral_expression": self._strategy_add_oral_expression,
            "break_paragraph": self._strategy_break_paragraph,
            "inject_rhetoric": self._strategy_inject_rhetoric,
            "simplify_writing": self._strategy_simplify_writing,
        }

        for sid in strategies:
            func = strategy_map.get(sid)
            if func is None:
                continue
            modified, records = func(modified)
            if records:
                edit_records.extend(records)
                used.append(sid)

        after = self.analyzer.analyze(modified)

        return HumanizeResult(
            original_text=text,
            rewritten_text=modified,
            edit_records=edit_records,
            before_score=before.overall_score,
            after_score=after.overall_score,
            strategies_used=used,
            word_count_before=_word_count(text),
            word_count_after=_word_count(modified),
        )

    # ── 策略1: 替换高危AI词汇 ──
    def _strategy_replace_high_risk(self, text: str) -> tuple[str, list[EditRecord]]:
        from kunlun.ai_rate.engine import HIGH_RISK_REPLACEMENTS

        records: list[EditRecord] = []
        replace_prob = 0.6 + self.aggressive * 0.4

        for ai_word, replacements in HIGH_RISK_REPLACEMENTS.items():
            if ai_word not in text or not replacements:
                continue
            occurrences = [m.start() for m in re.finditer(re.escape(ai_word), text)]
            to_replace = max(1, int(len(occurrences) * replace_prob))
            for i in range(min(to_replace, len(occurrences))):
                pos = occurrences[i]
                replacement = random.choice(replacements)
                # 记录原始位置（替换前）
                records.append(
                    EditRecord(
                        original=ai_word,
                        replaced=replacement,
                        position=pos,
                        strategy="replace_high_risk",
                        description="高危AI词替换",
                    )
                )
                text = text[:pos] + replacement + text[pos + len(ai_word) :]
                # 重新计算后续位置偏移
                offset = len(replacement) - len(ai_word)
                for j in range(i + 1, len(occurrences)):
                    occurrences[j] += offset

        return text, records

    # ── 策略2: 去除冗余修饰和套话 ──
    def _strategy_remove_redundancy(self, text: str) -> tuple[str, list[EditRecord]]:
        records: list[EditRecord] = []

        # 去除模板化套话
        for phrase in TEMPLATE_PHRASES:
            while phrase in text:
                pos = text.find(phrase)
                records.append(
                    EditRecord(
                        original=phrase,
                        replaced="",
                        position=pos,
                        strategy="remove_redundancy",
                        description="删除模板化套话",
                    )
                )
                text = text[:pos] + text[pos + len(phrase) :]

        # 去除冗余副词前缀（微微/轻轻/缓缓 + 动词）
        for prefix, verb_pattern in REDUNDANT_MODIFIERS:
            pattern = re.compile(re.escape(prefix) + verb_pattern)
            matches = list(pattern.finditer(text))
            remove_count = int(len(matches) * (0.4 + self.aggressive * 0.4))
            for i in range(min(remove_count, len(matches))):
                m = matches[i]
                # 只删除前缀，保留动词
                records.append(
                    EditRecord(
                        original=prefix,
                        replaced="",
                        position=m.start(),
                        strategy="remove_redundancy",
                        description=f"删除冗余修饰前缀'{prefix}'",
                    )
                )
                text = text[: m.start()] + text[m.start() + len(prefix) :]
                # 重新匹配以更新位置
                matches = list(pattern.finditer(text))

        return text, records

    # ── 策略3: 句式重构 ──
    def _strategy_restructure_sentence(self, text: str) -> tuple[str, list[EditRecord]]:
        records: list[EditRecord] = []
        sentences = _split_sentences(text)
        if len(sentences) < 2:
            return text, records

        result_parts: list[str] = []
        pos_offset = 0
        for sent in sentences:
            original_s = sent
            current = sent
            # 长句拆分（>50字且含逗号）
            _split_prob = 0.5 + self.aggressive * 0.3
            if len(current) > 50 and "，" in current and random.random() < _split_prob:
                parts = current.split("，")
                if len(parts) >= 3:
                    mid = len(parts) // 2
                    new_s = "，".join(parts[:mid]) + "。" + "，".join(parts[mid:])
                    records.append(
                        EditRecord(
                            original=original_s,
                            replaced=new_s,
                            position=pos_offset,
                            strategy="restructure_sentence",
                            description="长句拆分为两个短句",
                        )
                    )
                    current = new_s
            # 短句合并（连续两句都<15字）
            elif len(current) < 15 and result_parts and len(result_parts[-1]) < 20:
                prev = result_parts[-1]
                merged = prev.rstrip("。！？") + "，" + current
                records.append(
                    EditRecord(
                        original=prev + "|" + current,
                        replaced=merged,
                        position=max(0, pos_offset - len(prev)),
                        strategy="restructure_sentence",
                        description="短句合并",
                    )
                )
                result_parts[-1] = merged
                pos_offset += len(current)
                continue

            result_parts.append(current)
            pos_offset += len(current)

        return "".join(result_parts), records

    # ── 策略4: 对话标签多样化 ──
    def _strategy_diversify_dialogue(self, text: str) -> tuple[str, list[EditRecord]]:
        records: list[EditRecord] = []

        for tag, variants in DIALOGUE_TAG_VARIANTS.items():
            pattern = re.compile(re.escape(tag) + r"(?=[，。！？\s\"」』])")
            matches = list(pattern.finditer(text))
            replace_count = int(len(matches) * (0.5 + self.aggressive * 0.4))
            for i in range(min(replace_count, len(matches))):
                m = matches[i]
                variant = random.choice(variants)
                records.append(
                    EditRecord(
                        original=tag,
                        replaced=variant,
                        position=m.start(),
                        strategy="diversify_dialogue",
                        description=f"对话标签多样化: {tag}→{variant}",
                    )
                )
                text = text[: m.start()] + variant + text[m.end() :]
                offset = len(variant) - len(tag)
                for j in range(i + 1, len(matches)):
                    # 更新后续匹配位置
                    old_start = matches[j].start()
                    matches[j] = re.compile(pattern.pattern).search(text, old_start + offset)
                    if matches[j] is None:
                        break

        return text, records

    # ── 策略5: 增加口语化表达 ──
    def _strategy_add_oral_expression(self, text: str) -> tuple[str, list[EditRecord]]:
        records: list[EditRecord] = []

        # 在对话句子末尾添加语气词
        dialogue_pattern = re.compile(r'([「『"][^」』"]{2,30})([」』"])(?=[，。！？])')
        matches = list(dialogue_pattern.finditer(text))
        add_count = int(len(matches) * (0.3 + self.aggressive * 0.4))
        for i in range(min(add_count, len(matches))):
            m = matches[i]
            particle = random.choice(ORAL_PARTICLES)
            # 在引号内末尾添加语气词
            insert_pos = m.end() - 1  # 引号前
            records.append(
                EditRecord(
                    original=m.group(0),
                    replaced=m.group(1) + particle + m.group(2),
                    position=m.start(),
                    strategy="add_oral_expression",
                    description=f"对话末尾添加语气词'{particle}'",
                )
            )
            text = text[:insert_pos] + particle + text[insert_pos:]

        # 在陈述句末尾（非对话）偶尔添加"呢""吧"
        stmt_pattern = re.compile(r'([\u4e00-\u9fa5]{4,20})。(?!\s*[「『"])')
        matches = list(stmt_pattern.finditer(text))
        add_count2 = int(len(matches) * (0.1 + self.aggressive * 0.2))
        for i in range(min(add_count2, len(matches))):
            m = matches[i]
            particle = random.choice(["呢", "吧", "嘛"])
            insert_pos = m.end() - 1  # 句号前
            records.append(
                EditRecord(
                    original=m.group(0),
                    replaced=m.group(1) + particle + "。",
                    position=m.start(),
                    strategy="add_oral_expression",
                    description=f"陈述句添加语气词'{particle}'",
                )
            )
            text = text[:insert_pos] + particle + text[insert_pos:]

        return text, records

    # ── 策略6: 打破规整段落结构 ──
    def _strategy_break_paragraph(self, text: str) -> tuple[str, list[EditRecord]]:
        records: list[EditRecord] = []
        paragraphs = text.split("\n")
        result: list[str] = []
        pos_offset = 0

        for p in paragraphs:
            if not p.strip():
                result.append(p)
                pos_offset += len(p) + 1
                continue

            # 长段落拆分（>150字）
            if len(p) > 150 and random.random() < 0.5 + self.aggressive * 0.3:
                sentences = _split_sentences(p)
                if len(sentences) >= 3:
                    mid = len(sentences) // 2
                    p1 = "".join(sentences[:mid])
                    p2 = "".join(sentences[mid:])
                    records.append(
                        EditRecord(
                            original=p[:50] + "..." if len(p) > 50 else p,
                            replaced=p1[:30] + "... | " + p2[:30] + "...",
                            position=pos_offset,
                            strategy="break_paragraph",
                            description=f"长段落({len(p)}字)拆分为两段",
                        )
                    )
                    result.append(p1)
                    result.append("")
                    result.append(p2)
                    pos_offset += len(p) + 1
                    continue

            # 中等段落中提取一句作为独立短段落
            if 80 < len(p) < 150 and random.random() < 0.2 + self.aggressive * 0.2:
                sentences = _split_sentences(p)
                if len(sentences) >= 2:
                    split_idx = random.randint(1, len(sentences) - 1)
                    p1 = "".join(sentences[:split_idx])
                    p2 = "".join(sentences[split_idx:])
                    records.append(
                        EditRecord(
                            original=p[:40] + "...",
                            replaced=p1[:20] + "... | " + p2[:20] + "...",
                            position=pos_offset,
                            strategy="break_paragraph",
                            description="段落拆分为长短两段",
                        )
                    )
                    result.append(p1)
                    result.append("")
                    result.append(p2)
                    pos_offset += len(p) + 1
                    continue

            result.append(p)
            pos_offset += len(p) + 1

        return "\n".join(result), records

    # ── 策略7: 注入修辞手法 ──
    def _strategy_inject_rhetoric(self, text: str) -> tuple[str, list[EditRecord]]:
        records: list[EditRecord] = []

        # 在描写性句子中注入比喻
        # 匹配 "XX很XX" "XX非常XX" 等描述模式
        desc_pattern = re.compile(
            r"([\u4e00-\u9fa5]{2,6})(?:很|非常|十分|极其|格外)([\u4e00-\u9fa5]{1,3})"
        )
        matches = list(desc_pattern.finditer(text))
        inject_count = int(len(matches) * (0.3 + self.aggressive * 0.4))

        metaphor_templates = [
            "像{obj}一样{adj}",
            "如同{obj}般{adj}",
            "仿佛{obj}似的{adj}",
            "宛如{obj}，{adj}得很",
        ]
        metaphor_objects = ["潮水", "烈火", "寒冰", "钢铁", "狂风", "山岳", "星辰", "流水"]

        for i in range(min(inject_count, len(matches))):
            m = matches[i]
            obj = random.choice(metaphor_objects)
            adj = m.group(2)
            template = random.choice(metaphor_templates)
            replacement = template.format(obj=obj, adj=adj)
            records.append(
                EditRecord(
                    original=m.group(0),
                    replaced=replacement,
                    position=m.start(),
                    strategy="inject_rhetoric",
                    description=f"注入比喻修辞: {m.group(0)}→{replacement}",
                )
            )
            text = text[: m.start()] + replacement + text[m.end() :]
            offset = len(replacement) - len(m.group(0))
            for j in range(i + 1, len(matches)):
                matches[j] = desc_pattern.search(text, matches[j].start() + offset)
                if matches[j] is None:
                    break

        return text, records

    # ── 策略8: 简化过于书面的表达 ──
    def _strategy_simplify_writing(self, text: str) -> tuple[str, list[EditRecord]]:
        records: list[EditRecord] = []

        # 先替换多字书面语（避免单字替换误伤）
        multi_formal = {k: v for k, v in FORMAL_TO_COLLOQUIAL.items() if len(k) >= 2}
        sorted_items = sorted(multi_formal.items(), key=lambda x: len(x[0]), reverse=True)
        for formal, colloquial in sorted_items:
            while formal in text:
                pos = text.find(formal)
                records.append(
                    EditRecord(
                        original=formal,
                        replaced=colloquial,
                        position=pos,
                        strategy="simplify_writing",
                        description=f"书面语简化: {formal}→{colloquial}",
                    )
                )
                text = text[:pos] + colloquial + text[pos + len(formal) :]

        # 单字书面语替换（需上下文判断，保守替换）
        single_formal = {
            "之": "的",
            "其": "他",
            "此": "这",
            "乃": "是",
            "则": "就",
            "亦": "也",
            "且": "而且",
            "故": "所以",
        }
        for formal, colloquial in single_formal.items():
            # 只在非专有名词语境中替换（简单启发：前后都是常用字）
            _lookbehind = r"(?<=[\u4e00-\u9fa5])"
            _lookahead = r"(?=[\u4e00-\u9fa5，。！？])"
            pattern = re.compile(_lookbehind + re.escape(formal) + _lookahead)
            matches = list(pattern.finditer(text))
            replace_count = int(len(matches) * (0.3 + self.aggressive * 0.4))
            for i in range(min(replace_count, len(matches))):
                m = matches[i]
                records.append(
                    EditRecord(
                        original=formal,
                        replaced=colloquial,
                        position=m.start(),
                        strategy="simplify_writing",
                        description=f"单字书面语简化: {formal}→{colloquial}",
                    )
                )
                text = text[: m.start()] + colloquial + text[m.end() :]

        return text, records


# ═══════════════════════════════════════════════════════════════════════════
# 前后对比
# ═══════════════════════════════════════════════════════════════════════════


def compare_before_after(original: str, rewritten: str) -> CompareResult:
    """对比原文和改写文，生成差异高亮和AI率变化。"""
    analyzer = AiWorkbenchAnalyzer()
    before = analyzer.analyze(original)
    after = analyzer.analyze(rewritten)
    improvement = round(before.overall_score - after.overall_score, 1)

    # 字符级 diff
    diff_segments: list[DiffSegment] = []
    sm = difflib.SequenceMatcher(None, original, rewritten, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            chunk = original[i1:i2]
            # 合并相同片段，每段不超过80字
            diff_segments.extend(
                DiffSegment(
                    type="same",
                    original=chunk[k : k + 80],
                    rewritten=chunk[k : k + 80],
                    original_start=i1 + k,
                    rewritten_start=j1 + k,
                )
                for k in range(0, len(chunk), 80)
            )
        elif tag == "replace":
            diff_segments.append(
                DiffSegment(
                    type="modified",
                    original=original[i1:i2],
                    rewritten=rewritten[j1:j2],
                    original_start=i1,
                    rewritten_start=j1,
                )
            )
        elif tag == "delete":
            diff_segments.append(
                DiffSegment(
                    type="removed",
                    original=original[i1:i2],
                    rewritten="",
                    original_start=i1,
                    rewritten_start=j1,
                )
            )
        elif tag == "insert":
            diff_segments.append(
                DiffSegment(
                    type="added",
                    original="",
                    rewritten=rewritten[j1:j2],
                    original_start=i1,
                    rewritten_start=j1,
                )
            )

    # 各维度改善
    dim_improvements: list[dict] = []
    before_map = {d.name: d for d in before.dimensions}
    after_map = {d.name: d for d in after.dimensions}
    for name, label in DIMENSION_LABELS.items():
        b = before_map.get(name)
        a = after_map.get(name)
        if b and a:
            dim_improvements.append(
                {
                    "name": name,
                    "label": label,
                    "before": b.score,
                    "after": a.score,
                    "improvement": round(b.score - a.score, 1),
                }
            )

    level_cn = {
        "very_low": "极低",
        "low": "较低",
        "medium": "中等",
        "high": "较高",
        "very_high": "极高",
    }
    summary = (
        f"AI率: {before.overall_score:.1f} → {after.overall_score:.1f} "
        f"({'下降' if improvement > 0 else '上升'}{abs(improvement):.1f}) | "
        f"原文等级: {level_cn.get(before.level, before.level)} → "
        f"改写等级: {level_cn.get(after.level, after.level)} | "
        f"差异片段: {len(diff_segments)}段"
    )

    return CompareResult(
        before_score=before.overall_score,
        after_score=after.overall_score,
        improvement=improvement,
        diff_segments=diff_segments,
        dimension_improvements=dim_improvements,
        summary=summary,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 元信息查询
# ═══════════════════════════════════════════════════════════════════════════


def get_strategies() -> list[StrategyInfo]:
    """获取可用改写策略列表。"""
    return [
        StrategyInfo(
            id="replace_high_risk",
            name="替换高危AI词汇",
            description="使用109组替换映射，将仿佛/似乎/缓缓说道等高危AI词替换为人类常用表达",
            category="vocabulary",
        ),
        StrategyInfo(
            id="remove_redundancy",
            name="去除冗余修饰和套话",
            description="删除综上所述/值得注意的是等模板套话，去除微微/轻轻/缓缓等冗余副词前缀",
            category="vocabulary",
        ),
        StrategyInfo(
            id="restructure_sentence",
            name="句式重构",
            description="长短句交替、拆分超长句、合并超短句，打破句式单调性",
            category="sentence",
        ),
        StrategyInfo(
            id="diversify_dialogue",
            name="对话标签多样化",
            description="将说道/问道/答道等单一标签替换为笑道/冷哼/低语/喃喃等多样化表达",
            category="sentence",
        ),
        StrategyInfo(
            id="add_oral_expression",
            name="增加口语化表达",
            description="在对话和陈述句中添加啊/呢/吧/嘛等语气词，增强口语感",
            category="style",
        ),
        StrategyInfo(
            id="break_paragraph",
            name="打破规整段落结构",
            description="拆分超长段落、提取独立短段落，避免段落长度过于均匀",
            category="paragraph",
        ),
        StrategyInfo(
            id="inject_rhetoric",
            name="注入修辞手法",
            description="在描写句中注入比喻（像/如/仿佛）和拟人手法，丰富修辞层次",
            category="style",
        ),
        StrategyInfo(
            id="simplify_writing",
            name="简化过于书面的表达",
            description="将之/其/此/乃/亦等文言书面语替换为的/他/这/是/也等口语表达",
            category="vocabulary",
        ),
    ]


def get_dimensions() -> list[DimensionInfo]:
    """获取12个分析维度说明。"""
    return [
        DimensionInfo(
            name=name,
            label=DIMENSION_LABELS[name],
            description=DIMENSION_DESCRIPTIONS[name],
            weight=DIMENSION_WEIGHTS.get(name, 1.0),
        )
        for name in DIMENSION_LABELS
    ]


# ═══════════════════════════════════════════════════════════════════════════
# 公开函数
# ═══════════════════════════════════════════════════════════════════════════

_analyzer = AiWorkbenchAnalyzer()
_humanizer = AiWorkbenchHumanizer()


def analyze_text(text: str) -> AiAnalysisResult:
    """12维度AI率分析。"""
    return _analyzer.analyze(text)


def humanize_with_strategy(text: str, strategies: list[str]) -> HumanizeResult:
    """按指定策略列表改写文本。"""
    return _humanizer.humanize(text, strategies)


def batch_process(texts: list[str], strategies: list[str]) -> list[HumanizeResult]:
    """批量处理多段文本。"""
    return [_humanizer.humanize(t, strategies) for t in texts]
