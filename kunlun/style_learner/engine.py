"""
昆仑创作引擎 — 风格学习与人类风格模仿引擎

基于计算风格学（Stylometry）和LLM风格迁移技术，实现：
  1. 风格指纹提取 — 12维度量化作者风格特征
  2. 风格相似度计算 — 余弦距离+特征距离+综合评分
  3. 风格引导生成 — 基于风格指纹的Prompt构建与约束注入
  4. 男频作者风格库 — 预设热门作者风格特征，支持自定义
  5. 风格一致性检查 — 章节间风格漂移检测

与昆仑引擎集成:
  - 增强 audit/ 模块的风格一致性审计
  - 为 gacha/ 抽卡引擎提供风格评分维度
  - 为 vibe_writer/ 提供风格引导参数
  - 输出可被质量看板消费的风格数据

Author: 昆仑创作引擎
"""

from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from loguru import logger

# ══════════════════════════════════════════════════════
# 风格维度定义
# ══════════════════════════════════════════════════════


class StyleDimension(Enum):
    """风格量化维度"""

    VOCAB_RICHNESS = "vocab_richness"  # 词汇丰富度
    SENTENCE_LENGTH = "sentence_length"  # 句长分布
    PUNCTUATION_STYLE = "punctuation_style"  # 标点偏好
    PARAGRAPH_STRUCTURE = "paragraph_structure"  # 段落结构
    DIALOGUE_RATIO = "dialogue_ratio"  # 对话占比
    MODAL_PARTICLES = "modal_particles"  # 语气词频率
    EMOTION_STYLE = "emotion_style"  # 情感表达风格
    SCENE_COMPOSITION = "scene_composition"  # 场景构成
    NGRAM_SIGNATURE = "ngram_signature"  # n-gram特征
    CLAUSE_DENSITY = "clause_density"  # 从句密度
    DESCRIPTIVE_DENSITY = "descriptive_density"  # 描写密度
    NARRATIVE_PACE = "narrative_pace"  # 叙事节奏


# ══════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════


