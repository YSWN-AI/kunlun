"""
昆仑创作引擎 — AI率检测与人类化改写模块

提供中文男频网文的AI率检测、人类化改写和AI率门禁功能。

Usage:
    from kunlun.ai_rate import detect_ai_rate, humanize_text, ai_gate_check
    from kunlun.ai_rate import AIRateDetector, HumanizeEngine, AIGateKeeper

    # 检测AI率
    report = detect_ai_rate(text)
    print(report.summary())

    # 人类化改写
    result = humanize_text(text, aggressive=0.7)
    print(f"AI率: {result.ai_rate_before:.1f} -> {result.ai_rate_after:.1f}")

    # AI率门禁（自动改写）
    gate_result = ai_gate_check(text, threshold=35, auto_humanize=True)
"""

from kunlun.ai_rate.engine import (
    AI_HIGH_RISK_WORDS,
    AI_MEDIUM_RISK_WORDS,
    HIGH_RISK_REPLACEMENTS,
    HUMAN_STYLE_PHRASES,
    AIFeatureDimension,
    AIGateKeeper,
    AIRateDetector,
    AIRateReport,
    DimensionResult,
    HumanizeEngine,
    HumanizeResult,
    HumanizeStrategy,
    ai_gate_check,
    detect_ai_rate,
    humanize_text,
)

__all__ = [
    "AI_HIGH_RISK_WORDS",
    "AI_MEDIUM_RISK_WORDS",
    "HIGH_RISK_REPLACEMENTS",
    "HUMAN_STYLE_PHRASES",
    "AIFeatureDimension",
    "AIGateKeeper",
    "AIRateDetector",
    "AIRateReport",
    "DimensionResult",
    "HumanizeEngine",
    "HumanizeResult",
    "HumanizeStrategy",
    "ai_gate_check",
    "detect_ai_rate",
    "humanize_text",
]
