"""
门禁基础类型

GateLevel / GateResult / AuditResult — 所有门禁模块共享。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GateLevel(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class GateResult:
    gate_id: str
    level: GateLevel
    score: float  # 0.0~1.0
    detail: str
    data: dict | None = None


@dataclass
class AuditResult:
    passed: bool  # 所有门禁 PASS/WARN
    gates: dict[str, GateResult]
    score: float  # 加权总分
    summary: str
