"""
昆仑创作引擎 — Agent辩论式审校与模拟读者反馈模块

提供辩论式质量审校、多类型读者模拟和综合质量评估。

Usage:
    from kunlun.debate_review import (
        debate_review, simulate_readers, full_quality_assessment,
        DebateReviewEngine, ReaderSimulator, QualityAssessmentEngine,
    )

    # 辩论式审校
    result = debate_review(text, chapter=1, target_score=85)
    print(result.summary)
    print(f"评分: {result.total_score}/100")
    for issue in result.issues:
        print(f"  [{issue.dimension.value}] {issue.description}")

    # 模拟读者反馈
    reader_result = simulate_readers(text, chapter=1)
    print(reader_result.summary)
    for reader in reader_result.readers:
        print(f"  {reader.reader_name}: {reader.overall_score}/10, 继续阅读={reader.continue_reading}")

    # 综合质量评估
    assessment = full_quality_assessment(text, chapter=1, target_score=85)
    print(assessment["summary"])
    print(f"综合评分: {assessment['combined_score']}/100")
    for rec in assessment["recommendations"]:
        print(f"  优先级{rec['priority']}: {rec['suggestion']} (预估提升+{rec['estimated_improvement']})")

    # 新增 Agent 类（延迟导入，避免循环依赖）
    from kunlun.debate_review import CriticAgent, ReaderAgent, DebateOrchestrator
"""

from __future__ import annotations

from typing import Any

from kunlun.debate_review.engine import (
    DebateReviewEngine,
    DebateReviewResult,
    DebateRound,
    QualityAssessmentEngine,
    ReaderFeedback,
    ReaderSimulationResult,
    ReaderSimulator,
    ReaderType,
    ReviewDimension,
    ReviewIssue,
    RuleBasedQualityChecker,
    debate_review,
    full_quality_assessment,
    simulate_readers,
)

# 新增 Agent 类使用延迟导入（__getattr__），避免循环依赖
# 循环链: kunlun.agents.critic → kunlun.debate_review.engine →
#         kunlun.debate_review.__init__ → kunlun.debate_review.agents →
#         kunlun.agents.critic (部分初始化)
_LAZY_AGENT_EXPORTS: dict[str, str] = {
    "CRITICVerification": "kunlun.agents.debate_orchestrator",
    "CriticAgent": "kunlun.agents.critic",
    "CriticReport": "kunlun.agents.critic",
    "DebateOrchestrator": "kunlun.agents.debate_orchestrator",
    "DebateResult": "kunlun.agents.debate_orchestrator",
    "DebateRoundDetail": "kunlun.agents.debate_orchestrator",
    "EnhancedReaderFeedback": "kunlun.agents.reader",
    "ExtendedReaderType": "kunlun.agents.reader",
    "EXTENDED_READER_PROFILES": "kunlun.agents.reader",
    "PipelineResult": "kunlun.agents.debate_orchestrator",
    "PipelineStage": "kunlun.agents.debate_orchestrator",
    "ReaderAgent": "kunlun.agents.reader",
    "ReflexionEntry": "kunlun.agents.debate_orchestrator",
}

__all__ = [
    "DebateReviewEngine",
    "DebateReviewResult",
    "DebateRound",
    "QualityAssessmentEngine",
    "ReaderFeedback",
    "ReaderSimulationResult",
    "ReaderSimulator",
    "ReaderType",
    "ReviewDimension",
    "ReviewIssue",
    "RuleBasedQualityChecker",
    "debate_review",
    "full_quality_assessment",
    "simulate_readers",
    # 新增 Agent 类（延迟导入）
    "CRITICVerification",
    "CriticAgent",
    "CriticReport",
    "DebateOrchestrator",
    "DebateResult",
    "DebateRoundDetail",
    "EnhancedReaderFeedback",
    "ExtendedReaderType",
    "EXTENDED_READER_PROFILES",
    "PipelineResult",
    "PipelineStage",
    "ReaderAgent",
    "ReflexionEntry",
]


def __getattr__(name: str) -> Any:
    """模块级延迟导入，避免循环依赖"""
    if name in _LAZY_AGENT_EXPORTS:
        import importlib

        module = importlib.import_module(_LAZY_AGENT_EXPORTS[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
