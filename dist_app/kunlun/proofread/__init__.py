"""
昆仑创作引擎 — 文本审校引擎 (Proofread Engine)

深度融合 pycorrector (5.6k⭐) + ai-proofread + Vale 的设计理念，
为网文创作场景提供多层级文本审校能力。

用法：
    from kunlun.proofread import proofread_engine
    report = proofread_engine.proofread(text, level="standard")
"""

from kunlun.proofread.engine import (
    ConfusionPair,
    DiffHunk,
    DiffReporter,
    DiffResult,
    IssueCategory,
    IssueSeverity,
    LogicChecker,
    LogicIssue,
    ProofreadEngine,
    ProofreadIssue,
    ProofreadLevel,
    ProofreadReport,
    PunctuationChecker,
    PunctuationIssue,
    StyleIssue,
    StyleRule,
    TypoDetector,
    TypoIssue,
    WebnovelStyleLinter,
    proofread_engine,
)

__all__ = [
    "ConfusionPair",
    "DiffHunk",
    "DiffReporter",
    "DiffResult",
    "IssueCategory",
    "IssueSeverity",
    "LogicChecker",
    "LogicIssue",
    "ProofreadEngine",
    "ProofreadIssue",
    "ProofreadLevel",
    "ProofreadReport",
    "PunctuationChecker",
    "PunctuationIssue",
    "StyleIssue",
    "StyleRule",
    "TypoDetector",
    "TypoIssue",
    "WebnovelStyleLinter",
    "proofread_engine",
]
