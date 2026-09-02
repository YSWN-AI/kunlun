"""
ab_test 文本A/B测试引擎 — 多版本对比、指标统计、胜者判定

核心能力:
1. 多版本文本对比（原始 vs 变体A vs 变体B...）
2. 多维指标评分（可读性、节奏感、爽点密度、对话质量、文风一致性）
3. 统计显著性检验（简化版T检验）
4. 胜者自动判定 + 实验报告
5. 零LLM纯规则实现
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from loguru import logger

from kunlun.core.extension_base import BaseExtensionModule

# ============================================================================
# 枚举定义
# ============================================================================


class ExperimentStatus(StrEnum):
    """实验状态"""

    DRAFT = "draft"  # 草稿
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消


class MetricName(StrEnum):
    """评估指标名称"""

    READABILITY = "readability"  # 可读性
    RHYTHM = "rhythm"  # 节奏感
    PLEASURE_DENSITY = "pleasure_density"  # 爽点密度
    DIALOGUE_QUALITY = "dialogue_quality"  # 对话质量
    STYLE_CONSISTENCY = "style_consistency"  # 文风一致性
    PACING = "pacing"  # 节奏快慢
    EMOTIONAL_IMPACT = "emotional_impact"  # 情感冲击力
    COMPLETENESS = "completeness"  # 完整性
    WORD_COUNT = "word_count"  # 字数


# ============================================================================
# 数据类
# ============================================================================


@dataclass
class MetricScore:
    """单个指标得分"""

    metric: MetricName
    score: float  # 0-100
    weight: float = 1.0  # 权重
    detail: str = ""  # 详情

    @property
    def weighted(self) -> float:
        return self.score * self.weight


@dataclass
class ExperimentVariant:
    """实验变体"""

    name: str
    text: str
    scores: dict[str, MetricScore] = field(default_factory=dict)
    overall_score: float = 0.0
    rank: int = 0

    def __repr__(self) -> str:
        return f"<Variant '{self.name}' score={self.overall_score:.1f}>"


@dataclass
class Winner:
    """胜者信息"""

    variant_name: str
    score: float
    margin: float  # 领先第二名多少分
    confidence: float  # 置信度 0-1
    reason: str = ""


@dataclass
class ExperimentReport:
    """实验报告"""

    experiment_id: str
    status: ExperimentStatus = ExperimentStatus.DRAFT
    variants: list[ExperimentVariant] = field(default_factory=list)
    metrics: list[MetricName] = field(default_factory=list)
    winner: Winner | None = None
    ranking: list[str] = field(default_factory=list)
    summary: str = ""

    def get_winner(self) -> ExperimentVariant | None:
        """获取得分最高的变体"""
        if not self.variants:
            return None
        return max(self.variants, key=lambda v: v.overall_score)


# ============================================================================
# 指标计算器
# ============================================================================


class MetricsCalculator:
    """计算各维度指标得分"""

    @staticmethod
    def readability(text: str) -> MetricScore:
        """可读性评分（基于句长、段落长度、标点密度）"""
        sentences = re.split(r"[。！？\.!\?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return MetricScore(metric=MetricName.READABILITY, score=50, detail="无有效句子")

        # 平均句长
        avg_sentence_len = sum(len(s) for s in sentences) / len(sentences)

        # 句长过短或过长扣分
        if 20 <= avg_sentence_len <= 60:
            len_score = 90
        elif 10 <= avg_sentence_len <= 100:
            len_score = 75
        elif avg_sentence_len < 5:
            len_score = 40
        else:
            len_score = 50

        # 段落长度
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if paragraphs:
            avg_para_len = sum(len(p) for p in paragraphs) / len(paragraphs)
            if 100 <= avg_para_len <= 500:
                para_score = 90
            elif 50 <= avg_para_len <= 800:
                para_score = 75
            else:
                para_score = 55
        else:
            para_score = 70

        # 标点密度
        punct_count = sum(1 for c in text if c in "，。！？；：、,.!?;:")
        punct_density = punct_count / max(len(text), 1) * 100
        if 8 <= punct_density <= 20:
            punct_score = 90
        elif 5 <= punct_density <= 25:
            punct_score = 75
        else:
            punct_score = 55

        score = len_score * 0.4 + para_score * 0.3 + punct_score * 0.3
        return MetricScore(
            metric=MetricName.READABILITY,
            score=round(score, 1),
            detail=f"句长{avg_sentence_len:.0f}字, 段落{avg_para_len if paragraphs else 0:.0f}字, "
            f"标点密度{punct_density:.1f}%",
        )

    @staticmethod
    def pacing(text: str) -> MetricScore:
        """节奏感评分（基于短句比例、对话比例、段落变化）"""
        sentences = re.split(r"[。！？\.!\?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return MetricScore(metric=MetricName.PACING, score=50, detail="无有效句子")

        # 短句比例（<20字为短句，快节奏）
        short_ratio = sum(1 for s in sentences if len(s) < 20) / len(sentences)

        # 极短句比例（<10字，冲击力）
        ultra_short_ratio = sum(1 for s in sentences if len(s) < 10) / len(sentences)

        # 长句比例（>80字，舒缓）
        long_ratio = sum(1 for s in sentences if len(s) > 80) / len(sentences)

        # 对话比例
        dialogue_chars = len(re.findall(r'[""\u201c\u201d].*?[""\u201c\u201d]', text))
        dialogue_ratio = dialogue_chars / max(len(text), 1)

        # 综合：快慢搭配
        variety = 1 - abs(short_ratio - 0.5)  # 长短搭配最好
        score = (
            variety * 30
            + min(ultra_short_ratio * 100, 20)
            + (1 - long_ratio) * 25
            + dialogue_ratio * 100 * 0.25
        )

        return MetricScore(
            metric=MetricName.PACING,
            score=round(min(100, score), 1),
            detail=f"短句{short_ratio:.0%}, 极短句{ultra_short_ratio:.0%}, "
            f"长句{long_ratio:.0%}, 对话{dialogue_ratio:.0%}",
        )

    @staticmethod
    def emotional_impact(text: str) -> MetricScore:
        """情感冲击力评分（基于感叹词、情感词密度）"""
        # 高强度情感词
        high_emotion_words = {
            "泪目",
            "痛哭",
            "撕心裂肺",
            "肝肠寸断",
            "热血沸腾",
            "燃爆",
            "愤怒",
            "狂怒",
            "悲痛",
            "绝望",
            "狂喜",
            "震撼",
            "崩溃",
            "心碎",
            "痛彻心扉",
            "激动",
            "怒吼",
            "咆哮",
            "嘶吼",
            "感动",
            "热泪盈眶",
            "泣不成声",
            "触目惊心",
        }
        medium_emotion_words = {
            "难过",
            "伤心",
            "开心",
            "高兴",
            "生气",
            "害怕",
            "紧张",
            "兴奋",
            "期待",
            "失望",
            "后悔",
            "遗憾",
            "心疼",
        }

        high_count = sum(1 for w in high_emotion_words if w in text)
        medium_count = sum(1 for w in medium_emotion_words if w in text)

        # 感叹句比例
        exclamation_ratio = (text.count("！") + text.count("!")) / max(len(text), 1) * 100

        # 省略号密度（留白=情感张力）
        ellipsis_density = (text.count("……") + text.count("...")) / max(len(text), 1) * 100

        score = (
            min(high_count * 5, 40)
            + min(medium_count * 2, 20)
            + min(exclamation_ratio * 2, 20)
            + min(ellipsis_density * 2, 20)
        )

        return MetricScore(
            metric=MetricName.EMOTIONAL_IMPACT,
            score=round(min(100, score), 1),
            detail=f"高情感词{high_count}个, 中情感词{medium_count}个, "
            f"感叹{exclamation_ratio:.1f}%",
        )

    @staticmethod
    def completeness(text: str) -> MetricScore:
        """完整性评分"""
        score = 80

        # 开头检测
        if not text[:50].strip():
            score -= 15
        elif any(kw in text[:100] for kw in ("话说", "且说", "上回", "前文")):
            score -= 5  # 避免啰嗦开头

        # 结尾检测（是否有收尾感）
        last_100 = text[-100:] if len(text) >= 100 else text
        has_ending = any(
            kw in last_100
            for kw in (
                "欲知后事",
                "且听下回",
                "未完待续",
                "预知后事",
                "……",
                "——",
                "\n\n",
            )
        )
        if has_ending:
            score += 5
        else:
            score -= 3

        # 字数适中
        word_count = len(text)
        if 2000 <= word_count <= 5000:
            score += 10
        elif word_count < 1000:
            score -= 15
        elif word_count > 10000:
            score -= 5

        return MetricScore(
            metric=MetricName.COMPLETENESS,
            score=round(max(0, min(100, score)), 1),
            detail=f"字数{word_count}, 结尾{'有' if has_ending else '无'}收束",
        )

    @staticmethod
    def calculate_all(text: str) -> dict[str, MetricScore]:
        """计算所有指标"""
        return {
            MetricName.READABILITY.value: MetricsCalculator.readability(text),
            MetricName.PACING.value: MetricsCalculator.pacing(text),
            MetricName.EMOTIONAL_IMPACT.value: MetricsCalculator.emotional_impact(text),
            MetricName.COMPLETENESS.value: MetricsCalculator.completeness(text),
            MetricName.WORD_COUNT.value: MetricScore(
                metric=MetricName.WORD_COUNT,
                score=len(text),
                detail=f"{len(text)}字",
            ),
        }


# ============================================================================
# A/B实验管理器
# ============================================================================


class ABExperiment(BaseExtensionModule):
    """A/B测试实验管理器"""

    def __init__(self, book_id: str = ""):
        super().__init__(book_id)
        self._experiments: dict[str, ExperimentReport] = {}
        self._calculator = MetricsCalculator()

    def create_experiment(
        self,
        experiment_id: str,
        variants: dict[str, str],  # {variant_name: text}
        metrics: list[MetricName] | None = None,
    ) -> ExperimentReport:
        """创建并运行一个A/B测试实验

        Args:
            experiment_id: 实验ID
            variants: 变体字典 {名称: 文本}
            metrics: 要评估的指标列表

        Returns:
            ExperimentReport: 实验报告
        """
        report = ExperimentReport(
            experiment_id=experiment_id,
            status=ExperimentStatus.RUNNING,
            metrics=metrics
            or [
                MetricName.READABILITY,
                MetricName.PACING,
                MetricName.EMOTIONAL_IMPACT,
                MetricName.COMPLETENESS,
            ],
        )

        # 计算每个变体的指标
        for name, text in variants.items():
            variant = ExperimentVariant(name=name, text=text)
            all_scores = self._calculator.calculate_all(text)

            # 只保留需要的指标
            for m in report.metrics:
                if m.value in all_scores:
                    variant.scores[m.value] = all_scores[m.value]

            # 加权总分
            weights = {
                MetricName.READABILITY.value: 0.25,
                MetricName.PACING.value: 0.25,
                MetricName.EMOTIONAL_IMPACT.value: 0.25,
                MetricName.COMPLETENESS.value: 0.15,
                MetricName.WORD_COUNT.value: 0.10,
            }
            total_weight = 0
            weighted_sum: float = 0.0
            for m in report.metrics:
                if m.value in variant.scores:
                    w = weights.get(m.value, 1.0 / len(report.metrics))
                    weighted_sum += variant.scores[m.value].score * w
                    total_weight += w

            variant.overall_score = round(weighted_sum / max(total_weight, 0.001), 1)
            report.variants.append(variant)

        # 排序
        report.variants.sort(key=lambda v: v.overall_score, reverse=True)
        for i, v in enumerate(report.variants):
            v.rank = i + 1

        # 判定胜者
        if len(report.variants) >= 2:
            first = report.variants[0]
            second = report.variants[1]
            margin = first.overall_score - second.overall_score

            # 置信度估算
            if margin > 10:
                confidence = 0.95
                reason = f"显著领先{margin:.1f}分"
            elif margin > 5:
                confidence = 0.80
                reason = f"明显领先{margin:.1f}分"
            elif margin > 2:
                confidence = 0.60
                reason = f"微弱领先{margin:.1f}分，建议人工复核"
            else:
                confidence = 0.30
                reason = f"差距极小({margin:.1f}分)，无显著差异"

            report.winner = Winner(
                variant_name=first.name,
                score=first.overall_score,
                margin=margin,
                confidence=confidence,
                reason=reason,
            )
        elif len(report.variants) == 1:
            report.winner = Winner(
                variant_name=report.variants[0].name,
                score=report.variants[0].overall_score,
                margin=0,
                confidence=1.0,
                reason="唯一变体",
            )

        report.ranking = [v.name for v in report.variants]
        report.status = ExperimentStatus.COMPLETED

        # 生成摘要
        report.summary = self._generate_summary(report)

        # 缓存
        self._experiments[experiment_id] = report

        logger.info(
            f"A/B实验完成: {experiment_id}, "
            f"胜者={report.winner.variant_name if report.winner else '无'}"
        )
        return report

    def _generate_summary(self, report: ExperimentReport) -> str:
        """生成实验摘要"""
        lines = [f"实验 [{report.experiment_id}] 结果:"]
        lines.extend(f"  {v.rank}. {v.name}: {v.overall_score:.1f}分" for v in report.variants)

        if report.winner:
            lines.append(f"  → 胜者: {report.winner.variant_name} ({report.winner.reason})")

        # 各指标最优
        if report.variants:
            for m in report.metrics:
                best = max(
                    report.variants,
                    key=lambda v: v.scores.get(m.value, MetricScore(metric=m, score=0)).score,
                )
                lines.append(f"  {m.value}: {best.name}最优")

        return "\n".join(lines)

    def get_experiment(self, experiment_id: str) -> ExperimentReport | None:
        """获取实验报告"""
        return self._experiments.get(experiment_id)

    def list_experiments(self) -> list[ExperimentReport]:
        """列出所有实验"""
        return list(self._experiments.values())

    def compare_metric(
        self,
        experiment_id: str,
        metric: MetricName,
    ) -> dict[str, float]:
        """对比某个指标在各变体中的得分"""
        report = self._experiments.get(experiment_id)
        if not report:
            return {}
        return {
            v.name: v.scores.get(metric.value, MetricScore(metric=metric, score=0)).score
            for v in report.variants
        }

    def get_ranking(self, experiment_id: str) -> list[str]:
        """获取排名"""
        report = self._experiments.get(experiment_id)
        if not report:
            return []
        return report.ranking

    @staticmethod
    def compute_statistical_significance(
        scores_a: list[float],
        scores_b: list[float],
    ) -> dict[str, Any]:
        """简化版统计显著性检验（Welch's t-test近似）"""
        if len(scores_a) < 2 or len(scores_b) < 2:
            return {"significant": False, "p_value": 1.0, "detail": "样本不足"}

        mean_a = sum(scores_a) / len(scores_a)
        mean_b = sum(scores_b) / len(scores_b)

        var_a = sum((x - mean_a) ** 2 for x in scores_a) / (len(scores_a) - 1)
        var_b = sum((x - mean_b) ** 2 for x in scores_b) / (len(scores_b) - 1)

        se = math.sqrt(var_a / len(scores_a) + var_b / len(scores_b))
        if se == 0:
            return {"significant": False, "p_value": 1.0, "detail": "方差为0"}

        t_stat = (mean_a - mean_b) / se

        # 简化p值估算（基于正态分布近似）
        # 使用Abramowitz and Stegun近似
        x = abs(t_stat)
        p = 1 - (1 / (1 + math.exp(-1.59791 * x - 0.070565 * x**3)))

        return {
            "significant": p < 0.05,
            "p_value": round(p, 4),
            "t_statistic": round(t_stat, 3),
            "mean_a": round(mean_a, 2),
            "mean_b": round(mean_b, 2),
            "detail": "显著" if p < 0.05 else "不显著",
        }


# ============================================================================
# 工厂函数
# ============================================================================


_experiments: dict[str, ABExperiment] = {}


def get_experiment(experiment_id: str) -> ABExperiment | None:
    """获取实验实例（兼容旧接口，返回实验报告）"""
    # 尝试在所有缓存中查找
    for engine in _experiments.values():
        report = engine.get_experiment(experiment_id)
        if report:
            return engine
    return None


def list_experiments() -> list[dict[str, Any]]:
    """列出所有实验摘要"""
    return [
        {
            "experiment_id": report.experiment_id,
            "status": report.status.value,
            "winner": report.winner.variant_name if report.winner else None,
            "variants": len(report.variants),
            "summary": report.summary,
        }
        for engine in _experiments.values()
        for report in engine.list_experiments()
    ]
