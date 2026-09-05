"""
昆仑创作引擎 — AI文本人性化主引擎

整合四大模块：
  1. TextFingerprint — 统计指纹分析（perplexity/burstiness/句子CV）
  2. AIModeDetector — AI写作模式检测（29+24种模式）
  3. 多策略重写 — 翻译链 / 多轮LLM / 反馈闭环 / 规则后处理
  4. 管线集成 — 嵌入 GachaEngine 生成后 + StyleEngineer 润色链路

网文场景适配：
  - 黄金三章：最高降AI率需求（aggressive策略）
  - 打斗章节：保持动作节奏，减少成语堆砌
  - 日常章节：口语化对话，自然叙事
  - 高潮章节：情绪张力优先，适度降AI

使用方式:
    from kunlun.humanize import humanize_engine

    # 基础使用
    result = await humanize_engine.humanize(text, strategy="standard")

    # 集成到生成管线
    result = await humanize_engine.humanize(
        text, strategy="aggressive", chapter_type="opening"
    )

    # 仅检测
    report = humanize_engine.detect(text)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from loguru import logger

from kunlun.humanize.detector import (
    DetectionReport,
    ai_mode_detector,
)
from kunlun.humanize.fingerprint import (
    FingerprintResult,
    text_fingerprint,
)
from kunlun.humanize.rewriter import (
    RewriteResult,
    TranslationChain,
    feedback_loop,
    multi_pass_rewriter,
    rule_post_processor,
    translation_chain,
)


class HumanizationStrategy(Enum):
    """人性化策略"""

    NONE = "none"  # 不做处理
    MINIMAL = "minimal"  # 最小处理（规则后处理）
    STANDARD = "standard"  # 标准处理（翻译链 + 规则）
    AGGRESSIVE = "aggressive"  # 激进处理（反馈闭环 + 多轮LLM）
    OPENING = "opening"  # 开头章节专用（最强处理）


@dataclass
class HumanizeResult:
    """人性化处理结果"""

    original: str = ""
    humanized: str = ""
    strategy: str = ""

    # 统计指纹
    fingerprint_before: dict = field(default_factory=dict)
    fingerprint_after: dict = field(default_factory=dict)

    # AI模式检测
    markers_before: int = 0
    markers_after: int = 0
    detection_report: dict = field(default_factory=dict)

    # 降AI效果
    ai_score_before: float = 0.0
    ai_score_after: float = 0.0
    reduction_pct: float = 0.0  # AI得分降低百分比

    # 处理详情
    passes: int = 0
    changes_summary: str = ""
    warnings: list[str] = field(default_factory=list)

    # 网文特化
    chapter_type: str = ""
    is_opening: bool = False


class AntiAIDetector:
    """
    反AI检测器 — 快速检测文本的AI痕迹

    可在生成后立即调用，判断是否需要人性化处理。
    """

    def __init__(self):
        self._fingerprint = text_fingerprint
        self._detector = ai_mode_detector

    def detect(self, text: str) -> dict:
        """快速检测"""
        fp = self._fingerprint.analyze(text)
        det = self._detector.detect(text)

        return {
            "ai_likelihood": round(fp.ai_likelihood, 3),
            "risk_level": fp.risk_level,
            "fingerprint": {
                "perplexity": round(fp.perplexity_score, 2),
                "burstiness": round(fp.burstiness, 3),
                "sentence_cv": round(fp.sentence_length_cv, 3),
            },
            "markers": {
                "total": det.total_markers,
                "unique_patterns": det.unique_patterns,
                "summary": det.summary,
            },
            "needs_humanization": fp.ai_likelihood > 0.4,
            "recommended_strategy": self._recommend_strategy(fp, det),
        }

    def _recommend_strategy(self, fp: FingerprintResult, _det: DetectionReport) -> str:
        """推荐处理策略"""
        score = fp.ai_likelihood
        if score > 0.7:
            return "aggressive"
        if score > 0.5:
            return "standard"
        if score > 0.35:
            return "minimal"
        return "none"


class HumanizeEngine:
    """
    AI文本人性化主引擎

    架构设计：
    ┌─────────────┐
    │ 输入文本     │
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │ 统计指纹分析 │ ← TextFingerprint
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │ AI模式检测   │ ← AIModeDetector
    └──────┬──────┘
           ▼
    ┌─────────────────────────────┐
    │ 策略选择                     │
    │  ├─ minimal: 规则后处理      │
    │  ├─ standard: 翻译链+规则    │
    │  ├─ aggressive: 反馈闭环     │
    │  └─ opening: 多轮+翻译链     │
    └──────┬──────────────────────┘
           ▼
    ┌─────────────┐
    │ 效果验证     │ ← 再次检测对比
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │ 输出结果     │
    └─────────────┘

    集成点:
    - GachaEngine.generate() 之后: humanize_engine.humanize(result["best_text"])
    - StyleEngineer.execute() 之后: humanize_engine.humanize(polished_draft)
    - API 端点: POST /humanize
    - 守护进程: 每个章节生成后自动调用
    """

    def __init__(self):
        self._fingerprint = text_fingerprint
        self._detector = ai_mode_detector
        self._translation_chain = translation_chain
        self._multi_pass = multi_pass_rewriter
        self._feedback_loop = feedback_loop
        self._rule_processor = rule_post_processor
        self._anti_detector = AntiAIDetector()

    def detect(self, text: str) -> dict:
        """快速检测AI痕迹"""
        return self._anti_detector.detect(text)

    async def humanize(
        self,
        text: str,
        strategy: str = "standard",
        chapter_type: str = "normal",
        llm_caller=None,
        auto_strategy: bool = False,
    ) -> HumanizeResult:
        """
        执行人性化处理

        Args:
            text: 原始文本
            strategy: 策略名称 (minimal/standard/aggressive/opening/none)
            chapter_type: 章节类型 (normal/opening/climax/daily/fight)
            llm_caller: 可选的LLM调用函数 async fn(prompt, system_prompt) -> str
            auto_strategy: 是否自动选择策略（基于检测结果）

        Returns:
            HumanizeResult
        """
        if not text or len(text) < 50:
            return HumanizeResult(original=text, humanized=text, strategy="none")

        # 自动策略选择
        if auto_strategy:
            detection = self._anti_detector.detect(text)
            strategy = detection.get("recommended_strategy", "standard")
            logger.info(f"HumanizeEngine: 自动选择策略 → {strategy}")

        # 前置检测
        before_fp = self._fingerprint.analyze(text)
        before_det = self._detector.detect(text)

        # 执行策略
        rewrite_result = await self._execute_strategy(text, strategy, chapter_type, llm_caller)

        # 后置检测
        after_fp = self._fingerprint.analyze(rewrite_result.rewritten)
        after_det = self._detector.detect(rewrite_result.rewritten)

        # 如果效果不佳，追加规则后处理
        humanized = rewrite_result.rewritten
        if after_fp.ai_likelihood > 0.4 and strategy != "none":
            logger.info("HumanizeEngine: 效果未达标，追加规则后处理")
            humanized = self._rule_processor.process(humanized, after_det)
            after_fp = self._fingerprint.analyze(humanized)
            after_det = self._detector.detect(humanized)

        # 构建结果
        reduction = 0.0
        if before_fp.ai_likelihood > 0:
            reduction = (
                (before_fp.ai_likelihood - after_fp.ai_likelihood) / before_fp.ai_likelihood * 100
            )

        warnings = []
        if after_fp.ai_likelihood > 0.5:
            warnings.append(
                f"处理后AI得分仍较高({after_fp.ai_likelihood:.2f})，建议使用更激进的策略"
            )
        if len(humanized) < len(text) * 0.7:
            warnings.append("处理后文本长度显著缩短，可能丢失内容")

        return HumanizeResult(
            original=text,
            humanized=humanized,
            strategy=strategy,
            fingerprint_before={
                "perplexity": round(before_fp.perplexity_score, 2),
                "burstiness": round(before_fp.burstiness, 3),
                "sentence_cv": round(before_fp.sentence_length_cv, 3),
                "ai_likelihood": round(before_fp.ai_likelihood, 3),
                "risk_level": before_fp.risk_level,
            },
            fingerprint_after={
                "perplexity": round(after_fp.perplexity_score, 2),
                "burstiness": round(after_fp.burstiness, 3),
                "sentence_cv": round(after_fp.sentence_length_cv, 3),
                "ai_likelihood": round(after_fp.ai_likelihood, 3),
                "risk_level": after_fp.risk_level,
            },
            markers_before=before_det.total_markers,
            markers_after=after_det.total_markers,
            detection_report={
                "before": before_det.summary,
                "after": after_det.summary,
            },
            ai_score_before=before_fp.ai_likelihood,
            ai_score_after=after_fp.ai_likelihood,
            reduction_pct=round(reduction, 1),
            passes=rewrite_result.passes,
            changes_summary=rewrite_result.changes_summary,
            warnings=warnings,
            chapter_type=chapter_type,
            is_opening=(chapter_type == "opening"),
        )

    async def _execute_strategy(
        self,
        text: str,
        strategy: str,
        chapter_type: str,
        llm_caller=None,
    ) -> RewriteResult:
        """执行具体策略"""
        if strategy == "none":
            return RewriteResult(
                original=text,
                rewritten=text,
                strategy="none",
                fingerprint_before={},
                fingerprint_after={},
            )

        if strategy == "minimal":
            # 仅规则后处理
            processed = self._rule_processor.process(text)
            return RewriteResult(
                original=text,
                rewritten=processed,
                strategy="minimal",
                passes=1,
            )

        if strategy == "standard":
            # 翻译链（标准3跳）+ 规则后处理
            chain = TranslationChain("standard")
            chain_result = await chain.rewrite(text, llm_caller)
            processed = self._rule_processor.process(chain_result.rewritten)
            return RewriteResult(
                original=text,
                rewritten=processed,
                strategy="standard",
                passes=1,
                fingerprint_before=chain_result.fingerprint_before,
                fingerprint_after=chain_result.fingerprint_after,
                markers_before=chain_result.markers_before,
                markers_after=chain_result.markers_after,
            )

        if strategy == "aggressive":
            # 反馈闭环（检测→重写→再检测）
            loop_result = await self._feedback_loop.rewrite(text, llm_caller)
            processed = self._rule_processor.process(loop_result.rewritten)
            return RewriteResult(
                original=text,
                rewritten=processed,
                strategy="aggressive",
                passes=loop_result.passes,
                fingerprint_before=loop_result.fingerprint_before,
                fingerprint_after=loop_result.fingerprint_after,
                markers_before=loop_result.markers_before,
                markers_after=loop_result.markers_after,
            )

        if strategy == "opening":
            # 开头章节专用：翻译链（激进4跳）+ 多轮重写
            chain = TranslationChain("aggressive")
            chain_result = await chain.rewrite(text, llm_caller)

            pass_result = await self._multi_pass.rewrite(
                chain_result.rewritten,
                passes=2,
                llm_caller=llm_caller,
                chapter_type="opening",
            )

            processed = self._rule_processor.process(pass_result.rewritten)
            return RewriteResult(
                original=text,
                rewritten=processed,
                strategy="opening",
                passes=1 + pass_result.passes,
                fingerprint_before=chain_result.fingerprint_before,
                fingerprint_after=pass_result.fingerprint_after,
                markers_before=chain_result.markers_before,
                markers_after=pass_result.markers_after,
            )

        logger.warning(f"HumanizeEngine: 未知策略 {strategy}，使用 standard")
        return await self._execute_strategy(text, "standard", chapter_type, llm_caller)

    def quick_process(self, text: str) -> str:
        """
        快速处理（同步，零LLM成本）

        适合不需要LLM重写的场景，仅做规则后处理。
        """
        return self._rule_processor.process(text)

    def compare(self, original: str, humanized: str) -> dict:
        """对比处理前后效果"""
        return self._fingerprint.compare(original, humanized)


# 全局单例
humanize_engine = HumanizeEngine()
anti_ai_detector = AntiAIDetector()
