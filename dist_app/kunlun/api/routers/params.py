"""
昆仑创作引擎 — 模型参数管理路由
/params/defs, /params/{book_id}, /params/{book_id}/{agent}, POST /params/{book_id}/{param}
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["参数"])


class SetParamRequest(BaseModel):
    value: float = Field(..., description="参数值")
    agent: str = Field(..., description="Agent名称")


@router.get("/params/defs", summary="列出所有可调模型参数的定义")
async def list_param_defs() -> dict:
    """列出所有模型参数的定义（含推荐范围、默认值、Agent默认值）"""
    from kunlun.model_params import AGENTS, PARAM_DEFS

    return {
        "success": True,
        "params": [
            {
                "key": p.key,
                "label": p.label,
                "description": p.description,
                "default": p.default,
                "min": p.min_val,
                "max": p.max_val,
                "step": p.step,
                "agent_defaults": p.agent_defaults,
            }
            for p in PARAM_DEFS
        ],
        "agents": AGENTS,
    }


@router.get("/params/{book_id}", summary="获取作品所有Agent的模型参数")
async def get_all_params(book_id: str = "default") -> dict:
    """获取指定作品所有Agent的所有参数值"""
    from kunlun.model_params import model_param_manager

    return {
        "success": True,
        "book_id": book_id,
        "params": model_param_manager.get_all_agents(book_id),
    }


@router.get("/params/{book_id}/{agent}", summary="获取指定Agent的模型参数")
async def get_agent_params(book_id: str, agent: str) -> dict:
    from kunlun.model_params import AGENTS, model_param_manager

    if agent not in AGENTS:
        raise HTTPException(status_code=400, detail=f"未知Agent: {agent}，可选: {AGENTS}")
    return {
        "success": True,
        "book_id": book_id,
        "agent": agent,
        "params": model_param_manager.get_all(agent, book_id),
    }


@router.post("/params/{book_id}/{param}", summary="设置模型参数")
async def set_param(book_id: str, param: str, req: SetParamRequest) -> dict:
    from kunlun.model_params import AGENTS, PARAM_DEFS, model_param_manager

    if req.agent not in AGENTS:
        raise HTTPException(status_code=400, detail=f"未知Agent: {req.agent}")
    param_keys = [p.key for p in PARAM_DEFS]
    if param not in param_keys:
        raise HTTPException(status_code=400, detail=f"未知参数: {param}，可选: {param_keys}")
    try:
        warning = model_param_manager.set(req.agent, param, req.value, book_id)
        return {
            "success": True,
            "message": f"{book_id}/{req.agent}.{param} = {req.value}",
            "warning": warning,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
