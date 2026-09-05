"""
管线步骤实现 — 基于 BaseStep 的具体步骤类

每个步骤类封装一个管线段落，从 Makefile._step_* 方法迁移而来。
共 20 个步骤，按管线执行顺序排列。
"""

from __future__ import annotations

from kunlun.pipeline.steps.audit import AuditStep
from kunlun.pipeline.steps.blueprint import BlueprintStep
from kunlun.pipeline.steps.draft import DraftStep
from kunlun.pipeline.steps.icu import ICUStep
from kunlun.pipeline.steps.intel_sync import IntelSyncStep
from kunlun.pipeline.steps.kg_update import KGUpdateStep
from kunlun.pipeline.steps.learner_record import LearnerRecordStep
from kunlun.pipeline.steps.observer import ObserverStep
from kunlun.pipeline.steps.polish import PolishStep
from kunlun.pipeline.steps.post_reflect import PostReflectStep
from kunlun.pipeline.steps.post_write_validate import PostWriteValidateStep
from kunlun.pipeline.steps.publish import PublishStep
from kunlun.pipeline.steps.quality_check import QualityCheckStep
from kunlun.pipeline.steps.reflector import ReflectorStep
from kunlun.pipeline.steps.revise_loop import ReviseLoopStep
from kunlun.pipeline.steps.snapshot import SnapshotStep
from kunlun.pipeline.steps.society_rag import SocietyRAGStep
from kunlun.pipeline.steps.state_update import StateUpdateStep
from kunlun.pipeline.steps.style_drift import StyleDriftStep
from kunlun.pipeline.steps.truth_and_fingerprint import TruthAndFingerprintStep

__all__ = [
    "AuditStep",
    "BlueprintStep",
    "DraftStep",
    "ICUStep",
    "IntelSyncStep",
    "KGUpdateStep",
    "LearnerRecordStep",
    "ObserverStep",
    "PolishStep",
    "PostReflectStep",
    "PostWriteValidateStep",
    "PublishStep",
    "QualityCheckStep",
    "ReflectorStep",
    "ReviseLoopStep",
    "SnapshotStep",
    "SocietyRAGStep",
    "StateUpdateStep",
    "StyleDriftStep",
    "TruthAndFingerprintStep",
]
