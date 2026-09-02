"""
昆仑创作引擎 — 核心基类与抽象层

提供 BaseExtensionModule 等基础架构组件，
为 21+ 扩展模块提供统一的生命周期管理。
"""

from kunlun.core.agent_interface import (
    AgentCapability,
    AgentProtocol,
    ErrorClassifier,
    ErrorDecision,
    ErrorSeverity,
    PipelineContext,
    PipelineResult,
    PipelineStepDef,
    StepResult,
    StepStatus,
)
from kunlun.core.extension_base import BaseExtensionModule

__all__ = [
    "AgentCapability",
    "AgentProtocol",
    "BaseExtensionModule",
    "ErrorClassifier",
    "ErrorDecision",
    "ErrorSeverity",
    "PipelineContext",
    "PipelineResult",
    "PipelineStepDef",
    "StepResult",
    "StepStatus",
]
