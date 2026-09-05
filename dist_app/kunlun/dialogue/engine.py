"""
dialogue 对话引擎 — 网文对话质量评估与角色语音一致性管理

核心能力:
1. 对话质量评分（语体自然度、角色辨识度、推动力、节奏感）
2. 角色语音指纹（SpeakerProfile）— 口头禅、句式偏好、语气特征
3. 多角色对话区分度检测（防止"千面一腔"）
4. 对话密度与分布分析
5. 零LLM纯规则实现（基于中文语言学特征）
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from loguru import logger

from kunlun.core.extension_base import BaseExtensionModule
from kunlun.dialogue.distinctiveness import SpeakerDistinctiveness
from kunlun.dialogue.parser import (
    DialogueLine,
    DialogueMetrics,
    DialogueParser,
    DialogueReport,
    DialogueStyle,
    DistinctivenessLevel,
    SpeakerProfile,
)

# 重新导出，保持向后兼容
__all__ = [
    "DialogueEvaluator",
    "DialogueLine",
    "DialogueMetrics",
    "DialogueParser",
    "DialogueReport",
    "DialogueStyle",
    "DistinctivenessLevel",
    "SpeakerDistinctiveness",
    "SpeakerProfile",
    "get_dialogue_evaluator",
]

# ============================================================================
# 对话评估器（主入口）
# ============================================================================


class DialogueEvaluator(BaseExtensionModule):
    """对话质量评估器 — 评估对话的自然度、角色辨识度、推动力"""

    def __init__(self, book_id: str = ""):
        super().__init__(book_id)
        self._parser = DialogueParser()
        self._distinctiveness = SpeakerDistinctiveness()

    def evaluate_chapter(
        self,
        chapter_text: str,
        chapter_id: str = "",
        known_characters: dict[str, str] | None = None,
    ) -> DialogueReport:
        """评估一章的对话质量

        Args:
            chapter_text: 章节全文
            chapter_id: 章节ID
            known_characters: 已知角色 {id: name}

        Returns:
            DialogueReport: 完整的对话质量报告
        """
        report = DialogueReport(book_id=self.book_id, chapter_id=chapter_id)

        # 1. 提取对话行
        lines = self._parser.extract_with_speakers(chapter_text, known_characters)
        if not lines:
            report.overall_score = 100  # 无对话不算扣分
            report.metrics.distinctiveness = DistinctivenessLevel.HIGH
            return report

        # 2. 基础统计
        metrics = report.metrics
        metrics.total_lines = len(lines)
        metrics.total_words = sum(dl.word_count for dl in lines)
        total_chapter_words = len(chapter_text.replace("\n", "").replace(" ", ""))
        metrics.dialogue_ratio = metrics.total_words / max(total_chapter_words, 1)
        metrics.avg_line_length = metrics.total_words / len(lines)
        metrics.question_ratio = sum(1 for dl in lines if dl.has_question) / len(lines)
        metrics.exclamation_ratio = sum(1 for dl in lines if dl.has_exclamation) / len(lines)
        metrics.longest_monologue = max((dl.word_count for dl in lines), default=0)

        # 3. 按角色分组
        speaker_lines: dict[str, list[DialogueLine]] = defaultdict(list)
        for dl in lines:
            speaker_lines[dl.speaker_id].append(dl)
        metrics.speaker_count = len(speaker_lines)

        # 说话人均衡度（基尼系数反向）
        if speaker_lines:
            counts = sorted(len(v) for v in speaker_lines.values())
            n = len(counts)
            total = sum(counts)
            if total > 0 and n > 1:
                # 简化均衡度：1 - (max-min)/total
                metrics.speaker_balance = 1 - (counts[-1] - counts[0]) / total
            else:
                metrics.speaker_balance = 1.0

        # 4. 构建角色语音指纹
        for sid, s_lines in speaker_lines.items():
            sname = known_characters.get(sid, sid) if known_characters else sid
            report.speaker_profiles[sid] = self._distinctiveness.build_profile(sid, sname, s_lines)

        # 5. 角色辨识度检测
        metrics.distinctiveness = self._distinctiveness.compare_profiles(report.speaker_profiles)
        if metrics.distinctiveness in (DistinctivenessLevel.LOW, DistinctivenessLevel.NONE):
            report.distinctiveness_issues.append(
                f"角色辨识度{metrics.distinctiveness.value}，建议强化各角色语音特征"
            )

        # 6. 风格警告
        report.style_warnings = self._generate_style_warnings(lines, metrics)

        # 7. 综合评分（0-100）
        report.overall_score = self._calculate_score(metrics, report)

        logger.info(report.summary())
        return report

    def _generate_style_warnings(
        self, lines: list[DialogueLine], metrics: DialogueMetrics
    ) -> list[str]:
        """生成对话风格警告"""
        warnings: list[str] = []

        # 对话比例过低
        if metrics.dialogue_ratio < 0.15:
            warnings.append(f"对话占比仅{metrics.dialogue_ratio:.0%}，建议增加对话推动剧情")
        elif metrics.dialogue_ratio > 0.60:
            warnings.append(f"对话占比{metrics.dialogue_ratio:.0%}过高，建议增加叙述和描写")

        # 单句过长
        long_lines = [dl for dl in lines if dl.word_count > 80]
        if long_lines:
            warnings.append(f"有{len(long_lines)}句对话超过80字，建议拆分避免说教感")

        # 问句过多
        if metrics.question_ratio > 0.5:
            warnings.append(f"疑问句占比{metrics.question_ratio:.0%}，可能显得角色缺乏主见")

        # 感叹句过多
        if metrics.exclamation_ratio > 0.4:
            warnings.append(f"感叹句占比{metrics.exclamation_ratio:.0%}，情绪表达可能过于夸张")

        # 对话分配不均
        if metrics.speaker_balance < 0.3 and metrics.speaker_count >= 3:
            warnings.append("对话分配严重不均，某些角色几乎没有台词")

        return warnings

    def _calculate_score(self, metrics: DialogueMetrics, report: DialogueReport) -> float:
        """计算对话质量综合得分"""
        score = 80.0  # 基础分

        # 对话比例适中加分
        if 0.20 <= metrics.dialogue_ratio <= 0.45:
            score += 5
        elif metrics.dialogue_ratio < 0.10 or metrics.dialogue_ratio > 0.65:
            score -= 8

        # 角色辨识度
        distinctiveness_bonus = {
            DistinctivenessLevel.HIGH: 8,
            DistinctivenessLevel.MEDIUM: 2,
            DistinctivenessLevel.LOW: -5,
            DistinctivenessLevel.NONE: -12,
        }
        score += distinctiveness_bonus.get(metrics.distinctiveness, 0)

        # 对话均衡度
        score += metrics.speaker_balance * 5 - 2

        # 警告扣分
        score -= len(report.style_warnings) * 3

        # 平均句长适中
        if 15 <= metrics.avg_line_length <= 50:
            score += 2
        elif metrics.avg_line_length > 80:
            score -= 3

        return max(0, min(100, score))

    def compare_speakers(self, speaker_a: str, speaker_b: str) -> dict[str, Any]:
        """对比两个角色的语音差异"""
        return {
            "speaker_a": speaker_a,
            "speaker_b": speaker_b,
            "message": "请在 evaluate_chapter 后通过 speaker_profiles 进行对比",
        }

    def find_catchphrases(self, _character_id: str) -> list[str]:
        """获取角色的口头禅"""
        return []

    def analyze_style(self, character_id: str) -> dict[str, Any]:
        """分析角色语体风格"""
        return {
            "character_id": character_id,
            "dominant_style": DialogueStyle.NATURAL.value,
        }


# ============================================================================
# 工厂函数
# ============================================================================


_evaluators: dict[str, DialogueEvaluator] = {}


def get_dialogue_evaluator(book_id: str = "") -> DialogueEvaluator:
    """获取对话评估器实例（按book_id缓存）"""
    if book_id not in _evaluators:
        _evaluators[book_id] = DialogueEvaluator(book_id=book_id)
    return _evaluators[book_id]
