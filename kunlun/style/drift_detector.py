"""
风格漂移检测 — 监控章节间风格一致性

提供 StyleDriftDetector 类，用于:
- 设置目标风格指纹
- 记录每章风格并计算与目标的相似度
- 检测风格漂移（相似度低于阈值时告警）
- 输出各维度差异和改进建议
- 追踪风格漂移趋势

使用方式:
    from kunlun.style.drift_detector import drift_detector

    # 设置目标风格
    drift_detector.set_target(target_fp)

    # 记录章节并检测
    report = drift_detector.check_drift(1, chapter_text)
    if report.drifted:
        print(f"第{report.chapter}章风格漂移: {report.suggestion}")

    # 查看趋势
    trend = drift_detector.get_trend()
"""

from __future__ import annotations

from dataclasses import dataclass, field

from loguru import logger

from kunlun.style.fingerprint import StyleFingerprint, style_analyzer


@dataclass
class DriftReport:
    """风格漂移报告

    Attributes:
        chapter: 章节号
        similarity: 与目标风格的相似度（0-1）
        drifted: 是否发生漂移（相似度低于阈值）
        dimensions: 各维度差异（维度名 -> 差异值）
        suggestion: 改进建议
    """

    chapter: int = 0
    similarity: float = 0.0
    drifted: bool = False
    dimensions: dict[str, float] = field(default_factory=dict)
    suggestion: str = ""