@dataclass
class DimensionFeature:
    """单维度风格特征"""

    dimension: StyleDimension
    value: float
    vector: list[float] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class StyleFingerprint:
    """风格指纹 — 作者风格的量化表示"""

    author_name: str = ""
    sample_count: int = 0
    total_chars: int = 0
    dimensions: dict[str, DimensionFeature] = field(default_factory=dict)
    feature_vector: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_vector(self) -> list[float]:
        if self.feature_vector:
            return self.feature_vector
        vec = []
        for dim in StyleDimension:
            if dim.value in self.dimensions:
                vec.extend(self.dimensions[dim.value].vector)
        self.feature_vector = vec
        return vec

    def to_dict(self) -> dict[str, Any]:
        return {
            "author_name": self.author_name,
            "sample_count": self.sample_count,
            "total_chars": self.total_chars,
            "dimensions": {
                k: {
                    "dimension": v.dimension.value,
                    "value": v.value,
                    "vector": v.vector,
                    "detail": v.detail,
                    "description": v.description,
                }
                for k, v in self.dimensions.items()
            },
            "feature_vector": self.to_vector(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StyleFingerprint:
        fp = cls(
            author_name=data.get("author_name", ""),
            sample_count=data.get("sample_count", 0),
            total_chars=data.get("total_chars", 0),
            feature_vector=data.get("feature_vector", []),
            metadata=data.get("metadata", {}),
        )
        for k, v in data.get("dimensions", {}).items():
            fp.dimensions[k] = DimensionFeature(
                dimension=StyleDimension(v["dimension"]),
                value=v["value"],
                vector=v.get("vector", []),
                detail=v.get("detail", {}),
                description=v.get("description", ""),
            )
        return fp

    def summary(self) -> str:
        lines = [
            f"风格指纹: {self.author_name or '未命名'} "
            f"({self.sample_count}样本, {self.total_chars}字)"
        ]
        for dim in StyleDimension:
            if dim.value in self.dimensions:
                feat = self.dimensions[dim.value]
                lines.append(f"  {dim.value}: {feat.value:.2f} — {feat.description}")
        return "\n".join(lines)


@dataclass
class StyleSimilarityResult:
    """风格相似度结果"""

    similarity: float  # 0-100 综合相似度
    cosine_similarity: float  # 余弦相似度
    feature_distance: float  # 特征距离
    dimension_scores: dict[str, float] = field(default_factory=dict)
    matched_dimensions: list[str] = field(default_factory=list)
    divergent_dimensions: list[str] = field(default_factory=list)
    suggestion: str = ""

    def summary(self) -> str:
        level = (
            "极高"
            if self.similarity >= 85
            else "较高"
            if self.similarity >= 70
            else "中等"
            if self.similarity >= 50
            else "较低"
            if self.similarity >= 30
            else "极低"
        )
        return (
            f"风格相似度: {self.similarity:.1f}/100 ({level}) | "
            f"余弦: {self.cosine_similarity:.3f} | "
            f"特征距离: {self.feature_distance:.3f} | "
            f"匹配维度: {len(self.matched_dimensions)}/{len(self.dimension_scores)}"
        )


# ══════════════════════════════════════════════════════
# 男频作者风格库（预设）
# ══════════════════════════════════════════════════════


MALE_AUTHOR_STYLES: dict[str, dict[str, Any]] = {
    "辰东": {
        "description": "宏大叙事+史诗感+悬念伏笔，长句多，描写磅礴",
        "vocab_richness": 0.72,
        "sentence_length": {"mean": 28, "cv": 0.45, "long_ratio": 0.35},
        "punctuation": {"comma_period_ratio": 0.72, "diversity": 0.55, "ellipsis_freq": 0.02},
        "paragraph": {"mean_length": 85, "short_ratio": 0.15},
        "dialogue_ratio": 0.12,
        "modal_particles": 0.008,
        "emotion_style": {"direct_ratio": 0.25, "indirect_ratio": 0.75},
        "scene_composition": {
            "battle": 0.30,
            "dialogue": 0.15,
            "description": 0.35,
            "psychology": 0.20,
        },
        "descriptive_density": 0.28,
        "narrative_pace": "slow_majestic",
    },
    "我吃西红柿": {
        "description": "爽文节奏快+战斗密集+短句多，对话直白",
        "vocab_richness": 0.58,
        "sentence_length": {"mean": 18, "cv": 0.55, "long_ratio": 0.15},
        "punctuation": {"comma_period_ratio": 0.85, "diversity": 0.35, "ellipsis_freq": 0.005},
        "paragraph": {"mean_length": 45, "short_ratio": 0.40},
        "dialogue_ratio": 0.25,
        "modal_particles": 0.015,
        "emotion_style": {"direct_ratio": 0.55, "indirect_ratio": 0.45},
        "scene_composition": {
            "battle": 0.40,
            "dialogue": 0.25,
            "description": 0.15,
            "psychology": 0.20,
        },
        "descriptive_density": 0.12,
        "narrative_pace": "fast_punchy",
    },
    "天蚕土豆": {
        "description": "热血升级+装逼打脸+情绪渲染强，感叹号多",
        "vocab_richness": 0.60,
        "sentence_length": {"mean": 20, "cv": 0.50, "long_ratio": 0.18},
        "punctuation": {"comma_period_ratio": 0.78, "diversity": 0.45, "exclamation_freq": 0.04},
        "paragraph": {"mean_length": 50, "short_ratio": 0.35},
        "dialogue_ratio": 0.22,
        "modal_particles": 0.020,
        "emotion_style": {"direct_ratio": 0.60, "indirect_ratio": 0.40},
        "scene_composition": {
            "battle": 0.35,
            "dialogue": 0.22,
            "description": 0.18,
            "psychology": 0.25,
        },
        "descriptive_density": 0.15,
        "narrative_pace": "medium_energetic",
    },
    "耳根": {
        "description": "仙侠意境+哲学思辨+心理描写深，长句与短句交替",
        "vocab_richness": 0.75,
        "sentence_length": {"mean": 25, "cv": 0.60, "long_ratio": 0.28},
        "punctuation": {"comma_period_ratio": 0.70, "diversity": 0.60, "ellipsis_freq": 0.025},
        "paragraph": {"mean_length": 70, "short_ratio": 0.20},
        "dialogue_ratio": 0.15,
        "modal_particles": 0.012,
        "emotion_style": {"direct_ratio": 0.30, "indirect_ratio": 0.70},
        "scene_composition": {
            "battle": 0.20,
            "dialogue": 0.15,
            "description": 0.30,
            "psychology": 0.35,
        },
        "descriptive_density": 0.25,
        "narrative_pace": "medium_contemplative",
    },
    "忘语": {
        "description": "凡人修仙+写实细腻+节奏稳健，细节描写丰富",
        "vocab_richness": 0.68,
        "sentence_length": {"mean": 24, "cv": 0.48, "long_ratio": 0.25},
        "punctuation": {"comma_period_ratio": 0.75, "diversity": 0.50, "ellipsis_freq": 0.015},
        "paragraph": {"mean_length": 65, "short_ratio": 0.22},
        "dialogue_ratio": 0.18,
        "modal_particles": 0.010,
        "emotion_style": {"direct_ratio": 0.35, "indirect_ratio": 0.65},
        "scene_composition": {
            "battle": 0.25,
            "dialogue": 0.18,
            "description": 0.32,
            "psychology": 0.25,
        },
        "descriptive_density": 0.22,
        "narrative_pace": "steady_detailed",
    },
    "爱潜水的乌贼": {
        "description": "克苏鲁+蒸汽朋克+设定严谨，多视角叙事，伏笔密集",
        "vocab_richness": 0.78,
        "sentence_length": {"mean": 26, "cv": 0.52, "long_ratio": 0.30},
        "punctuation": {"comma_period_ratio": 0.68, "diversity": 0.65, "semicolon_freq": 0.015},
        "paragraph": {"mean_length": 75, "short_ratio": 0.18},
        "dialogue_ratio": 0.20,
        "modal_particles": 0.008,
        "emotion_style": {"direct_ratio": 0.28, "indirect_ratio": 0.72},
        "scene_composition": {
            "battle": 0.20,
            "dialogue": 0.20,
            "description": 0.30,
            "psychology": 0.30,
        },
        "descriptive_density": 0.24,
        "narrative_pace": "medium_intricate",
    },
}


# ══════════════════════════════════════════════════════
# 风格指纹提取器
# ══════════════════════════════════════════════════════


class StyleFingerprintExtractor:
    """风格指纹提取器 — 从文本样本中提取12维度风格特征"""

    # 中文语气词
    MODAL_PARTICLES = [
        "啊",
        "呢",
        "吧",
        "嘛",
        "呀",
        "哦",
        "哈",
        "啦",
        "呗",
        "呐",
        "哇",
        "咦",
        "唉",
        "嗯",
    ]

    # 战斗场景关键词
    BATTLE_KEYWORDS = [
        "杀",
        "攻",
        "防",
        "战",
        "斗",
        "剑",
        "刀",
        "拳",
        "掌",
        "指",
        "灵力",
        "真元",
        "真气",
        "功法",
        "招式",
        "破绽",
        "攻势",
        "守势",
        "轰",
        "撞",
        "劈",
        "斩",
        "刺",
        "扫",
        "砸",
        "震",
        "爆",
        "碎",
    ]

    # 描写场景关键词
    DESCRIPTION_KEYWORDS = [
        "天空",
        "大地",
        "山川",
        "河流",
        "森林",
        "宫殿",
        "城池",
        "光芒",
        "气息",
        "威压",
        "气势",
        "景象",
        "景色",
        "风景",
        "雄伟",
        "壮观",
        "美丽",
        "绚丽",
        "璀璨",
        "巍峨",
        "磅礴",
    ]

    # 心理场景关键词
    PSYCHOLOGY_KEYWORDS = [
        "心中",
        "内心",
        "心底",
        "心头",
        "心间",
        "心神",
        "思绪",
        "念头",
        "想法",
        "考虑",
        "思考",
        "思索",
        "盘算",
        "算计",
        "担心",
        "害怕",
        "期待",
        "渴望",
        "犹豫",
        "纠结",
        "矛盾",
    ]

    def __init__(self, ngram_n: int = 3, sample_min_chars: int = 200):
        self.ngram_n = ngram_n
        self.sample_min_chars = sample_min_chars

    def extract(self, text: str, author_name: str = "") -> StyleFingerprint:
        if not text or len(text.strip()) < 50:
            fp = StyleFingerprint(author_name=author_name)
            fp.metadata["warning"] = f"样本过少({len(text)}字)，无法提取可靠特征"
            return fp

        fp = StyleFingerprint(
            author_name=author_name,
            sample_count=1,
            total_chars=len(text.replace(" ", "").replace("\n", "")),
        )
        if len(text.strip()) < self.sample_min_chars:
            fp.metadata["low_confidence"] = True
            fp.metadata["warning"] = (
                f"样本不足({len(text)}字)，建议至少{self.sample_min_chars}字以获得可靠风格指纹"
            )

        fp.dimensions[StyleDimension.VOCAB_RICHNESS.value] = self._extract_vocab_richness(text)
        fp.dimensions[StyleDimension.SENTENCE_LENGTH.value] = self._extract_sentence_length(text)
        fp.dimensions[StyleDimension.PUNCTUATION_STYLE.value] = self._extract_punctuation(text)
        fp.dimensions[StyleDimension.PARAGRAPH_STRUCTURE.value] = self._extract_paragraph(text)
        fp.dimensions[StyleDimension.DIALOGUE_RATIO.value] = self._extract_dialogue(text)
        fp.dimensions[StyleDimension.MODAL_PARTICLES.value] = self._extract_modal_particles(text)
        fp.dimensions[StyleDimension.EMOTION_STYLE.value] = self._extract_emotion_style(text)
        fp.dimensions[StyleDimension.SCENE_COMPOSITION.value] = self._extract_scene_composition(
            text
        )
        fp.dimensions[StyleDimension.NGRAM_SIGNATURE.value] = self._extract_ngram(text)
        fp.dimensions[StyleDimension.CLAUSE_DENSITY.value] = self._extract_clause_density(text)
        fp.dimensions[StyleDimension.DESCRIPTIVE_DENSITY.value] = self._extract_descriptive_density(
            text
        )
        fp.dimensions[StyleDimension.NARRATIVE_PACE.value] = self._extract_narrative_pace(text)

        fp.to_vector()
        return fp

    def extract_from_samples(self, samples: list[str], author_name: str = "") -> StyleFingerprint:
        if not samples:
            return StyleFingerprint(author_name=author_name)
        combined = "\n".join(samples)
        fp = self.extract(combined, author_name)
        fp.sample_count = len(samples)
        return fp

    def _extract_vocab_richness(self, text: str) -> DimensionFeature:
        chars = [c for c in text if "\u4e00" <= c <= "\u9fff"]
        total = len(chars)
        unique = len(set(chars))
        ttr = unique / max(1, total)
        # 词汇丰富度向量：TTR, 唯一字数, 总字数(归一化)
        vector = [ttr, min(1.0, unique / 3000), min(1.0, total / 50000)]
        return DimensionFeature(
            dimension=StyleDimension.VOCAB_RICHNESS,
            value=ttr * 100,
            vector=vector,
            detail={"ttr": ttr, "unique_chars": unique, "total_chars": total},
            description=f"词汇丰富度TTR={ttr:.3f}, 唯一字{unique}个",
        )

    def _extract_sentence_length(self, text: str) -> DimensionFeature:
        sentences = re.split(r"(?<=[。！？!?…])", text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 1]
        if not sentences:
            return DimensionFeature(
                dimension=StyleDimension.SENTENCE_LENGTH, value=0, vector=[0, 0, 0]
            )
        lengths = [len(s) for s in sentences]
        mean_len = sum(lengths) / len(lengths)
        variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
        std_dev = math.sqrt(variance)
        cv = std_dev / max(1, mean_len)
        long_ratio = sum(1 for l in lengths if l > 40) / len(lengths)
        vector = [min(1.0, mean_len / 50), cv, long_ratio]
        return DimensionFeature(
            dimension=StyleDimension.SENTENCE_LENGTH,
            value=mean_len,
            vector=vector,
            detail={
                "mean": mean_len,
                "std": std_dev,
                "cv": cv,
                "min": min(lengths),
                "max": max(lengths),
                "long_ratio": long_ratio,
            },
            description=(
                f"平均句长{mean_len:.1f}字, 变异系数{cv:.2f}, 长句占比{long_ratio * 100:.0f}%"
            ),
        )

    def _extract_punctuation(self, text: str) -> DimensionFeature:
        puncts = {
            "，": 0,
            "。": 0,
            "！": 0,
            "？": 0,
            "、": 0,
            "；": 0,
            "：": 0,
            "…": 0,
            "—": 0,
            "（": 0,
        }
        for p in puncts:
            puncts[p] = text.count(p)
        total = sum(puncts.values())
        if total == 0:
            return DimensionFeature(
                dimension=StyleDimension.PUNCTUATION_STYLE, value=0, vector=[0, 0, 0]
            )
        comma_period_ratio = (puncts["，"] + puncts["。"]) / total
        diversity = sum(1 for v in puncts.values() if v > 0) / len(puncts)
        exclamation_freq = puncts["！"] / max(1, total)
        ellipsis_freq = puncts["…"] / max(1, total)
        vector = [comma_period_ratio, diversity, exclamation_freq, ellipsis_freq]
        value = (1 - comma_period_ratio) * 50 + diversity * 50
        return DimensionFeature(
            dimension=StyleDimension.PUNCTUATION_STYLE,
            value=value,
            vector=vector,
            detail={
                **puncts,
                "comma_period_ratio": comma_period_ratio,
                "diversity": diversity,
                "exclamation_freq": exclamation_freq,
            },
            description=(
                f"标点多样性{diversity:.2f}, 逗号句号占比{comma_period_ratio * 100:.0f}%, "
                f"感叹号频率{exclamation_freq * 100:.1f}%"
            ),
        )

    def _extract_paragraph(self, text: str) -> DimensionFeature:
        paragraphs = [p for p in text.split("\n") if p.strip()]
        if not paragraphs:
            return DimensionFeature(
                dimension=StyleDimension.PARAGRAPH_STRUCTURE, value=0, vector=[0, 0]
            )
        lengths = [len(p) for p in paragraphs]
        mean_len = sum(lengths) / len(lengths)
        short_ratio = sum(1 for l in lengths if l < 30) / len(lengths)
        vector = [min(1.0, mean_len / 100), short_ratio]
        return DimensionFeature(
            dimension=StyleDimension.PARAGRAPH_STRUCTURE,
            value=mean_len,
            vector=vector,
            detail={"mean": mean_len, "short_ratio": short_ratio, "count": len(paragraphs)},
            description=f"平均段落{mean_len:.1f}字, 短段落占比{short_ratio * 100:.0f}%",
        )

    def _extract_dialogue(self, text: str) -> DimensionFeature:
        dialogues = re.findall(r'[""「『]([^""」』]+)[""」』]', text)
        dialogue_chars = sum(len(d) for d in dialogues)
        total_chars = len(text.replace(" ", "").replace("\n", ""))
        ratio = dialogue_chars / max(1, total_chars)
        vector = [ratio, min(1.0, len(dialogues) / 50)]
        return DimensionFeature(
            dimension=StyleDimension.DIALOGUE_RATIO,
            value=ratio * 100,
            vector=vector,
            detail={
                "ratio": ratio,
                "dialogue_count": len(dialogues),
                "dialogue_chars": dialogue_chars,
            },
            description=f"对话占比{ratio * 100:.1f}%, 共{len(dialogues)}段对话",
        )

    def _extract_modal_particles(self, text: str) -> DimensionFeature:
        total = sum(text.count(p) for p in self.MODAL_PARTICLES)
        total_chars = len(text.replace(" ", "").replace("\n", ""))
        freq = total / max(1, total_chars)
        per_1k = freq * 1000
        vector = [min(1.0, per_1k / 50)]
        return DimensionFeature(
            dimension=StyleDimension.MODAL_PARTICLES,
            value=per_1k,
            vector=vector,
            detail={"total": total, "freq": freq, "per_1k": per_1k},
            description=f"语气词频率{per_1k:.1f}/千字",
        )

    def _extract_emotion_style(self, text: str) -> DimensionFeature:
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
        direct_ratio = direct_count / max(1, direct_count + indirect_count)
        vector = [direct_ratio, min(1.0, direct_count / 100), min(1.0, indirect_count / 200)]
        return DimensionFeature(
            dimension=StyleDimension.EMOTION_STYLE,
            value=direct_ratio * 100,
            vector=vector,
            detail={
                "direct_count": direct_count,
                "indirect_count": indirect_count,
                "direct_ratio": direct_ratio,
            },
            description=(
                f"直接情感占比{direct_ratio * 100:.0f}% (直接{direct_count}/间接{indirect_count})"
            ),
        )

    def _extract_scene_composition(self, text: str) -> DimensionFeature:
        sentences = re.split(r"(?<=[。！？])", text)
        sentences = [s for s in sentences if s.strip()]
        if not sentences:
            return DimensionFeature(
                dimension=StyleDimension.SCENE_COMPOSITION, value=0, vector=[0, 0, 0, 0]
            )
        battle = sum(1 for s in sentences if any(k in s for k in self.BATTLE_KEYWORDS))
        dialogue = sum(1 for s in sentences if re.search(r'[""「『]', s))
        description = sum(1 for s in sentences if any(k in s for k in self.DESCRIPTION_KEYWORDS))
        psychology = sum(1 for s in sentences if any(k in s for k in self.PSYCHOLOGY_KEYWORDS))
        total = len(sentences)
        battle_r = battle / total
        dialogue_r = dialogue / total
        desc_r = description / total
        psych_r = psychology / total
        vector = [battle_r, dialogue_r, desc_r, psych_r]
        dominant = max(
            [
                ("battle", battle_r),
                ("dialogue", dialogue_r),
                ("description", desc_r),
                ("psychology", psych_r),
            ],
            key=lambda x: x[1],
        )
        return DimensionFeature(
            dimension=StyleDimension.SCENE_COMPOSITION,
            value=dominant[1] * 100,
            vector=vector,
            detail={
                "battle": battle_r,
                "dialogue": dialogue_r,
                "description": desc_r,
                "psychology": psych_r,
                "dominant": dominant[0],
            },
            description=(
                f"场景构成: 战斗{battle_r * 100:.0f}% 对话{dialogue_r * 100:.0f}% "
                f"描写{desc_r * 100:.0f}% 心理{psych_r * 100:.0f}% (主导:{dominant[0]})"
            ),
        )

    def _extract_ngram(self, text: str) -> DimensionFeature:
        chars = [c for c in text if "\u4e00" <= c <= "\u9fff"]
        if len(chars) < self.ngram_n:
            return DimensionFeature(dimension=StyleDimension.NGRAM_SIGNATURE, value=0, vector=[])
        ngrams: dict[str, int] = {}
        for i in range(len(chars) - self.ngram_n + 1):
            ng = "".join(chars[i : i + self.ngram_n])
            ngrams[ng] = ngrams.get(ng, 0) + 1
        total = sum(ngrams.values())
        unique = len(ngrams)
        top10 = sorted(ngrams.items(), key=lambda x: x[1], reverse=True)[:10]
        top10_ratio = sum(c for _, c in top10) / max(1, total)
        vector = [min(1.0, unique / 5000), top10_ratio]
        return DimensionFeature(
            dimension=StyleDimension.NGRAM_SIGNATURE,
            value=unique,
            vector=vector,
            detail={
                "total_ngrams": total,
                "unique_ngrams": unique,
                "top10": top10,
                "top10_ratio": top10_ratio,
            },
            description=f"{self.ngram_n}-gram: {unique}种唯一, Top10占比{top10_ratio * 100:.1f}%",
        )

    def _extract_clause_density(self, text: str) -> DimensionFeature:
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
        ]
        sentences = re.split(r"(?<=[。！？])", text)
        sentences = [s for s in sentences if s.strip()]
        if not sentences:
            return DimensionFeature(dimension=StyleDimension.CLAUSE_DENSITY, value=0, vector=[0, 0])
        total_clauses = sum(s.count(m) for s in sentences for m in clause_markers)
        avg_clauses = total_clauses / len(sentences)
        long_ratio = sum(1 for s in sentences if len(s) > 50) / len(sentences)
        vector = [min(1.0, avg_clauses / 3), long_ratio]
        return DimensionFeature(
            dimension=StyleDimension.CLAUSE_DENSITY,
            value=avg_clauses,
            vector=vector,
            detail={
                "avg_clauses": avg_clauses,
                "long_ratio": long_ratio,
                "total_clauses": total_clauses,
            },
            description=f"平均从句{avg_clauses:.2f}个/句, 长句占比{long_ratio * 100:.0f}%",
        )

    def _extract_descriptive_density(self, text: str) -> DimensionFeature:
        adj_markers = ["的", "地", "得"]
        degree_words = ["非常", "十分", "格外", "异常", "极其", "极为", "甚是", "相当", "颇为"]
        color_words = ["红", "蓝", "绿", "黄", "白", "黑", "紫", "金", "银", "灰", "青", "橙"]
        total_adj = sum(text.count(m) for m in adj_markers)
        total_degree = sum(text.count(w) for w in degree_words)
        total_color = sum(text.count(w) for w in color_words)
        total_chars = len(text.replace(" ", "").replace("\n", ""))
        density = (total_adj + total_degree * 2 + total_color) / max(1, total_chars)
        vector = [min(1.0, density * 10), min(1.0, total_color / 50)]
        return DimensionFeature(
            dimension=StyleDimension.DESCRIPTIVE_DENSITY,
            value=density * 100,
            vector=vector,
            detail={
                "adj_count": total_adj,
                "degree_count": total_degree,
                "color_count": total_color,
                "density": density,
            },
            description=(
                f"描写密度{density * 100:.1f}% "
                f"(的地得{total_adj}, 程度词{total_degree}, 颜色词{total_color})"
            ),
        )

    def _extract_narrative_pace(self, text: str) -> DimensionFeature:
        sentences = re.split(r"(?<=[。！？])", text)
        sentences = [s for s in sentences if s.strip()]
        if not sentences:
            return DimensionFeature(
                dimension=StyleDimension.NARRATIVE_PACE, value=0, vector=[0, 0, 0]
            )
        # 节奏指标：短句占比(快)、动词密度(快)、场景切换频率
        short_ratio = sum(1 for s in sentences if len(s) < 15) / len(sentences)
        verbs = [
            "说",
            "道",
            "走",
            "跑",
            "跳",
            "飞",
            "杀",
            "打",
            "砍",
            "劈",
            "刺",
            "扫",
            "看",
            "望",
            "盯",
            "瞪",
            "笑",
            "哭",
            "怒",
            "吼",
            "叫",
            "喊",
            "想",
            "思",
            "念",
            "记",
            "忘",
            "知",
            "觉",
            "感",
            "悟",
        ]
        verb_density = sum(text.count(v) for v in verbs) / max(1, len(text))
        # 场景切换：段落开头变化
        paragraphs = [p for p in text.split("\n") if p.strip()]
        scene_changes = 0
        for i in range(1, len(paragraphs)):
            if paragraphs[i][:2] != paragraphs[i - 1][:2]:
                scene_changes += 1
        scene_change_freq = scene_changes / max(1, len(paragraphs))
        pace_score = (short_ratio * 0.4 + verb_density * 100 * 0.3 + scene_change_freq * 0.3) * 100
        vector = [short_ratio, min(1.0, verb_density * 50), scene_change_freq]
        pace_label = "快节奏" if pace_score > 50 else "中节奏" if pace_score > 30 else "慢节奏"
        return DimensionFeature(
            dimension=StyleDimension.NARRATIVE_PACE,
            value=pace_score,
            vector=vector,
            detail={
                "short_ratio": short_ratio,
                "verb_density": verb_density,
                "scene_change_freq": scene_change_freq,
                "pace_label": pace_label,
            },
            description=(
                f"叙事节奏: {pace_label} ({pace_score:.1f}/100), "
                f"短句占比{short_ratio * 100:.0f}%, 场景切换频率{scene_change_freq * 100:.0f}%"
            ),
        )


# ══════════════════════════════════════════════════════
# 风格相似度计算器
# ══════════════════════════════════════════════════════


class StyleSimilarityCalculator:
    """风格相似度计算器"""

    DIMENSION_WEIGHTS: dict[StyleDimension, float] = {
        StyleDimension.VOCAB_RICHNESS: 0.08,
        StyleDimension.SENTENCE_LENGTH: 0.12,
        StyleDimension.PUNCTUATION_STYLE: 0.10,
        StyleDimension.PARAGRAPH_STRUCTURE: 0.08,
        StyleDimension.DIALOGUE_RATIO: 0.10,
        StyleDimension.MODAL_PARTICLES: 0.06,
        StyleDimension.EMOTION_STYLE: 0.08,
        StyleDimension.SCENE_COMPOSITION: 0.12,
        StyleDimension.NGRAM_SIGNATURE: 0.08,
        StyleDimension.CLAUSE_DENSITY: 0.06,
        StyleDimension.DESCRIPTIVE_DENSITY: 0.06,
        StyleDimension.NARRATIVE_PACE: 0.06,
    }

    def calculate(self, fp1: StyleFingerprint, fp2: StyleFingerprint) -> StyleSimilarityResult:
        v1 = fp1.to_vector()
        v2 = fp2.to_vector()

        if not v1 or not v2 or len(v1) != len(v2):
            return StyleSimilarityResult(
                similarity=0,
                cosine_similarity=0,
                feature_distance=999,
                suggestion="向量长度不一致，无法计算相似度",
            )

        cosine = self._cosine_similarity(v1, v2)
        euclidean = self._euclidean_distance(v1, v2)

        dimension_scores: dict[str, float] = {}
        matched: list[str] = []
        divergent: list[str] = []
        for dim in StyleDimension:
            if dim.value in fp1.dimensions and dim.value in fp2.dimensions:
                f1 = fp1.dimensions[dim.value]
                f2 = fp2.dimensions[dim.value]
                if f1.vector and f2.vector and len(f1.vector) == len(f2.vector):
                    dim_cos = self._cosine_similarity(f1.vector, f2.vector)
                    score = dim_cos * 100
                    dimension_scores[dim.value] = score
                    if score >= 70:
                        matched.append(dim.value)
                    elif score < 40:
                        divergent.append(dim.value)

        weighted_dim_score = 0.0
        total_weight = 0.0
        for dim_name, score in dimension_scores.items():
            w = self.DIMENSION_WEIGHTS.get(StyleDimension(dim_name), 0.05)
            weighted_dim_score += float(score) * w
            total_weight += w
        dim_avg = weighted_dim_score / max(0.01, total_weight)

        similarity = cosine * 40 + dim_avg * 0.5 + max(0, 100 - euclidean * 50) * 0.1
        similarity = max(0, min(100, similarity))

        suggestion = self._generate_suggestion(similarity, matched, divergent, fp1, fp2)

        return StyleSimilarityResult(
            similarity=similarity,
            cosine_similarity=cosine,
            feature_distance=euclidean,
            dimension_scores=dimension_scores,
            matched_dimensions=matched,
            divergent_dimensions=divergent,
            suggestion=suggestion,
        )

    def _cosine_similarity(self, v1: list[float], v2: list[float]) -> float:
        dot = sum(a * b for a, b in zip(v1, v2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0
        return dot / (norm1 * norm2)

    def _euclidean_distance(self, v1: list[float], v2: list[float]) -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2, strict=False)))

    def _generate_suggestion(
        self,
        similarity: float,
        matched: list[str],
        divergent: list[str],
        _fp1: StyleFingerprint,
        fp2: StyleFingerprint,
    ) -> str:
        if similarity >= 85:
            return "风格高度一致，可直接使用目标风格"
        if similarity >= 70:
            if divergent:
                return f"风格较接近，需调整: {', '.join(divergent)}"
            return "风格较接近，微调即可"
        if similarity >= 50:
            parts = []
            if divergent:
                parts.append(f"重点改进: {', '.join(divergent)}")
            if matched:
                parts.append(f"已匹配: {', '.join(matched[:3])}")
            return " | ".join(parts) if parts else "风格中等相似，需要系统性调整"
        target = fp2.author_name or "目标"
        focus = ", ".join(divergent[:3]) if divergent else "核心维度"
        return f"风格差异较大，建议: 1)增加{target}风格样本 2)重点调整{focus}"


