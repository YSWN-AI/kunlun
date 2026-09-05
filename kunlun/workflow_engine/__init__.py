"""
昆仑创作引擎 — 工作流可视化编辑器

提供可拖拽的节点式工作流编排，支持 LLM 调用、文本处理、质量检查、
条件分支、人工审核等节点类型，内置章节生成、爆款仿写、降AI 等预设模板。
"""

from __future__ import annotations

from kunlun.workflow_engine.models import (
    WorkflowDefinition,
    WorkflowEdge,
    WorkflowExecution,
    WorkflowNode,
)
from kunlun.workflow_engine.presets import get_presets, list_presets
from kunlun.workflow_engine.service import WorkflowService

__all__ = [
    "WorkflowDefinition",
    "WorkflowEdge",
    "WorkflowExecution",
    "WorkflowNode",
    "WorkflowService",
    "get_presets",
    "list_presets",
]
