"""
提示词自定义管理 API 路由
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class SetPromptRequest(BaseModel):
    content: str = Field(..., description="提示词内容", min_length=1)


@router.get("/prompts/{book_id}", summary="列出所有可自定义的提示词状态", tags=["提示词"])
async def list_prompts(book_id: str = "default") -> dict:
    """列出作品的所有提示词及其来源（系统默认/用户覆盖/会话）"""
    from kunlun.prompt_manager import prompt_manager

    prompts = prompt_manager.list_overrides(book_id)
    return {
        "success": True,
        "book_id": book_id,
        "prompts": [
            {
                "agent": p.agent,
                "source": p.source,
                "has_override": p.has_override,
                "preview": p.content[:200] + "..." if len(p.content) > 200 else p.content,
                "length": len(p.content),
            }
            for p in prompts
        ],
    }


@router.get("/prompts/{book_id}/{agent}", summary="获取指定提示词", tags=["提示词"])
async def get_prompt(book_id: str, agent: str) -> dict:
    """获取指定Agent/阶段的提示词完整内容"""
    from kunlun.prompt_manager import CUSTOMIZABLE_PROMPTS, prompt_manager

    if agent not in CUSTOMIZABLE_PROMPTS:
        raise HTTPException(
            status_code=400, detail=f"不可自定义: {agent}，可选: {CUSTOMIZABLE_PROMPTS}"
        )
    source = prompt_manager.get_source(agent, book_id)
    return {
        "success": True,
        "agent": agent,
        "book_id": book_id,
        "source": source.source,
        "has_override": source.has_override,
        "content": source.content,
    }


@router.post("/prompts/{book_id}/{agent}", summary="设置提示词（用户覆盖）", tags=["提示词"])
async def set_prompt(book_id: str, agent: str, req: SetPromptRequest) -> dict:
    """为指定Agent/阶段设置自定义提示词。设置后将覆盖系统默认提示词。"""
    from kunlun.prompt_manager import CUSTOMIZABLE_PROMPTS, prompt_manager

    if agent not in CUSTOMIZABLE_PROMPTS:
        raise HTTPException(
            status_code=400, detail=f"不可自定义: {agent}，可选: {CUSTOMIZABLE_PROMPTS}"
        )
    prompt_manager.set_user_override(agent, book_id, req.content)
    return {
        "success": True,
        "message": f"{book_id}/{agent} 提示词已更新",
        "length": len(req.content),
    }


@router.delete("/prompts/{book_id}/{agent}", summary="重置提示词为系统默认", tags=["提示词"])
async def reset_prompt(book_id: str, agent: str) -> dict:
    """删除用户覆盖，恢复系统默认提示词"""
    from kunlun.prompt_manager import CUSTOMIZABLE_PROMPTS, prompt_manager

    if agent not in CUSTOMIZABLE_PROMPTS:
        raise HTTPException(status_code=400, detail=f"不可自定义: {agent}")
    prompt_manager.reset_user_override(agent, book_id)
    return {"success": True, "message": f"{book_id}/{agent} 已恢复默认"}