# ══════════════════════════════════════════════════════
# 风格引导生成器
# ══════════════════════════════════════════════════════


class StyleGuidedGenerator:
    """风格引导生成器 — 基于风格指纹构建Prompt和约束"""

    def __init__(
        self,
        extractor: StyleFingerprintExtractor | None = None,
        similarity_calculator: StyleSimilarityCalculator | None = None,
    ):
        self.extractor = extractor or StyleFingerprintExtractor()
        self.similarity = similarity_calculator or StyleSimilarityCalculator()

    def build_style_prompt(
        self, target_fp: StyleFingerprint, scene_type: str = "general", chapter_context: str = ""
    ) -> str:
        dims = target_fp.dimensions
        parts = [f"【风格要求】严格模仿以下作者风格创作：{target_fp.author_name or '目标风格'}"]

        if StyleDimension.SENTENCE_LENGTH.value in dims:
            sl = dims[StyleDimension.SENTENCE_LENGTH.value].detail
            parts.append(
                f"- 句长: 平均{sl.get('mean', 0):.0f}字，"
                f"长句占比{sl.get('long_ratio', 0) * 100:.0f}%，"
                f"句长变异系数{sl.get('cv', 0):.2f}"
            )

        if StyleDimension.PARAGRAPH_STRUCTURE.value in dims:
            ps = dims[StyleDimension.PARAGRAPH_STRUCTURE.value].detail
            parts.append(
                f"- 段落: 平均{ps.get('mean', 0):.0f}字/段，"
                f"短段落占比{ps.get('short_ratio', 0) * 100:.0f}%"
            )

        if StyleDimension.DIALOGUE_RATIO.value in dims:
            dr = dims[StyleDimension.DIALOGUE_RATIO.value].detail
            parts.append(
                f"- 对话: 占比{dr.get('ratio', 0) * 100:.0f}%，"
                f"约{dr.get('dialogue_count', 0)}段对话/章"
            )

        if StyleDimension.MODAL_PARTICLES.value in dims:
            mp = dims[StyleDimension.MODAL_PARTICLES.value].detail
            parts.append(f"- 语气词: 频率{mp.get('per_1k', 0):.1f}/千字")

        if StyleDimension.EMOTION_STYLE.value in dims:
            es = dims[StyleDimension.EMOTION_STYLE.value].detail
            style = "直接表达情感" if es.get("direct_ratio", 0) > 0.5 else "间接含蓄表达情感"
            parts.append(f"- 情感: {style}（直接占比{es.get('direct_ratio', 0) * 100:.0f}%）")

        if StyleDimension.SCENE_COMPOSITION.value in dims:
            sc = dims[StyleDimension.SCENE_COMPOSITION.value].detail
            parts.append(
                f"- 场景: 战斗{sc.get('battle', 0) * 100:.0f}% "
                f"对话{sc.get('dialogue', 0) * 100:.0f}% "
                f"描写{sc.get('description', 0) * 100:.0f}% "
                f"心理{sc.get('psychology', 0) * 100:.0f}%"
            )

        if StyleDimension.DESCRIPTIVE_DENSITY.value in dims:
            dd = dims[StyleDimension.DESCRIPTIVE_DENSITY.value].detail
            parts.append(f"- 描写密度: {dd.get('density', 0) * 100:.1f}%")

        if StyleDimension.NARRATIVE_PACE.value in dims:
            np = dims[StyleDimension.NARRATIVE_PACE.value].detail
            parts.append(f"- 叙事节奏: {np.get('pace_label', '中节奏')}")

        if StyleDimension.PUNCTUATION_STYLE.value in dims:
            pu = dims[StyleDimension.PUNCTUATION_STYLE.value].detail
            parts.append(
                f"- 标点: 多样性{pu.get('diversity', 0):.2f}，"
                f"感叹号频率{pu.get('exclamation_freq', 0) * 100:.1f}%"
            )

        parts.append("【风格禁忌】")
        parts.append("- 禁止使用AI高频套话（仿佛、似乎、不由得、心中暗道、眼中闪过等）")
        parts.append("- 禁止过度修饰和冗余形容词")
        parts.append("- 保持风格一致性，不要在不同段落间切换风格")

        if scene_type != "general":
            parts.append(f"【场景类型】{scene_type}")
            scene_guides = {
                "battle": "战斗场景：短句为主，动词密集，节奏快，减少环境描写",
                "dialogue": "对话场景：对话占比高，语气词自然，角色口吻鲜明",
                "description": "描写场景：长句为主，形容词丰富，节奏慢，注重意境",
                "psychology": "心理场景：内心独白为主，反思性语言，节奏舒缓",
                "climax": "高潮场景：短句爆发，情绪强烈，节奏极快，感叹号适度增加",
            }
            if scene_type in scene_guides:
                parts.append(f"- {scene_guides[scene_type]}")

        if chapter_context:
            parts.append(f"【章节上下文】{chapter_context[:500]}")

        return "\n".join(parts)

    def check_style_consistency(self, chapters: list[str], author_name: str = "") -> dict[str, Any]:
        if len(chapters) < 2:
            return {"consistent": True, "message": "样本不足，无法检测风格漂移"}

        fingerprints = []
        for i, ch in enumerate(chapters):
            fp = self.extractor.extract(ch, f"{author_name}_ch{i + 1}")
            fingerprints.append(fp)

        base_fp = fingerprints[0]
        results: list[dict[str, Any]] = []
        drift_dims: set[str] = set()

        for i in range(1, len(fingerprints)):
            sim = self.similarity.calculate(base_fp, fingerprints[i])
            assert isinstance(sim, StyleSimilarityResult)
            results.append(
                {
                    "chapter": i + 1,
                    "similarity": sim.similarity,
                    "divergent": sim.divergent_dimensions,
                }
            )
            drift_dims.update(list(sim.divergent_dimensions))

        avg_sim = sum(r["similarity"] for r in results) / len(results) if results else 100
        consistent = avg_sim >= 60

        return {
            "consistent": consistent,
            "avg_similarity": avg_sim,
            "chapter_results": results,
            "drift_dimensions": list(drift_dims),
            "message": (
                f"风格一致性: {'通过' if consistent else '存在漂移'} (平均相似度{avg_sim:.1f})"
            ),
        }


