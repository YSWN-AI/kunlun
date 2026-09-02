"""
昆仑创作引擎 — 确定性连续性引擎 (Deterministic Continuity Engine)

灵感来源: Novel-OS 确定性连续性引擎 + InkOS 状态不可变快照
对标: 网文连载中角色/事件/设定/时间线的连续性保障
"""

from kunlun.continuity.engine import (
    ContinuityChecker,
    ContinuityEngine,
    ContinuityReport,
    ContinuitySeverity,
    ContinuitySnapshot,
    ContinuityViolation,
    SnapshotManager,
    get_continuity_engine,
)

__all__ = [
    "ContinuityChecker",
    "ContinuityEngine",
    "ContinuityReport",
    "ContinuitySeverity",
    "ContinuitySnapshot",
    "ContinuityViolation",
    "SnapshotManager",
    "get_continuity_engine",
]
