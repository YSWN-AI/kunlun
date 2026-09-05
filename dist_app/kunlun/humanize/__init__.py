"""
昆仑创作引擎 — AI文本人性化（降AI率）模块

核心理念：基于业界顶级开源项目（blader/humanizer、Humanizer-zh、humanize-text）
进行深度重构与无缝嵌入，专为网文创作场景适配。

三层架构：
  1. 统计指纹层 (fingerprint/)  — 计算/优化 perplexity、burstiness、句子方差
  2. 模式检测层 (detector/)      — 29种AI写作模式检测 + 24种中文特化
  3. 重写引擎层 (rewriter/)      — 翻译链/多轮LLM/检测反馈/规则后处理

引用开源项目：
  - blader/humanizer (16.8k⭐): 29种AI写作模式定义
  - op7418/Humanizer-zh (2.4k⭐): 24种中文特化模式
  - lynote-ai/humanize-text: 4种人性化方法论（翻译链、多轮重写、反馈循环、混合引擎）

用法：
    from kunlun.humanize import humanize_engine
    result = await humanize_engine.humanize(text, strategy="aggressive")
"""

from __future__ import annotations

from kunlun.humanize.detector import (
    AIMarker,
    AIModeCategory,
    AIModeDetector,
    DetectionReport,
)
from kunlun.humanize.engine import (
    AntiAIDetector,
    HumanizationStrategy,
    HumanizeEngine,
    HumanizeResult,
    anti_ai_detector,
    humanize_engine,
)
from kunlun.humanize.fingerprint import (
    BurstinessProfile,
    FingerprintResult,
    TextFingerprint,
)
from kunlun.humanize.rewriter import (
    FeedbackLoop,
    MultiPassRewriter,
    RewriteResult,
    RulePostProcessor,
    TranslationChain,
)

__all__ = [
    "AIMarker",
    "AIModeCategory",
    # 模式检测
    "AIModeDetector",
    "AntiAIDetector",
    "BurstinessProfile",
    "DetectionReport",
    "FeedbackLoop",
    "FingerprintResult",
    "HumanizationStrategy",
    # 引擎
    "HumanizeEngine",
    "HumanizeResult",
    "MultiPassRewriter",
    "RewriteResult",
    "RulePostProcessor",
    # 统计指纹
    "TextFingerprint",
    # 重写引擎
    "TranslationChain",
    "anti_ai_detector",
    "humanize_engine",
]