# ══════════════════════════════════════════════════════
# 风格库管理器
# ══════════════════════════════════════════════════════


class StyleLibrary:
    """风格库管理器 — 管理预设和自定义作者风格"""

    def __init__(self):
        self.styles: dict[str, StyleFingerprint] = {}
        self._load_presets()

    def _load_presets(self):
        for name, data in MALE_AUTHOR_STYLES.items():
            fp = self._preset_to_fingerprint(name, data)
            self.styles[name] = fp

    def _preset_to_fingerprint(self, name: str, data: dict[str, Any]) -> StyleFingerprint:
        fp = StyleFingerprint(author_name=name, sample_count=100, total_chars=500000)
        fp.metadata["preset"] = True
        fp.metadata["description"] = data.get("description", "")

        # 词汇丰富度
        vr = data.get("vocab_richness", 0.65)
        fp.dimensions[StyleDimension.VOCAB_RICHNESS.value] = DimensionFeature(
            dimension=StyleDimension.VOCAB_RICHNESS,
            value=vr * 100,
            vector=[vr, 0.8, 0.9],
            description=f"预设词汇丰富度{vr:.2f}",
        )

        # 句长
        sl = data.get("sentence_length", {"mean": 22, "cv": 0.5, "long_ratio": 0.2})
        fp.dimensions[StyleDimension.SENTENCE_LENGTH.value] = DimensionFeature(
            dimension=StyleDimension.SENTENCE_LENGTH,
            value=sl["mean"],
            vector=[min(1.0, sl["mean"] / 50), sl["cv"], sl["long_ratio"]],
            detail=sl,
            description=f"预设平均句长{sl['mean']}字",
        )

        # 标点
        pu = data.get(
            "punctuation", {"comma_period_ratio": 0.75, "diversity": 0.5, "exclamation_freq": 0.02}
        )
        fp.dimensions[StyleDimension.PUNCTUATION_STYLE.value] = DimensionFeature(
            dimension=StyleDimension.PUNCTUATION_STYLE,
            value=(1 - pu["comma_period_ratio"]) * 50 + pu["diversity"] * 50,
            vector=[
                pu["comma_period_ratio"],
                pu["diversity"],
                pu.get("exclamation_freq", 0.02),
                pu.get("ellipsis_freq", 0.01),
            ],
            detail=pu,
            description=f"预设标点多样性{pu['diversity']:.2f}",
        )

        # 段落
        pa = data.get("paragraph", {"mean": 60, "short_ratio": 0.25})
        pa_mean = pa.get("mean", pa.get("mean_length", 60))
        fp.dimensions[StyleDimension.PARAGRAPH_STRUCTURE.value] = DimensionFeature(
            dimension=StyleDimension.PARAGRAPH_STRUCTURE,
            value=pa_mean,
            vector=[min(1.0, pa_mean / 100), pa["short_ratio"]],
            detail={"mean": pa_mean, "short_ratio": pa["short_ratio"]},
            description=f"预设平均段落{pa_mean}字",
        )

        # 对话
        dr = data.get("dialogue_ratio", 0.2)
        fp.dimensions[StyleDimension.DIALOGUE_RATIO.value] = DimensionFeature(
            dimension=StyleDimension.DIALOGUE_RATIO,
            value=dr * 100,
            vector=[dr, 0.5],
            detail={"ratio": dr},
            description=f"预设对话占比{dr * 100:.0f}%",
        )

        # 语气词
        mp = data.get("modal_particles", 0.012)
        fp.dimensions[StyleDimension.MODAL_PARTICLES.value] = DimensionFeature(
            dimension=StyleDimension.MODAL_PARTICLES,
            value=mp * 1000,
            vector=[min(1.0, mp * 1000 / 50)],
            detail={"per_1k": mp * 1000},
            description=f"预设语气词频率{mp * 1000:.1f}/千字",
        )

        # 情感
        es = data.get("emotion_style", {"direct_ratio": 0.4, "indirect_ratio": 0.6})
        fp.dimensions[StyleDimension.EMOTION_STYLE.value] = DimensionFeature(
            dimension=StyleDimension.EMOTION_STYLE,
            value=es["direct_ratio"] * 100,
            vector=[es["direct_ratio"], 0.5, 0.5],
            detail=es,
            description=f"预设直接情感占比{es['direct_ratio'] * 100:.0f}%",
        )

        # 场景
        sc = data.get(
            "scene_composition",
            {"battle": 0.3, "dialogue": 0.2, "description": 0.25, "psychology": 0.25},
        )
        fp.dimensions[StyleDimension.SCENE_COMPOSITION.value] = DimensionFeature(
            dimension=StyleDimension.SCENE_COMPOSITION,
            value=max(sc.values()) * 100,
            vector=[sc["battle"], sc["dialogue"], sc["description"], sc["psychology"]],
            detail=sc,
            description="预设场景构成",
        )

        # n-gram
        fp.dimensions[StyleDimension.NGRAM_SIGNATURE.value] = DimensionFeature(
            dimension=StyleDimension.NGRAM_SIGNATURE,
            value=2000,
            vector=[0.6, 0.15],
            description="预设n-gram特征",
        )

        # 从句
        fp.dimensions[StyleDimension.CLAUSE_DENSITY.value] = DimensionFeature(
            dimension=StyleDimension.CLAUSE_DENSITY,
            value=0.8,
            vector=[0.3, 0.25],
            description="预设从句密度",
        )

        # 描写密度
        dd = data.get("descriptive_density", 0.18)
        fp.dimensions[StyleDimension.DESCRIPTIVE_DENSITY.value] = DimensionFeature(
            dimension=StyleDimension.DESCRIPTIVE_DENSITY,
            value=dd * 100,
            vector=[min(1.0, dd * 10), 0.5],
            detail={"density": dd},
            description=f"预设描写密度{dd * 100:.0f}%",
        )

        # 叙事节奏
        pace_map = {
            "fast_punchy": 75,
            "medium_energetic": 55,
            "medium_contemplative": 40,
            "slow_majestic": 25,
            "steady_detailed": 45,
            "medium_intricate": 50,
        }
        pace_score = pace_map.get(data.get("narrative_pace", "medium_energetic"), 50)
        fp.dimensions[StyleDimension.NARRATIVE_PACE.value] = DimensionFeature(
            dimension=StyleDimension.NARRATIVE_PACE,
            value=pace_score,
            vector=[pace_score / 100, 0.5, 0.5],
            detail={"pace_label": data.get("narrative_pace", "medium")},
            description=f"预设叙事节奏{data.get('narrative_pace', 'medium')}",
        )

        fp.to_vector()
        return fp

    def get_style(self, name: str) -> StyleFingerprint | None:
        return self.styles.get(name)

    def list_styles(self) -> list[dict[str, str]]:
        return [
            {
                "name": name,
                "description": fp.metadata.get("description", ""),
                "preset": fp.metadata.get("preset", False),
            }
            for name, fp in self.styles.items()
        ]

    def add_custom_style(
        self, name: str, samples: list[str], description: str = ""
    ) -> StyleFingerprint:
        extractor = StyleFingerprintExtractor()
        fp = extractor.extract_from_samples(samples, name)
        fp.metadata["preset"] = False
        fp.metadata["description"] = description
        self.styles[name] = fp
        return fp

    def remove_style(self, name: str) -> bool:
        if name in self.styles and not self.styles[name].metadata.get("preset", False):
            del self.styles[name]
            return True
        return False

    def save_to_file(self, filepath: str):
        data = {
            name: fp.to_dict()
            for name, fp in self.styles.items()
            if not fp.metadata.get("preset", False)
        }
        with Path(filepath).open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_from_file(self, filepath: str):
        with Path(filepath).open(encoding="utf-8") as f:
            data = json.load(f)
        for name, fp_data in data.items():
            self.styles[name] = StyleFingerprint.from_dict(fp_data)


