"""
昆仑创作引擎 — 工作流可视化编辑器 API 路由

/workflow-engine/workflows          — 工作流 CRUD
/workflow-engine/presets            — 预设工作流列表
/workflow-engine/workflows/{id}/execute — 执行工作流
/workflow-engine/executions         — 执行记录
/workflow-engine/node-types         — 可用节点类型
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from kunlun.workflow_engine.models import NODE_TYPE_CONFIG_SCHEMA, NODE_TYPES

router = APIRouter(prefix="/workflow-engine", tags=["工作流可视化编辑器"])


# ── 请求/响应模型 ─────────────────────────────────────────────
class ExecuteRequest(BaseModel):
    """执行工作流请求体。"""

    inputs: dict[str, Any] = Field(default_factory=dict, description="工作流输入变量")


class WorkflowCreateRequest(BaseModel):
    """创建工作流请求体。"""

    name: str
    description: str = ""
    category: str = "自定义"
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)


class WorkflowUpdateRequest(BaseModel):
    """更新工作流请求体。"""

    name: str | None = None
    description: str | None = None
    category: str | None = None
    nodes: list[dict[str, Any]] | None = None
    edges: list[dict[str, Any]] | None = None
    variables: dict[str, Any] | None = None


# ── 工作流 CRUD ───────────────────────────────────────────────
@router.get("/workflows", summary="工作流列表")
async def list_workflows_endpoint(
    category: str | None = Query(default=None, description="按分类筛选"),
    search: str | None = Query(default=None, description="按名称/描述搜索"),
) -> dict:
    """获取工作流列表（包含预设和自定义）。"""
    from kunlun.workflow_engine.service import list_workflows

    workflows = list_workflows(category=category, search=search)
    return {
        "success": True,
        "count": len(workflows),
        "workflows": [w.model_dump(mode="json") for w in workflows],
    }


@router.get("/workflows/{workflow_id}", summary="工作流详情")
async def get_workflow_endpoint(workflow_id: str) -> dict:
    """获取单个工作流的完整定义。"""
    from kunlun.workflow_engine.service import get_workflow

    workflow = get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail=f"工作流不存在: {workflow_id}")
    return {"success": True, "workflow": workflow.model_dump(mode="json")}


@router.post("/workflows", summary="创建工作流")
async def create_workflow_endpoint(request: WorkflowCreateRequest) -> dict:
    """创建自定义工作流。"""
    from kunlun.workflow_engine.service import create_workflow

    try:
        workflow = create_workflow(request.model_dump())
        return {"success": True, "workflow": workflow.model_dump(mode="json")}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/workflows/{workflow_id}", summary="更新工作流")
async def update_workflow_endpoint(workflow_id: str, request: WorkflowUpdateRequest) -> dict:
    """更新自定义工作流（预设不可修改）。"""
    from kunlun.workflow_engine.service import update_workflow

    data = {k: v for k, v in request.model_dump().items() if v is not None}
    try:
        workflow = update_workflow(workflow_id, data)
        if workflow is None:
            raise HTTPException(status_code=404, detail=f"工作流不存在: {workflow_id}")
        return {"success": True, "workflow": workflow.model_dump(mode="json")}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/workflows/{workflow_id}", summary="删除工作流")
async def delete_workflow_endpoint(workflow_id: str) -> dict:
    """删除自定义工作流（预设不可删除）。"""
    from kunlun.workflow_engine.service import delete_workflow

    try:
        deleted = delete_workflow(workflow_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"工作流不存在: {workflow_id}")
        return {"success": True, "message": f"工作流 {workflow_id} 已删除"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ── 预设工作流 ────────────────────────────────────────────────
@router.get("/presets", summary="预设工作流列表")
async def list_presets_endpoint() -> dict:
    """获取所有内置预设工作流。"""
    from kunlun.workflow_engine.service import list_presets

    presets = list_presets()
    return {
        "success": True,
        "count": len(presets),
        "presets": [p.model_dump(mode="json") for p in presets],
    }


# ── 执行管理 ──────────────────────────────────────────────────
@router.post("/workflows/{workflow_id}/execute", summary="执行工作流")
async def execute_workflow_endpoint(workflow_id: str, request: ExecuteRequest) -> dict:
    """
    执行指定工作流。

    LLM 节点使用模拟执行（不调用真实 LLM），确保离线可用。
    返回完整的执行记录，包含各节点结果和详细日志。
    """
    from kunlun.workflow_engine.service import execute_workflow

    try:
        execution = execute_workflow(workflow_id, request.inputs)
        return {
            "success": True,
            "execution": execution.model_dump(mode="json"),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行失败: {e}") from e


@router.get("/executions/{execution_id}", summary="获取执行状态")
async def get_execution_endpoint(execution_id: str) -> dict:
    """获取工作流执行的详细状态和结果。"""
    from kunlun.workflow_engine.service import get_execution

    execution = get_execution(execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail=f"执行记录不存在: {execution_id}")
    return {"success": True, "execution": execution.model_dump(mode="json")}


@router.get("/executions", summary="执行记录列表")
async def list_executions_endpoint(
    workflow_id: str | None = Query(default=None, description="按工作流筛选"),
) -> dict:
    """获取所有执行记录，可按工作流筛选。"""
    from kunlun.workflow_engine.service import list_executions

    executions = list_executions(workflow_id=workflow_id)
    return {
        "success": True,
        "count": len(executions),
        "executions": [e.model_dump(mode="json") for e in executions],
    }


@router.post("/executions/{execution_id}/cancel", summary="取消执行")
async def cancel_execution_endpoint(execution_id: str) -> dict:
    """取消正在运行的工作流执行。"""
    from kunlun.workflow_engine.service import cancel_execution

    cancelled = cancel_execution(execution_id)
    if not cancelled:
        raise HTTPException(
            status_code=400,
            detail=f"无法取消执行: {execution_id}（不存在或已结束）",
        )
    return {"success": True, "message": f"执行 {execution_id} 已取消"}


# ── 节点类型 ──────────────────────────────────────────────────
@router.get("/node-types", summary="获取可用节点类型及配置说明")
async def get_node_types_endpoint() -> dict:
    """
    获取所有可用的节点类型及其配置字段说明。

    供前端可视化编辑器渲染节点属性面板。
    """
    return {
        "success": True,
        "count": len(NODE_TYPES),
        "node_types": NODE_TYPES,
        "config_schema": NODE_TYPE_CONFIG_SCHEMA,
    }
