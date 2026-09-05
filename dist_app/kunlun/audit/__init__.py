"""
审计门禁模块

Phase 3: 独立审计门禁，可供 Auditor Agent 或其他模块直接调用。

两套审计系统:
  1. 8门禁 (gates.py) — 轻量级快速检查,零LLM调用
  2. 33维审计 (audit33.py) — 全面连续性检查,对照7个真相文件

使用:
    from kunlun.audit import audit_gates, AuditResult
    from kunlun.audit import auditor33, Audit33Report

    # 快速8门禁
    result = audit_gates(draft="...", blueprint={}, kg_snapshot_id="...")
    if result.passed:
        print("通过")

    # 完整33维审计
    report = auditor33.run_audit(draft="...", chapter=1, blueprint={}, book_id="my_book")
    if report.passed:
        print(f"33维审计通过,AI痕迹评分{report.ai_detection_score:.1f}")
"""

from __future__ import annotations

from kunlun.audit.audit33 import (
    Audit33Report,
    Auditor33,
    DimResult,
    auditor33,
)
from kunlun.audit.gates import (
    GATE_WEIGHTS,
    AuditResult,
    GateG1Arc,
    GateG2InfoRelease,
    GateG3AIDetection,
    GateG4PleasureGap,
    GateG5PleasureDiversity,
    GateG6EmotionConsistency,
    GateG7DialogueEffectiveness,
    GateG8BattleRhythm,
    GateLevel,
    GateResult,
    audit_gates,
)

__all__ = [
    "GATE_WEIGHTS",
    "Audit33Report",
    "AuditResult",
    "Auditor33",
    "DimResult",
    "GateG1Arc",
    "GateG2InfoRelease",
    "GateG3AIDetection",
    "GateG4PleasureGap",
    "GateG5PleasureDiversity",
    "GateG6EmotionConsistency",
    "GateG7DialogueEffectiveness",
    "GateG8BattleRhythm",
    "GateLevel",
    "GateResult",
    "audit_gates",
    "auditor33",
]