# ══════════════════════════════════════════════════════
# 便捷函数
# ══════════════════════════════════════════════════════


def extract_style_fingerprint(text: str, author_name: str = "") -> StyleFingerprint:
    extractor = StyleFingerprintExtractor()
    return extractor.extract(text, author_name)


def calculate_style_similarity(text1: str, text2: str) -> StyleSimilarityResult:
    extractor = StyleFingerprintExtractor()
    fp1 = extractor.extract(text1, "text1")
    fp2 = extractor.extract(text2, "text2")
    calculator = StyleSimilarityCalculator()
    return calculator.calculate(fp1, fp2)


def get_preset_style(name: str) -> StyleFingerprint | None:
    library = StyleLibrary()
    return library.get_style(name)


def list_preset_styles() -> list[dict[str, str]]:
    library = StyleLibrary()
    return library.list_styles()


def build_style_prompt(style_name: str, scene_type: str = "general") -> str:
    library = StyleLibrary()
    fp = library.get_style(style_name)
    if not fp:
        available = ", ".join(s["name"] for s in library.list_styles())
        return f"风格 '{style_name}' 不存在。可用风格: {available}"
    generator = StyleGuidedGenerator()
    return generator.build_style_prompt(fp, scene_type)


# ══════════════════════════════════════════════════════
# 爆款仿写四维度分析器 (StyleLearner)
# ══════════════════════════════════════════════════════


