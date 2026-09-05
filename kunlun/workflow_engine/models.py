# mypy: ignore-errors
"""
工作流引擎 — Pydantic 数据模型

定义节点、边、工作流定义、执行记录等核心数据结构。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def _now_iso() -> str:
    """返回当前 UTC 时间的 ISO 格式字符串。"""
    return datetime.now(UTC).isoformat()


# ── 节点类型常量 ──────────────────────────────────────────────
NODE_TYPES: list[str] = [
    "llm_call",
    "text_process",
    "quality_check",
    "condition",
    "human_review",
    "input",
    "output",
]

# 各节点类型的配置说明（供前端表单渲染）
NODE_TYPE_CONFIG_SCHEMA: dict[str, dict[str, Any]] = {
    "llm_call": {
        "label": "LLM 调用",
        "description": "调用大语言模型生成文本（模拟执行）",
        "config_fields": {
            "model": {"type": "string", "default": "gpt-4o-mini", "description": "模型名称"},
            "prompt_template": {
                "type": "string",
                "default": "请根据以下内容生成：{{input}}",
                "description": "提示词模板，支持 {{变量名}} 占位符",
            },
            "temperature": {"type": "number", "default": 0.7, "min": 0, "max": 2},
            "max_tokens": {"type": "integer", "default": 2048, "min": 1},
        },
    },
    "text_process": {
        "label": "文本处理",
        "description": "对输入文本执行字符串操作",
        "config_fields": {
            "operation": {
                "type": "enum",
                "options": ["uppercase", "lowercase", "trim", "replace", "split", "join"],
                "default": "trim",
                "description": "操作类型",
            },
            "params": {
                "type": "object",
                "default": {},
                "description": "操作参数（replace: {old, new}; split: {sep}; join: {sep}）",
            },
        },
    },
    "quality_check": {
        "label": "质量检查",
        "description": "对文本进行多维度质量评分（模拟）",
        "config_fields": {
            "dimensions": {
                "type": "array",
                "default": ["连贯性", "逻辑性", "文采", "节奏", "人物", "情节", "设定", "吸引力"],
                "description": "检查维度列表",
            },
            "threshold": {"type": "number", "default": 0.6, "min": 0, "max": 1},
        },
    },
    "condition": {
        "label": "条件分支",
        "description": "根据字段值判断走 true 或 false 分支",
        "config_fields": {
            "field": {"type": "string", "default": "score", "description": "判断字段名"},
            "operator": {
                "type": "enum",
                "options": ["gt", "gte", "lt", "lte", "eq", "ne", "contains"],
                "default": "gte",
            },
            "value": {"type": "any", "default": 0.6},
            "true_branch": {
                "type": "string",
                "default": "",
                "description": "true 分支目标节点ID",
            },
            "false_branch": {
                "type": "string",
                "default": "",
                "description": "false 分支目标节点ID",
            },
        },
    },
    "human_review": {
        "label": "人工审核",
        "description": "暂停等待人工审核（模拟自动通过）",
        "config_fields": {
            "instructions": {
                "type": "string",
                "default": "请审核以下内容",
                "description": "审核说明",
            },
        },
    },
    "input": {
        "label": "输入",
        "description": "工作流输入变量定义",
        "config_fields": {
            "variable_name": {"type": "string", "default": "input_text", "description": "变量名"},
            "description": {"type": "string", "default": "", "description": "变量说明"},
        },
    },
    "output": {
        "label": "输出",
        "description": "工作流输出变量定义",
        "config_fields": {
            "variable_name": {"type": "string", "default": "output_text", "description": "变量名"},
            "description": {"type": "string", "default": "", "description": "变量说明"},
        },
    },
}


class WorkflowNode(BaseModel):
    """工作流节点。"""

    id: str = Field(..., description="节点ID")
    type: str = Field(..., description="节点类型")
    name: str = Field(..., description="节点名称")
    position: dict[str, float] = Field(
        default_factory=lambda: {"x": 0, "y": 0}, description="画布位置 {x, y}"
    )
    config: dict[str, Any] = Field(default_factory=dict, description="节点配置")
    inputs: list[str] = Field(default_factory=list, description="输入连接（上游节点ID）")
    outputs: list[str] = Field(default_factory=list, description="输出连接（下游节点ID）")


class WorkflowEdge(BaseModel):
    """工作流边（节点间连接）。"""

    id: str = Field(..., description="边ID")
    source: str = Field(..., description="源节点ID")
    target: str = Field(..., description="目标节点ID")
    source_handle: str = Field(default="output", description="源端口（output/true/false）")
    target_handle: str = Field(default="input", description="目标端口（input）")


class WorkflowDefinition(BaseModel):
    """工作流定义。"""

    id: str = Field(..., description="工作流ID")
    name: str = Field(..., description="工作流名称")
    description: str = Field(default="", description="工作流描述")
    category: str = Field(default="自定义", description="分类（章节生成/爆款仿写/降AI/自定义）")
    nodes: list[WorkflowNode] = Field(default_factory=list, description="节点列表")
    edges: list[WorkflowEdge] = Field(default_factory=list, description="边列表")
    variables: dict[str, Any] = Field(default_factory=dict, description="全局变量定义")
    is_preset: bool = Field(default=False, description="是否预设工作流")
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)


class WorkflowExecution(BaseModel):
    """工作流执行记录。"""

    id: str = Field(..., description="执行ID")
    workflow_id: str = Field(..., description="工作流ID")
    status: str = Field(default="pending", description="pending/running/completed/failed/cancelled")
    current_node: str = Field(default="", description="当前执行节点ID")
    results: dict[str, Any] = Field(default_factory=dict, description="各节点执行结果")
    logs: list[dict[str, Any]] = Field(default_factory=list, description="执行日志")
    started_at: str = Field(default_factory=_now_iso)
    completed_at: str = Field(default="")
