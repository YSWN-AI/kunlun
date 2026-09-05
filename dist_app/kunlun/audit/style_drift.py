"""
昆仑创作引擎 — 文风漂移检测器 (Style Drift Detector)

借鉴 PlotPilot 的文风漂移检测，实现跨章节文风一致性监控。

核心功能:
1. 单章内前后风格一致性检测（已在 post_write_validator 中实现基础版）
2. 跨章节文风趋势分析（本模块实现）
3. 文风指纹对比（与目标文风的偏差）
4. 自动预警与建议

检测维度:
- 句长分布: 均值/标准差/变异系数的跨章节变化
- 词汇多样性: 型例比 (TTR) / 独特词汇占比
- 对话比例: 对话占全文比例的变化
- 段落结构: 段落长度分布的变化
- 修辞密度: 比喻/排比/拟人等修辞手法的使用频率
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class StyleProfile:
    """单章文风特征档案"""

    chapter: int
    # 句长统计
    avg_sentence_length: float = 0.0
    std_sentence_length: float = 0.0
    cv_sentence_length: float = 0.0  # 变异系数
    # 词汇统计
    total_words: int = 0
    unique_words: int = 0
    ttr: float = 0.0  # 型例比 (Type-Token Ratio)
    # 对话统计
    dialogue_ratio: float = 0.0
    dialogue_avg_length: float = 0.0
    # 段落统计
    avg_paragraph_length: float = 0.0
    std_paragraph_length: float = 0.0
    # 修辞统计
    metaphor_count: float = 0.0  # 比喻
    parallelism_count: float = 0.0  # 排比
    personification_count: float = 0.0  # 拟人
    # 高频词 (前20)
    top_words: dict[str, int] = field(default_factory=dict)


@dataclass
class DriftAlert:
    """漂移告警"""

    chapter: int
    dimension: str  # 告警维度
    current_value: float
    baseline_value: float
    deviation: float  # 偏差比例
    severity: str  # "warning" / "critical"
    suggestion: str = ""


@dataclass
class DriftReport:
    """漂移检测报告"""

    book_id: str
    chapters_analyzed: int
    profiles: list[StyleProfile] = field(default_factory=list)
    alerts: list[DriftAlert] = field(default_factory=list)
    overall_stability: float = 1.0  # 0-1，1=完全稳定
    trend_direction: str = "stable"  # "stable" / "drifting" / "diverging"


class StyleDriftDetector:
    """
    文风漂移检测器

    用法:
        detector = StyleDriftDetector()
        profile = detector.analyze_chapter(text, chapter=5)
        drift_report = detector.compare_with_baseline(profile, baseline_profiles)
    """

    # 漂移检测阈值
    SENTENCE_LENGTH_DRIFT_THRESHOLD = 0.4  # 句长变异>40%触发告警
    TTR_DRIFT_THRESHOLD = 0.3  # TTR变化>30%触发告警
    DIALOGUE_RATIO_DRIFT_THRESHOLD = 0.5  # 对话比例变化>50%触发告警
    PARAGRAPH_LENGTH_DRIFT_THRESHOLD = 0.5  # 段落长度变化>50%触发告警
    RHETORIC_DENSITY_DRIFT_THRESHOLD = 0.6  # 修辞密度变化>60%触发告警

    # 比喻词
    METAPHOR_MARKERS = ["像", "仿佛", "宛如", "犹如", "如同", "好比", "似", "若"]

    # 排比标记（连续相同句式开头）
    PARALLELISM_PATTERNS = [
        r"(?:^|。)(?:他|她|它|这|那|不|没)",
        r"(?:是|有|在|让|把|被|给)",
    ]

    # 拟人标记
    PERSONIFICATION_PATTERNS = [
        r"(?:风|雨|阳光|月光|大地|天空|大海|河流)(?:在|仿佛|好像|似乎)",
    ]

    def analyze_chapter(self, text: str, chapter: int) -> StyleProfile:
        """分析单章文风特征"""
        if not text:
            return StyleProfile(chapter=chapter)

        profile = StyleProfile(chapter=chapter)

        # 1. 句长统计
        sentences = re.findall(r"[^。！？\n]{5,}[。！？]", text)
        if sentences:
            lengths = [len(s) for s in sentences]
            profile.avg_sentence_length = sum(lengths) / len(lengths)
            if len(lengths) > 1:
                mean = profile.avg_sentence_length
                variance = sum((v - mean) ** 2 for v in lengths) / (len(lengths) - 1)
                profile.std_sentence_length = math.sqrt(variance)
                profile.cv_sentence_length = profile.std_sentence_length / max(mean, 1)

        # 2. 词汇统计（中文以字为基本单位，词用2-gram近似）
        # 使用字符级2-gram作为"词"的近似
        words = [
            text[i : i + 2]
            for i in range(len(text) - 1)
            if "\u4e00" <= text[i] <= "\u9fff" and "\u4e00" <= text[i + 1] <= "\u9fff"
        ]
        profile.total_words = len(words)
        profile.unique_words = len(set(words))
        profile.ttr = profile.unique_words / max(profile.total_words, 1)

        # 高频词Top20
        word_counts = Counter(words)
        profile.top_words = dict(word_counts.most_common(20))

        # 3. 对话统计
        dialogue_matches = re.findall(r'[""「]([^""」]+)[""」]', text)
        if dialogue_matches:
            profile.dialogue_ratio = sum(len(d) for d in dialogue_matches) / max(len(text), 1)
            profile.dialogue_avg_length = sum(len(d) for d in dialogue_matches) / len(
                dialogue_matches
            )

        # 4. 段落统计
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
        if paragraphs:
            para_lengths = [len(p) for p in paragraphs]
            profile.avg_paragraph_length = sum(para_lengths) / len(para_lengths)
            if len(para_lengths) > 1:
                mean = profile.avg_paragraph_length
                variance = sum((v - mean) ** 2 for v in para_lengths) / (len(para_lengths) - 1)
                profile.std_paragraph_length = math.sqrt(variance)

        # 5. 修辞统计
        profile.metaphor_count = sum(text.count(m) for m in self.METAPHOR_MARKERS)
        for pat in self.PARALLELISM_PATTERNS:
            profile.parallelism_count += len(re.findall(pat, text))
        for pat in self.PERSONIFICATION_PATTERNS:
            profile.personification_count += len(re.findall(pat, text))

        return profile

    def compare_with_baseline(
        self,
        current: StyleProfile,
        baseline_profiles: list[StyleProfile],
    ) -> DriftReport:
        """
        将当前章节与基线对比，检测文风漂移

        Args:
            current: 当前章节的文风档案
            baseline_profiles: 前N章（作为基线）的文风档案列表

        Returns:
            DriftReport: 漂移检测报告
        """
        if not baseline_profiles:
            return DriftReport(
                book_id="",
                chapters_analyzed=1,
                profiles=[current],
                overall_stability=1.0,
            )

        # 计算基线均值
        n = len(baseline_profiles)
        baseline = StyleProfile(chapter=0)
        baseline.avg_sentence_length = sum(p.avg_sentence_length for p in baseline_profiles) / n
        baseline.std_sentence_length = sum(p.std_sentence_length for p in baseline_profiles) / n
        baseline.cv_sentence_length = sum(p.cv_sentence_length for p in baseline_profiles) / n
        baseline.ttr = sum(p.ttr for p in baseline_profiles) / n
        baseline.dialogue_ratio = sum(p.dialogue_ratio for p in baseline_profiles) / n
        baseline.dialogue_avg_length = sum(p.dialogue_avg_length for p in baseline_profiles) / n
        baseline.avg_paragraph_length = sum(p.avg_paragraph_length for p in baseline_profiles) / n
        baseline.metaphor_count = sum(p.metaphor_count for p in baseline_profiles) / n
        baseline.parallelism_count = sum(p.parallelism_count for p in baseline_profiles) / n
        baseline.personification_count = sum(p.personification_count for p in baseline_profiles) / n

        alerts: list[DriftAlert] = []
        stability_scores: list[float] = []

        # 1. 句长漂移检测
        if baseline.avg_sentence_length > 0:
            drift = (
                abs(current.avg_sentence_length - baseline.avg_sentence_length)
                / baseline.avg_sentence_length
            )
            stability_scores.append(max(0, 1 - drift))
            if drift > self.SENTENCE_LENGTH_DRIFT_THRESHOLD:
                severity = "critical" if drift > 0.6 else "warning"
                alerts.append(
                    DriftAlert(
                        chapter=current.chapter,
                        dimension="句长分布",
                        current_value=current.avg_sentence_length,
                        baseline_value=baseline.avg_sentence_length,
                        deviation=drift,
                        severity=severity,
                        suggestion=f"句长从基线{baseline.avg_sentence_length:.0f}字偏离到{current.avg_sentence_length:.0f}字"
                        f"（{drift:.0%}），建议检查是否模型切换或Prompt变更导致",
                    )
                )

        # 2. TTR（词汇多样性）漂移
        if baseline.ttr > 0:
            drift = abs(current.ttr - baseline.ttr) / baseline.ttr
            stability_scores.append(max(0, 1 - drift))
            if drift > self.TTR_DRIFT_THRESHOLD:
                severity = "critical" if drift > 0.5 else "warning"
                alerts.append(
                    DriftAlert(
                        chapter=current.chapter,
                        dimension="词汇多样性(TTR)",
                        current_value=current.ttr,
                        baseline_value=baseline.ttr,
                        deviation=drift,
                        severity=severity,
                        suggestion=(
                            f"词汇多样性从{baseline.ttr:.2f}变化到{current.ttr:.2f}"
                            f"（{drift:.0%}），"
                            f"{'词汇变得重复' if current.ttr < baseline.ttr else '词汇变得分散'}"
                        ),
                    )
                )

        # 3. 对话比例漂移
        if baseline.dialogue_ratio > 0:
            drift = abs(current.dialogue_ratio - baseline.dialogue_ratio) / max(
                baseline.dialogue_ratio, 0.01
            )
            stability_scores.append(max(0, 1 - drift))
            if drift > self.DIALOGUE_RATIO_DRIFT_THRESHOLD:
                severity = "critical" if drift > 0.8 else "warning"
                alerts.append(
                    DriftAlert(
                        chapter=current.chapter,
                        dimension="对话比例",
                        current_value=current.dialogue_ratio,
                        baseline_value=baseline.dialogue_ratio,
                        deviation=drift,
                        severity=severity,
                        suggestion=(
                            f"对话比例从{baseline.dialogue_ratio:.0%}"
                            f"变化到{current.dialogue_ratio:.0%}"
                            f"（{drift:.0%}），"
                            + (
                                "对话过多可能拖慢节奏"
                                if current.dialogue_ratio > baseline.dialogue_ratio
                                else "叙述过多可能缺乏互动"
                            )
                        ),
                    )
                )

        # 4. 段落长度漂移
        if baseline.avg_paragraph_length > 0:
            drift = (
                abs(current.avg_paragraph_length - baseline.avg_paragraph_length)
                / baseline.avg_paragraph_length
            )
            stability_scores.append(max(0, 1 - drift))
            if drift > self.PARAGRAPH_LENGTH_DRIFT_THRESHOLD:
                alerts.append(
                    DriftAlert(
                        chapter=current.chapter,
                        dimension="段落结构",
                        current_value=current.avg_paragraph_length,
                        baseline_value=baseline.avg_paragraph_length,
                        deviation=drift,
                        severity="warning",
                        suggestion=f"段落长度从基线{baseline.avg_paragraph_length:.0f}字偏离到{current.avg_paragraph_length:.0f}字",
                    )
                )

        # 5. 修辞密度漂移
        baseline_rhetoric = (
            baseline.metaphor_count + baseline.parallelism_count + baseline.personification_count
        )
        current_rhetoric = (
            current.metaphor_count + current.parallelism_count + current.personification_count
        )
        if baseline_rhetoric > 0:
            drift = abs(current_rhetoric - baseline_rhetoric) / baseline_rhetoric
            stability_scores.append(max(0, 1 - drift))
            if drift > self.RHETORIC_DENSITY_DRIFT_THRESHOLD:
                alerts.append(
                    DriftAlert(
                        chapter=current.chapter,
                        dimension="修辞密度",
                        current_value=current_rhetoric,
                        baseline_value=baseline_rhetoric,
                        deviation=drift,
                        severity="warning",
                        suggestion=f"修辞手法使用频率变化{drift:.0%}，可能影响文风一致性",
                    )
                )

        # 计算整体稳定性
        overall_stability = (
            sum(stability_scores) / max(len(stability_scores), 1) if stability_scores else 1.0
        )

        # 判断趋势方向
        trend = "stable"
        critical_count = sum(1 for a in alerts if a.severity == "critical")
        warning_count = sum(1 for a in alerts if a.severity == "warning")
        if critical_count >= 2:
            trend = "diverging"
        elif critical_count >= 1 or warning_count >= 3:
            trend = "drifting"

        return DriftReport(
            book_id="",
            chapters_analyzed=n + 1,
            profiles=[*baseline_profiles, current],
            alerts=alerts,
            overall_stability=round(overall_stability, 3),
            trend_direction=trend,
        )

    def get_trend_summary(self, report: DriftReport) -> str:
        """生成趋势摘要文本"""
        if report.trend_direction == "stable":
            return (
                f"文风稳定（稳定性{report.overall_stability:.2f}），{len(report.alerts)}个轻微告警"
            )

        critical = [a for a in report.alerts if a.severity == "critical"]
        if report.trend_direction == "diverging":
            dims = ", ".join(a.dimension for a in critical[:3])
            return (
                f"⚠ 文风严重偏移（稳定性{report.overall_stability:.2f}），"
                f"{len(critical)}个维度严重偏离: {dims}"
            )

        warnings = [a for a in report.alerts if a.severity == "warning"]
        return f"文风轻微漂移（稳定性{report.overall_stability:.2f}），{len(warnings)}个维度需关注"


# 全局单例
style_drift_detector = StyleDriftDetector()
