"""
昆仑创作引擎 — 7Agent 协作流程模块

对标马良写作的多智能体协作系统，提供 supervisor/structure/blueprint/
generation/setting/consistency/correction 七个 Agent 的串行协作写作流程。

用法:
    from kunlun.agent_pipeline import AgentPipeline, PipelineConfig

    pipeline = AgentPipeline(book_id="test_001")
    result = await pipeline.run_chapter(1, "第一章 觉醒", {})
"""

from __future__ import annotations

from kunlun.agent_pipeline.pipeline import (
    AGENT_DEFINITIONS,
    AgentPipeline,
    PipelineConfig,
    StepResult,
)

__all__ = [
    "AGENT_DEFINITIONS",
    "AgentPipeline",
    "PipelineConfig",
    "StepResult",
]
