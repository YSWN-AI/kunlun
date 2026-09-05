"""
昆仑创作引擎 — 7Agent 协作流程 API 路由

统一前缀 /agent-pipeline，提供 Agent 列表查询、配置管理与单章协作
执行端点。

端点清单:
    GET  /agent-pipeline/agents?book_id=   获取 7 个 Agent 列表及配置
    GET  /agent-pipeline/config?book_id=   获取协作流程配置
    POST /agent-pipeline/config             更新配置
    POST /agent-pipeline/run                执行一章协作流程
"""

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Any

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter(prefix="/agent-pipeline", tags=["7Agent协作流程"])


# ---------------------------------------------------------------------------
# 辅助函数：递归将 dataclass / Enum / 嵌套结构转为可 JSON 序列化的 dict
# ---------------------------------------------------------------------------
def _to_dict(obj: Any) -> Any:
    """递归转换对象为可序列化结构，处理 Enum → .value、dataclass → dict。"""
    if isinstance(obj, Enum):
        return obj.value
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _to_dict(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_dict(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# 请求体模型
# ---------------------------------------------------------------------------
class AgentPipelineConfigRequest(BaseModel):
    """更新协作流程配置请求体。"""

    book_id: str = Field(..., description="书籍ID")
    mode: str | None = Field(default=None, description="运行模式: single / multi")
    agent_models: dict[str, str] | None = Field(default=None, description="每个Agent的模型配置")
    enabled_agents: list[str] | None = Field(default=None, description="启用的Agent id列表")
    max_retries: int | None = Field(default=None, description="失败重试次数")


class AgentPipelineRunRequest(BaseModel):
    """执行一章协作流程请求体。"""

    book_id: str = Field(..., description="书籍ID")
    chapter_number: int = Field(..., description="章节号")
    chapter_title: str = Field(..., description="章节标题")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="上下文信息（outline/volume_outline/previous_chapter/"
        "style_guide/characters/world_setting/target_words 等）",
    )


# ---------------------------------------------------------------------------
# 辅助：获取 AgentPipeline 实例
# ---------------------------------------------------------------------------
def _get_pipeline(book_id: str, data_dir: str = "data") -> Any:
    """延迟导入并创建 AgentPipeline 实例。

    Args:
        book_id: 书籍 ID。
        data_dir: 数据根目录。

    Returns:
        AgentPipeline 实例。
    """
    from kunlun.agent_pipeline.pipeline import AgentPipeline

    return AgentPipeline(book_id=book_id, data_dir=data_dir)


# ---------------------------------------------------------------------------
# GET /agent-pipeline/agents — 获取 7 个 Agent 列表及配置
# ---------------------------------------------------------------------------
@router.get("/agents", summary="获取7个Agent列表及配置")
async def get_agents(book_id: str = "default") -> dict:
    """获取 7 个 Agent 的定义及当前配置状态。

    Args:
        book_id: 书籍 ID，默认 "default"。

    Returns:
        包含 success / agents 列表的响应。
    """
    try:
        pipeline = _get_pipeline(book_id)
        agents = pipeline.get_agents()
        return {"success": True, "book_id": book_id, "agents": agents}
    except Exception as e:
        logger.error(f"[agent-pipeline] 获取Agent列表失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# GET /agent-pipeline/config — 获取协作流程配置
# ---------------------------------------------------------------------------
@router.get("/config", summary="获取协作流程配置")
async def get_config(book_id: str = "default") -> dict:
    """获取指定书籍的协作流程配置。

    Args:
        book_id: 书籍 ID，默认 "default"。

    Returns:
        包含 success / config 的响应。
    """
    try:
        pipeline = _get_pipeline(book_id)
        config = pipeline.load_config()
        return {"success": True, "book_id": book_id, "config": _to_dict(config)}
    except Exception as e:
        logger.error(f"[agent-pipeline] 获取配置失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# POST /agent-pipeline/config — 更新配置
# ---------------------------------------------------------------------------
@router.post("/config", summary="更新协作流程配置")
async def update_config(req: AgentPipelineConfigRequest) -> dict:
    """更新指定书籍的协作流程配置并持久化。

    Args:
        req: 配置更新请求体。

    Returns:
        包含 success / 更新后 config 的响应。
    """
    try:
        pipeline = _get_pipeline(req.book_id)
        update_data: dict[str, Any] = {}
        if req.mode is not None:
            update_data["mode"] = req.mode
        if req.agent_models is not None:
            update_data["agent_models"] = req.agent_models
        if req.enabled_agents is not None:
            update_data["enabled_agents"] = req.enabled_agents
        if req.max_retries is not None:
            update_data["max_retries"] = req.max_retries

        config = pipeline.update_config(update_data)
        return {"success": True, "book_id": req.book_id, "config": _to_dict(config)}
    except ValueError as e:
        logger.warning(f"[agent-pipeline] 配置参数无效: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"[agent-pipeline] 更新配置失败: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# POST /agent-pipeline/run — 执行一章协作流程
# ---------------------------------------------------------------------------
@router.post("/run", summary="执行一章协作流程")
async def run_chapter(req: AgentPipelineRunRequest) -> dict:
    """执行完整的单章 7Agent 协作写作流程。

    多 Agent 模式: structure → blueprint → generation → consistency →
    correction 五步串行。
    单 Agent 模式: 仅执行 generation 一步。

    Args:
        req: 执行请求体，包含 book_id / chapter_number / chapter_title /
            context。

    Returns:
        包含 success / task_id / steps / final_text / total_duration_ms
        的响应。
    """
    try:
        pipeline = _get_pipeline(req.book_id)
        return await pipeline.run_chapter(
            chapter_number=req.chapter_number,
            chapter_title=req.chapter_title,
            context=req.context,
        )
    except Exception as e:
        logger.error(f"[agent-pipeline] 执行协作流程失败: {e}")
        return {
            "success": False,
            "task_id": "",
            "steps": [],
            "final_text": "",
            "total_duration_ms": 0,
            "error": str(e),
        }
