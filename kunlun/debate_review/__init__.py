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
"""

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
]