class StyleDriftDetector:
    """风格漂移检测器 — 监控章节间风格一致性

    通过对比每章指纹与目标风格指纹，检测风格漂移并给出改进建议。
    """

    def __init__(self):
        self.target_fingerprint: StyleFingerprint | None = None
        self.chapter_fingerprints: list[tuple[int, StyleFingerprint]] = []
        self.drift_threshold: float = 0.7

    def set_target(self, fp: StyleFingerprint) -> None:
        """设置目标风格指纹

        Args:
            fp: 目标风格指纹
        """
        self.target_fingerprint = fp
        logger.info(f"[StyleDriftDetector] 目标风格已设置: {fp.name}")

    def record_chapter(self, chapter: int, text: str) -> float:
        """记录章节指纹，返回与目标的相似度

        Args:
            chapter: 章节号
            text: 章节文本

        Returns:
            与目标风格的相似度（0-1），无目标时返回0.0
        """
        fp = style_analyzer.analyze(text, name=f"chapter_{chapter}")
        self.chapter_fingerprints.append((chapter, fp))

        if self.target_fingerprint is None:
            logger.warning("[StyleDriftDetector] 未设置目标风格，无法计算相似度")
            return 0.0

        similarity = self._calc_similarity(fp, self.target_fingerprint)
        logger.info(f"[StyleDriftDetector] 第{chapter}章记录完成，相似度: {similarity:.3f}")
        return similarity

    def check_drift(self, chapter: int, text: str) -> DriftReport:
        """检测章节风格漂移

        Args:
            chapter: 章节号
            text: 章节文本

        Returns:
            DriftReport 漂移报告
        """
        fp = style_analyzer.analyze(text, name=f"chapter_{chapter}")

        if self.target_fingerprint is None:
            logger.warning("[StyleDriftDetector] 未设置目标风格，返回空报告")
            return DriftReport(
                chapter=chapter,
                similarity=0.0,
                drifted=False,
                suggestion="未设置目标风格指纹，请先调用set_target()",
            )

        similarity = self._calc_similarity(fp, self.target_fingerprint)
        drifted = similarity < self.drift_threshold
        dimensions = self.get_drift_dimensions(fp)
        suggestion = self._generate_suggestion(similarity, dimensions, drifted)

        report = DriftReport(
            chapter=chapter,
            similarity=round(similarity, 4),
            drifted=drifted,
            dimensions=dimensions,
            suggestion=suggestion,
        )

        if drifted:
            logger.warning(
                f"[StyleDriftDetector] 第{chapter}章风格漂移! "
                f"相似度={similarity:.3f} < 阈值={self.drift_threshold}"
            )
        else:
            logger.info(f"[StyleDriftDetector] 第{chapter}章风格一致，相似度: {similarity:.3f}")

        return report

    def get_trend(self) -> list[dict]:
        """获取风格漂移趋势（各章相似度序列）

        Returns:
            各章相似度列表，每项为 {"chapter": int, "similarity": float, "drifted": bool}
        """
        trend = []
        for chapter, fp in self.chapter_fingerprints:
            if self.target_fingerprint is not None:
                sim = self._calc_similarity(fp, self.target_fingerprint)
            else:
                sim = 0.0
            trend.append(
                {
                    "chapter": chapter,
                    "similarity": round(sim, 4),
                    "drifted": sim < self.drift_threshold,
                }
            )
        return trend

    def get_drift_dimensions(self, chapter_fp: StyleFingerprint) -> dict[str, float]:
        """计算各维度差异（章节指纹 vs 目标指纹）

        Args:
            chapter_fp: 章节风格指纹

        Returns:
            各维度差异字典（维度名 -> 绝对差异），无目标时返回空字典
        """
        if self.target_fingerprint is None:
            return {}

        target = self.target_fingerprint
        dimensions = {
            "句长差异": abs(chapter_fp.avg_sentence_length - target.avg_sentence_length),
            "句长波动差异": abs(chapter_fp.sentence_length_std - target.sentence_length_std),
            "词汇多样性差异": abs(chapter_fp.word_diversity - target.word_diversity),
            "段落节奏差异": abs(chapter_fp.paragraph_length_cv - target.paragraph_length_cv),
            "对话占比差异": abs(chapter_fp.dialogue_ratio - target.dialogue_ratio),
            "短句比例差异": abs(chapter_fp.short_sentence_ratio - target.short_sentence_ratio),
            "长句比例差异": abs(chapter_fp.long_sentence_ratio - target.long_sentence_ratio),
            "生僻词比例差异": abs(chapter_fp.rare_word_ratio - target.rare_word_ratio),
            "比喻密度差异": abs(chapter_fp.metaphor_per_1k - target.metaphor_per_1k),
            "四字格密度差异": abs(chapter_fp.four_character_per_1k - target.four_character_per_1k),
            "动作描写差异": abs(chapter_fp.action_desc_ratio - target.action_desc_ratio),
            "心理描写差异": abs(chapter_fp.psych_desc_ratio - target.psych_desc_ratio),
            "AI味差异": abs(chapter_fp.ai_taste_score - target.ai_taste_score),
        }
        return dimensions

    def _calc_similarity(self, fp1: StyleFingerprint, fp2: StyleFingerprint) -> float:
        """计算两个指纹的相似度

        优先使用 cosine_similarity，若向量为空则回退到 compare()。

        Args:
            fp1: 指纹1
            fp2: 指纹2

        Returns:
            相似度（0-1）
        """
        if fp1.feature_vector and fp2.feature_vector:
            return fp1.cosine_similarity(fp2)
        return style_analyzer.compare(fp1, fp2)

    def _generate_suggestion(
        self, similarity: float, dimensions: dict[str, float], drifted: bool
    ) -> str:
        """根据差异维度生成改进建议

        Args:
            similarity: 相似度
            dimensions: 各维度差异
            drifted: 是否漂移

        Returns:
            建议文本
        """
        if not drifted:
            return f"风格一致（相似度{similarity:.2f}），保持当前写作节奏。"

        # 找出差异最大的3个维度
        sorted_dims = sorted(dimensions.items(), key=lambda x: x[1], reverse=True)
        top_dims = sorted_dims[:3]

        suggestions = [
            f"风格漂移（相似度{similarity:.2f} < 阈值{self.drift_threshold}），主要差异:"
        ]
        for dim_name, diff in top_dims:
            if diff > 0.01:
                suggestions.append(f"  - {dim_name}: 偏差{diff:.2f}，建议向目标风格靠拢")

        suggestions.append("建议: 参考目标风格的to_prompt()约束，调整句式、词汇和描写比例。")
        return "\n".join(suggestions)


# ── 全局单例 ──
drift_detector = StyleDriftDetector()