class StyleLearner:
    """爆款仿写四维度分析器

    对参考文本进行纯规则统计分析，覆盖：
      1. 设定仿写 — 设定密度、类型分布、世界观构建方式
      2. 情节仿写 — 情节密度、情绪波峰、转折设计、节奏曲线
      3. 正文风格 — 句长、句式、描写密度、对话占比、高频词、段落长度
      4. 结构仿写 — 章节字数、开篇模式、结尾模式、卷章架构建议

    所有分析均不依赖 LLM，基于关键词匹配、jieba 分词和统计规则。
    """

    # 设定类型关键词
    SETTING_KEYWORDS: dict[str, list[str]] = {
        "修炼体系": [
            "境界",
            "修为",
            "功法",
            "武技",
            "灵力",
            "真元",
            "真气",
            "丹田",
            "经脉",
            "突破",
        ],
        "地理势力": [
            "宗门",
            "家族",
            "帝国",
            "王朝",
            "城池",
            "山脉",
            "森林",
            "海域",
            "秘境",
            "禁地",
        ],
        "物品设定": [
            "法宝",
            "丹药",
            "灵草",
            "矿石",
            "阵法",
            "符箓",
            "神器",
            "灵器",
            "储物",
            "材料",
        ],
        "种族生灵": [
            "人族",
            "妖族",
            "魔族",
            "神族",
            "龙族",
            "灵兽",
            "妖兽",
            "凶兽",
            "异族",
            "血脉",
        ],
        "规则法则": [
            "天道",
            "法则",
            "规则",
            "因果",
            "气运",
            "命数",
            "轮回",
            "天劫",
            "道心",
            "本源",
        ],
        "历史背景": [
            "上古",
            "远古",
            "洪荒",
            "纪元",
            "时代",
            "传说",
            "神话",
            "遗迹",
            "传承",
            "秘辛",
        ],
    }

    # 情绪关键词
    EMOTION_KEYWORDS: list[str] = [
        "愤怒",
        "暴怒",
        "震惊",
        "惊骇",
        "恐惧",
        "害怕",
        "狂喜",
        "兴奋",
        "激动",
        "绝望",
        "悲伤",
        "痛苦",
        "嫉妒",
        "贪婪",
        "杀意",
        "杀机",
        "热血",
        "沸腾",
        "震撼",
        "难以置信",
        "不可思议",
        "毛骨悚然",
    ]

    # 动作动词（用于节奏曲线）
    ACTION_VERBS: list[str] = [
        "冲",
        "杀",
        "攻",
        "防",
        "退",
        "进",
        "跳",
        "飞",
        "落",
        "起",
        "挥",
        "劈",
        "斩",
        "刺",
        "扫",
        "砸",
        "轰",
        "撞",
        "抓",
        "握",
        "跑",
        "奔",
        "跃",
        "翻",
        "滚",
        "爬",
        "蹲",
        "站",
        "坐",
        "躺",
    ]

    # 转折信号词
    TWIST_MARKERS: list[str] = [
        "然而",
        "但是",
        "可是",
        "却",
        "不料",
        "没想到",
        "谁知",
        "突然",
        "就在这时",
        "下一刻",
        "忽然",
        "猛然",
        "骤然",
        "竟",
        "竟然",
    ]

    # 悬念结尾信号
    SUSPENSE_ENDINGS: list[str] = [
        "？",
        "！",
        "……",
        "——",
        "谁",
        "什么",
        "怎么",
        "为何",
        "难道",
        "究竟",
        "到底",
        "未知",
        "谜团",
        "秘密",
        "真相",
        "伏笔",
    ]

    def __init__(self) -> None:
        self._jieba_initialized = False

    def _ensure_jieba(self) -> None:
        """延迟初始化 jieba 分词器"""
        if not self._jieba_initialized:
            try:
                import jieba

                jieba.setLogLevel(60)  # 关闭 jieba 日志
                self._jieba_initialized = True
            except ImportError:
                self._jieba_initialized = False

    # ── 维度一：设定仿写分析 ──────────────────────────

    def analyze_setting(self, text: str) -> dict[str, Any]:
        """设定仿写分析

        Args:
            text: 参考文本

        Returns:
            包含设定密度、类型分布、世界观构建方式的字典
        """
        if not text or len(text.strip()) < 50:
            return {
                "setting_density_per_1k": 0.0,
                "type_distribution": {},
                "worldbuilding_method": "样本不足",
                "total_setting_mentions": 0,
                "word_count": len(text),
            }

        word_count = len(text.replace(" ", "").replace("\n", ""))
        type_counts: dict[str, int] = {}
        total_mentions = 0

        for setting_type, keywords in self.SETTING_KEYWORDS.items():
            count = sum(text.count(kw) for kw in keywords)
            if count > 0:
                type_counts[setting_type] = count
                total_mentions += count

        # 设定密度 = 每1000字设定条目数
        setting_density = round(total_mentions / max(1, word_count) * 1000, 2)

        # 类型分布（百分比）
        type_distribution: dict[str, Any] = {}
        for st, cnt in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            type_distribution[st] = {
                "count": cnt,
                "ratio": round(cnt / max(1, total_mentions), 3),
            }

        # 世界观构建方式总结
        dominant_types = list(type_distribution.keys())[:3]
        if setting_density >= 5:
            method = "高密度设定流，世界观信息密集，适合硬核玄幻/科幻"
        elif setting_density >= 2:
            method = "中密度设定，设定与情节平衡，适合主流网文"
        else:
            method = "低密度设定，重情节轻设定，适合快节奏爽文"

        if dominant_types:
            method += "；核心设定维度: " + "、".join(dominant_types)

        return {
            "setting_density_per_1k": setting_density,
            "type_distribution": type_distribution,
            "worldbuilding_method": method,
            "total_setting_mentions": total_mentions,
            "word_count": word_count,
        }

    # ── 维度二：情节仿写分析 ──────────────────────────

    def analyze_plot(self, text: str) -> dict[str, Any]:
        """情节仿写分析

        Args:
            text: 参考文本

        Returns:
            包含情节密度、情绪波峰频率、转折设计、节奏曲线的字典
        """
        if not text or len(text.strip()) < 50:
            return {
                "plot_density_per_1k": 0.0,
                "emotion_peak_frequency": 0.0,
                "twist_analysis": {},
                "rhythm_curve": [],
                "word_count": len(text),
            }

        word_count = len(text.replace(" ", "").replace("\n", ""))
        paragraphs = [p for p in text.split("\n") if p.strip()]

        # 情节密度 = 每1000字事件节点数
        action_paragraphs = sum(1 for p in paragraphs if any(v in p for v in self.ACTION_VERBS))
        twist_count = sum(text.count(m) for m in self.TWIST_MARKERS)
        event_nodes = len(paragraphs) + twist_count + action_paragraphs
        plot_density = round(event_nodes / max(1, word_count) * 1000, 2)

        # 情绪波峰频率
        exclamation_count = text.count("！") + text.count("!")
        question_count = text.count("？") + text.count("?")
        emotion_count = sum(text.count(kw) for kw in self.EMOTION_KEYWORDS)
        emotion_peaks = exclamation_count + question_count + emotion_count
        emotion_peak_freq = round(emotion_peaks / max(1, word_count) * 1000, 2)

        # 转折设计分析
        paragraph_lengths = [len(p) for p in paragraphs]
        avg_para_len = sum(paragraph_lengths) / max(1, len(paragraph_lengths))
        if len(paragraph_lengths) > 1:
            mean_len = avg_para_len
            variance = sum((l - mean_len) ** 2 for l in paragraph_lengths) / len(paragraph_lengths)
            std_len = math.sqrt(variance)
            length_variation = round(std_len / max(1, mean_len), 3)
        else:
            length_variation = 0.0

        # 对话占比
        dialogues = re.findall(r'[""「『]([^""」』]+)[""」』]', text)
        dialogue_chars = sum(len(d) for d in dialogues)
        dialogue_ratio = round(dialogue_chars / max(1, word_count), 3)

        twist_analysis = {
            "twist_marker_count": twist_count,
            "twist_density_per_1k": round(twist_count / max(1, word_count) * 1000, 2),
            "paragraph_length_variation": length_variation,
            "avg_paragraph_length": round(avg_para_len, 1),
            "dialogue_ratio": dialogue_ratio,
            "rhythm_style": (
                "快节奏（段落短、变化大）"
                if length_variation > 0.6 and avg_para_len < 40
                else "中节奏（段落适中、变化中等）"
                if length_variation > 0.3
                else "慢节奏（段落长、变化小）"
            ),
        }

        # 节奏曲线：按段落的动作/对话/描写比例
        rhythm_curve: list[dict[str, Any]] = []
        sample_step = max(1, len(paragraphs) // 20)
        for i in range(0, len(paragraphs), sample_step):
            p = paragraphs[i]
            action_ratio = sum(1 for v in self.ACTION_VERBS if v in p) / max(1, len(p))
            has_dialogue = bool(re.search(r'[""「『]', p))
            desc_markers = ["的", "地", "得", "天空", "大地", "光芒", "气息"]
            desc_ratio = sum(1 for m in desc_markers if m in p) / max(1, len(p))
            rhythm_curve.append(
                {
                    "paragraph_index": i,
                    "action_density": round(action_ratio * 100, 2),
                    "dialogue": has_dialogue,
                    "description_density": round(desc_ratio * 100, 2),
                    "length": len(p),
                }
            )

        return {
            "plot_density_per_1k": plot_density,
            "emotion_peak_frequency": emotion_peak_freq,
            "emotion_breakdown": {
                "exclamation": exclamation_count,
                "question": question_count,
                "emotion_keywords": emotion_count,
            },
            "twist_analysis": twist_analysis,
            "rhythm_curve": rhythm_curve,
            "word_count": word_count,
        }

    # ── 维度三：正文风格仿写分析 ──────────────────────

    def analyze_style(self, text: str) -> dict[str, Any]:
        """正文风格仿写分析

        Args:
            text: 参考文本

        Returns:
            包含句长、句式分布、描写密度、对话占比、高频词、段落长度的字典
        """
        if not text or len(text.strip()) < 50:
            return {
                "avg_sentence_length": 0.0,
                "sentence_type_distribution": {},
                "descriptive_density": 0.0,
                "dialogue_ratio": 0.0,
                "top_words": [],
                "avg_paragraph_length": 0.0,
                "word_count": len(text),
            }

        word_count = len(text.replace(" ", "").replace("\n", ""))

        # 句长与句式分布
        sentences = re.split(r"(?<=[。！？!?…])", text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 1]
        if sentences:
            lengths = [len(s) for s in sentences]
            avg_sentence_length = round(sum(lengths) / len(lengths), 1)

            declarative = sum(1 for s in sentences if s.endswith(("。", ".")))
            interrogative = sum(1 for s in sentences if s.endswith(("？", "?")))
            exclamatory = sum(1 for s in sentences if s.endswith(("！", "!")))
            other = len(sentences) - declarative - interrogative - exclamatory

            sentence_type_distribution = {
                "declarative": round(declarative / max(1, len(sentences)), 3),
                "interrogative": round(interrogative / max(1, len(sentences)), 3),
                "exclamatory": round(exclamatory / max(1, len(sentences)), 3),
                "other": round(other / max(1, len(sentences)), 3),
                "total": len(sentences),
            }
        else:
            avg_sentence_length = 0.0
            sentence_type_distribution = {}

        # 描写密度
        adj_markers = ["的", "地", "得"]
        degree_words = ["非常", "十分", "格外", "异常", "极其", "极为", "甚是", "相当", "颇为"]
        color_words = ["红", "蓝", "绿", "黄", "白", "黑", "紫", "金", "银", "灰", "青", "橙"]
        total_adj = sum(text.count(m) for m in adj_markers)
        total_degree = sum(text.count(w) for w in degree_words)
        total_color = sum(text.count(w) for w in color_words)
        descriptive_density = round(
            (total_adj + total_degree * 2 + total_color) / max(1, word_count) * 100, 2
        )

        # 对话占比
        dialogues = re.findall(r'[""「『]([^""」』]+)[""」』]', text)
        dialogue_chars = sum(len(d) for d in dialogues)
        dialogue_ratio = round(dialogue_chars / max(1, word_count), 3)

        # 高频词 TOP20（jieba 分词，延迟导入）
        top_words: list[dict[str, Any]] = []
        self._ensure_jieba()
        try:
            import jieba

            stopwords = {
                "的",
                "了",
                "在",
                "是",
                "我",
                "有",
                "和",
                "就",
                "不",
                "人",
                "都",
                "一",
                "一个",
                "上",
                "也",
                "很",
                "到",
                "说",
                "要",
                "去",
                "你",
                "会",
                "着",
                "没有",
                "看",
                "好",
                "自己",
                "这",
                "他",
                "她",
                "它",
                "们",
                "那",
                "被",
                "从",
                "把",
                "让",
                "向",
                "对",
                "与",
                "及",
                "等",
                "而",
                "但",
                "却",
                "又",
                "还",
                "已",
                "已经",
                "曾",
                "将",
                "正",
                "刚",
                "才",
                "便",
                "于是",
                "因此",
                "所以",
                "因为",
                "如果",
                "虽然",
                "但是",
                "然而",
                "不过",
                "只是",
                "只有",
                "只要",
                "无论",
                "不管",
                "即使",
                "既然",
                "那么",
                "这个",
                "那个",
                "什么",
                "怎么",
                "为什么",
                "哪里",
                "谁",
                "多少",
                "几",
                "些",
                "每",
                "各",
                "某",
                "另",
                "其他",
                "可以",
                "能",
                "能够",
                "应该",
                "必须",
                "需要",
                "想",
                "知道",
                "觉得",
                "认为",
                "发现",
                "看到",
                "听到",
                "出来",
                "起来",
                "下来",
                "上去",
                "过来",
                "过去",
                "回来",
                "进来",
                "出去",
            }
            words = jieba.lcut(text)
            word_freq: dict[str, int] = {}
            for raw_word in words:
                word = raw_word.strip()
                if len(word) >= 2 and word not in stopwords and not word.isdigit():
                    word_freq[word] = word_freq.get(word, 0) + 1
            top20 = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
            top_words = [{"word": w, "count": c} for w, c in top20]
        except ImportError:
            chars = [c for c in text if "\u4e00" <= c <= "\u9fff"]
            if len(chars) >= 2:
                bigrams: dict[str, int] = {}
                for i in range(len(chars) - 1):
                    bg = chars[i] + chars[i + 1]
                    bigrams[bg] = bigrams.get(bg, 0) + 1
                top20 = sorted(bigrams.items(), key=lambda x: x[1], reverse=True)[:20]
                top_words = [{"word": w, "count": c} for w, c in top20]

        # 段落平均长度
        paragraphs = [p for p in text.split("\n") if p.strip()]
        avg_paragraph_length = (
            round(sum(len(p) for p in paragraphs) / max(1, len(paragraphs)), 1)
            if paragraphs
            else 0.0
        )

        return {
            "avg_sentence_length": avg_sentence_length,
            "sentence_type_distribution": sentence_type_distribution,
            "descriptive_density": descriptive_density,
            "dialogue_ratio": dialogue_ratio,
            "top_words": top_words,
            "avg_paragraph_length": avg_paragraph_length,
            "word_count": word_count,
        }

    # ── 维度四：结构仿写分析 ──────────────────────────

    def analyze_structure(self, text: str) -> dict[str, Any]:
        """结构仿写分析

        Args:
            text: 参考文本（可含章节标记）

        Returns:
            包含章节字数分布、开篇模式、结尾模式、卷章架构建议的字典
        """
        if not text or len(text.strip()) < 50:
            return {
                "chapter_word_distribution": [],
                "opening_mode": "未知",
                "ending_mode": "未知",
                "architecture_suggestion": "样本不足",
                "chapter_count": 0,
                "word_count": len(text),
            }

        word_count = len(text.replace(" ", "").replace("\n", ""))

        # 章节分割
        chapter_pattern = re.compile(
            r"(?:第[一二三四五六七八九十百千零\d]+[章节回卷集部]|Chapter\s*\d+|"
            r"CHAPTER\s*\d+|^\s*#{1,3}\s)",
            re.MULTILINE,
        )
        splits = list(chapter_pattern.finditer(text))

        chapters: list[dict[str, Any]] = []
        if splits:
            for i, match in enumerate(splits):
                start = match.start()
                end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
                chapter_text = text[start:end].strip()
                chapter_word = len(chapter_text.replace(" ", "").replace("\n", ""))
                title_match = re.match(
                    r"(第[一二三四五六七八九十百千零\d]+[章节回卷集部][^\n]*)", chapter_text
                )
                title = title_match.group(1).strip() if title_match else f"第{i + 1}章"
                chapters.append(
                    {
                        "index": i + 1,
                        "title": title[:50],
                        "word_count": chapter_word,
                    }
                )
        else:
            chunk_size = 3000
            clean_text = text.replace(" ", "").replace("\n", "")
            for i in range(0, len(clean_text), chunk_size):
                chunk = clean_text[i : i + chunk_size]
                chapters.append(
                    {
                        "index": i // chunk_size + 1,
                        "title": f"虚拟第{i // chunk_size + 1}章",
                        "word_count": len(chunk),
                    }
                )

        # 章节字数分布
        chapter_words = [c["word_count"] for c in chapters]
        avg_chapter_words = (
            round(sum(chapter_words) / len(chapter_words), 0) if chapter_words else 0
        )
        chapter_word_distribution = {
            "chapter_count": len(chapters),
            "avg_words": avg_chapter_words,
            "min_words": min(chapter_words) if chapter_words else 0,
            "max_words": max(chapter_words) if chapter_words else 0,
            "chapters": chapters[:50],
        }

        # 开篇模式分析（取前500字）
        opening_text = text[:500]
        opening_has_dialogue = bool(re.search(r'[""「『]', opening_text))
        opening_has_action = any(v in opening_text for v in self.ACTION_VERBS)
        opening_has_description = any(
            m in opening_text for m in ["天空", "大地", "光芒", "气息", "的", "景色", "景象"]
        )
        opening_has_suspense = any(
            m in opening_text for m in ["？", "秘密", "未知", "谜团", "谁", "什么"]
        )

        if opening_has_dialogue and not opening_has_description:
            opening_mode = "对话开篇（快速进入角色互动）"
        elif opening_has_action and not opening_has_description:
            opening_mode = "动作开篇（直接进入冲突/战斗）"
        elif opening_has_suspense:
            opening_mode = "悬念开篇（抛出谜题吸引读者）"
        elif opening_has_description:
            opening_mode = "描写开篇（环境/氛围铺垫）"
        else:
            opening_mode = "叙述开篇（平铺直叙引入）"

        # 结尾模式分析（取最后500字）
        ending_text = text[-500:]
        ending_has_suspense = any(m in ending_text for m in self.SUSPENSE_ENDINGS)
        ending_has_summary = any(
            m in ending_text for m in ["终于", "最终", "至此", "一切", "从此", "后来"]
        )
        ending_has_emotion = any(
            m in ending_text for m in ["泪", "笑", "怒", "悲", "喜", "心", "感慨", "叹息"]
        )

        if ending_has_suspense and ending_text.rstrip().endswith(("？", "!", "！", "……")):
            ending_mode = "悬念结尾（钩子留到下一章）"
        elif ending_has_summary:
            ending_mode = "总结结尾（收束本章情节）"
        elif ending_has_emotion:
            ending_mode = "情感结尾（情绪共鸣收尾）"
        else:
            ending_mode = "自然结尾（情节告一段落）"

        # 卷章宏观架构建议
        if len(chapters) >= 10:
            if avg_chapter_words >= 3500:
                arch = "长章节模式（3500+字/章），适合深度剧情流，建议每10章一个小高潮"
            elif avg_chapter_words >= 2000:
                arch = "标准章节模式（2000-3500字/章），适合主流网文，建议每5-8章一个转折"
            else:
                arch = "短章节模式（2000字以下/章），适合快节奏爽文，建议每3-5章一个爽点"
        else:
            arch = "样本章节较少，建议积累更多章节后分析宏观架构"

        return {
            "chapter_word_distribution": chapter_word_distribution,
            "opening_mode": opening_mode,
            "ending_mode": ending_mode,
            "architecture_suggestion": arch,
            "chapter_count": len(chapters),
            "word_count": word_count,
        }

    # ── 多书共性规律提炼 ──────────────────────────────

    def extract_common_patterns(  # noqa: PLR0912
        self, analyses: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """多书共性规律提炼

        Args:
            analyses: 最多3本参考书的 analyze_book 结果列表

        Returns:
            包含共性规律（黄金公式）和差异点的字典
        """
        if not analyses:
            return {"common_patterns": [], "differences": [], "book_count": 0}

        analyses = analyses[:3]
        book_count = len(analyses)

        common_patterns: list[str] = []
        differences: list[dict[str, Any]] = []

        # 设定维度共性
        setting_results = [a.get("setting", {}) for a in analyses]
        setting_densities = [r.get("setting_density_per_1k", 0) for r in setting_results]
        if all(d >= 2 for d in setting_densities):
            common_patterns.append(
                f"设定密度均≥2/千字（均值{round(sum(setting_densities) / book_count, 1)}），"
                "属于中高密度设定流"
            )
        elif all(d < 2 for d in setting_densities):
            common_patterns.append("设定密度均<2/千字，属于低密度快节奏流")

        all_type_sets = []
        for r in setting_results:
            types = set(r.get("type_distribution", {}).keys())
            all_type_sets.append(types)
        if all_type_sets:
            common_types = set.intersection(*all_type_sets) if book_count > 1 else all_type_sets[0]
            if common_types:
                common_patterns.append("核心设定类型重合: " + "、".join(sorted(common_types)))

        # 情节维度共性
        plot_results = [a.get("plot", {}) for a in analyses]
        plot_densities = [r.get("plot_density_per_1k", 0) for r in plot_results]
        if plot_densities:
            avg_plot_density = sum(plot_densities) / book_count
            if all(
                abs(d - avg_plot_density) / max(1, avg_plot_density) < 0.3 for d in plot_densities
            ):
                common_patterns.append(
                    f"情节密度接近（均值{round(avg_plot_density, 1)}/千字），节奏一致性高"
                )

        emotion_freqs = [r.get("emotion_peak_frequency", 0) for r in plot_results]
        if all(f >= 2 for f in emotion_freqs):
            common_patterns.append("情绪波峰频率均≥2/千字，强情绪驱动型")

        # 风格维度共性
        style_results = [a.get("style", {}) for a in analyses]
        sentence_lengths = [r.get("avg_sentence_length", 0) for r in style_results]
        if sentence_lengths:
            avg_sl = sum(sentence_lengths) / book_count
            if all(abs(sl - avg_sl) / max(1, avg_sl) < 0.25 for sl in sentence_lengths):
                common_patterns.append(f"平均句长接近（均值{round(avg_sl, 1)}字），句式风格统一")

        dialogue_ratios = [r.get("dialogue_ratio", 0) for r in style_results]
        if dialogue_ratios:
            avg_dr = sum(dialogue_ratios) / book_count
            if all(abs(dr - avg_dr) < 0.1 for dr in dialogue_ratios):
                common_patterns.append(f"对话占比接近（均值{round(avg_dr * 100, 1)}%）")

        all_top_word_sets = []
        for r in style_results:
            words = {item["word"] for item in r.get("top_words", [])[:10]}
            all_top_word_sets.append(words)
        if all_top_word_sets:
            common_top_words = (
                set.intersection(*all_top_word_sets) if book_count > 1 else all_top_word_sets[0]
            )
            if common_top_words:
                common_patterns.append(
                    "高频词重合（TOP10交集）: " + "、".join(sorted(common_top_words)[:10])
                )

        # 结构维度共性
        structure_results = [a.get("structure", {}) for a in analyses]
        opening_modes = [r.get("opening_mode", "") for r in structure_results]
        if len(set(opening_modes)) == 1 and opening_modes[0]:
            common_patterns.append(f"开篇模式一致: {opening_modes[0]}")

        ending_modes = [r.get("ending_mode", "") for r in structure_results]
        if len(set(ending_modes)) == 1 and ending_modes[0]:
            common_patterns.append(f"结尾模式一致: {ending_modes[0]}")

        # 差异点分析
        if book_count > 1:
            if max(setting_densities) - min(setting_densities) > 3:
                _sd_min = min(setting_densities)
                _sd_max = max(setting_densities)
                differences.append(
                    {
                        "dimension": "设定密度",
                        "detail": f"差异较大（{_sd_min}~{_sd_max}/千字）",
                    }
                )
            if max(plot_densities) - min(plot_densities) > 10:
                differences.append(
                    {
                        "dimension": "情节密度",
                        "detail": f"差异较大（{min(plot_densities)}~{max(plot_densities)}/千字）",
                    }
                )
            if max(sentence_lengths) - min(sentence_lengths) > 10:
                differences.append(
                    {
                        "dimension": "平均句长",
                        "detail": f"差异较大（{min(sentence_lengths)}~{max(sentence_lengths)}字）",
                    }
                )
            if len(set(opening_modes)) > 1:
                differences.append(
                    {
                        "dimension": "开篇模式",
                        "detail": "不一致: " + " / ".join(set(opening_modes)),
                    }
                )

        golden_formula = ""
        if common_patterns:
            golden_formula = " | ".join(common_patterns[:5])

        return {
            "common_patterns": common_patterns,
            "differences": differences,
            "golden_formula": golden_formula,
            "book_count": book_count,
        }

    # ── 综合分析 ──────────────────────────────────────

    def analyze_book(
        self,
        title: str,
        text: str,
        dimensions: list[str] | None = None,
        book_id: str = "",
        data_dir: str = "data",
    ) -> dict[str, Any]:
        """综合分析 — 对一本书执行四个维度的完整分析

        Args:
            title: 书名
            text: 参考文本
            dimensions: 要分析的维度列表，默认全部
            book_id: 书籍ID，用于存储
            data_dir: 数据目录

        Returns:
            包含四个维度分析结果的完整报告
        """
        if dimensions is None:
            dimensions = ["setting", "plot", "style", "structure"]

        result: dict[str, Any] = {
            "title": title,
            "book_id": book_id,
            "analyzed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "dimensions": dimensions,
            "word_count": len(text.replace(" ", "").replace("\n", "")),
        }

        if "setting" in dimensions:
            result["setting"] = self.analyze_setting(text)
        if "plot" in dimensions:
            result["plot"] = self.analyze_plot(text)
        if "style" in dimensions:
            result["style"] = self.analyze_style(text)
        if "structure" in dimensions:
            result["structure"] = self.analyze_structure(text)

        # 存储到 data/books/book_<id>/style_analysis/
        if book_id:
            try:
                analysis_id = f"sa_{int(time.time() * 1000)}"
                result["analysis_id"] = analysis_id
                save_dir = Path(data_dir) / "books" / f"book_{book_id}" / "style_analysis"
                save_dir.mkdir(parents=True, exist_ok=True)
                save_path = save_dir / f"{analysis_id}.json"
                with save_path.open("w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)

                # 更新索引文件
                index_path = save_dir / "_index.json"
                index: list[dict[str, Any]] = []
                if index_path.exists():
                    try:
                        with index_path.open(encoding="utf-8") as f:
                            index = json.load(f)
                    except (json.JSONDecodeError, OSError):
                        index = []
                index.append(
                    {
                        "analysis_id": analysis_id,
                        "title": title,
                        "word_count": result["word_count"],
                        "dimensions": dimensions,
                        "analyzed_at": result["analyzed_at"],
                    }
                )
                with index_path.open("w", encoding="utf-8") as f:
                    json.dump(index, f, ensure_ascii=False, indent=2)
            except OSError as e:
                logger.debug(f"[StyleLearner] 存储分析结果失败: {e}")

        return result
