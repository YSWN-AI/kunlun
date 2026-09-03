"""
昆仑创作引擎 — debate_review 兼容层

从新 agents 模块 re-export Agent 类，保持 debate_review 包的内聚性。
使用模块级 __getattr__ 实现延迟导入，避免循环依赖。

使旧代码可以通过 `from kunlun.debate_review.agents import CriticAgent` 等方式导入，
也可以通过 `from kunlun.debate_review import CriticAgent` 导入。
"""

from __future__ import annotations

from typing import Any

# 延迟导入映射：名称 → 模块路径
_LAZY_EXPORTS: dict[str, str] = {
    # CriticAgent
    "CRITIC_DIMENSIONS": "kunlun.agents.critic",
    "CriticAgent": "kunlun.agents.critic",
    "CriticReport": "kunlun.agents.critic",
    # ReaderAgent
    "EnhancedReaderFeedback": "kunlun.agents.reader",
    "ExtendedReaderType": "kunlun.agents.reader",
    "EXTENDED_READER_PROFILES": "kunlun.agents.reader",
    "ReaderAgent": "kunlun.agents.reader",
    # DebateOrchestrator
    "CRITICVerification": "kunlun.agents.debate_orchestrator",
    "DebateOrchestrator": "kunlun.agents.debate_orchestrator",
    "DebateResult": "kunlun.agents.debate_orchestrator",
    "DebateRoundDetail": "kunlun.agents.debate_orchestrator",
    "PipelineResult": "kunlun.agents.debate_orchestrator",
    "PipelineStage": "kunlun.agents.debate_orchestrator",
    "ReflexionEntry": "kunlun.agents.debate_orchestrator",
}

__all__ = list(_LAZY_EXPORTS.keys())


def __getattr__(name: str) -> Any:
    """模块级延迟导入，避免循环依赖"""
    if name in _LAZY_EXPORTS:
        import importlib

        module = importlib.import_module(_LAZY_EXPORTS[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
