"""
昆仑创作引擎 — 规划/行动双模式路由

端点:
  GET  /mode/current     — 获取当前模式
  POST /mode/switch      — 切换模式
  GET  /mode/config      — 获取模式配置
  PUT  /mode/config      — 更新模式配置
  GET  /mode/can-execute — 当前是否可执行
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import
from kunlun.api.security_middleware import validate_book_id

router = APIRouter(prefix="/mode", tags=["WritingMode"])


# ─── 请求模型 ──────────────────────────────────────


class CurrentModeRequest(BaseModel):
    book_id: str = Field(..., description="作品 ID")


class SwitchModeRequest(BaseModel):
    book_id: str = Field(..., description="作品 ID")
    mode: str = Field(..., description="目标模式：planning 或 action")


class ModeConfigRequest(BaseModel):
    book_id: str = Field(..., description="作品 ID")


class UpdateModeConfigRequest(BaseModel):
    book_id: str = Field(..., description="作品 ID")
    mode: str = Field(..., description="目标模式：planning 或 action")
    config: dict = Field(
        default_factory=dict,
        description="模式配置，支持 model/temperature/max_tokens/auto_approve",
    )


class CanExecuteRequest(BaseModel):
    book_id: str = Field(..., description="作品 ID")


# ─── 端点 ──────────────────────────────────────────


def _get_manager(book_id: str):
    """延迟导入并实例化 ModeManager。"""
    manager_cls = cached_import("kunlun.writing_mode", "ModeManager")
    return manager_cls(book_id)


def _get_mode_enum():
    """延迟导入 WritingMode 枚举。"""
    return cached_import("kunlun.writing_mode", "WritingMode")


@router.get("/current")
async def get_current_mode(book_id: str):
    """获取当前写作模式。"""
    validate_book_id(book_id)
    manager = _get_manager(book_id)
    mode = manager.get_mode(book_id)
    return {
        "success": True,
        "data": {
            "mode": mode.value,
            "can_execute": mode.value == "action",
            "prompt_suffix": manager.get_system_prompt_suffix(book_id),
        },
    }


@router.post("/switch")
async def switch_mode(req: SwitchModeRequest):
    """切换写作模式。"""
    validate_book_id(req.book_id)
    writing_mode_cls = _get_mode_enum()
    try:
        target_mode = writing_mode_cls(req.mode)
    except ValueError:
        return {"success": False, "message": f"无效模式: {req.mode}，仅支持 planning/action"}
    manager = _get_manager(req.book_id)
    old_mode = manager.get_mode(req.book_id)
    manager.set_mode(req.book_id, target_mode)
    return {
        "success": True,
        "data": {
            "old_mode": old_mode.value,
            "new_mode": target_mode.value,
            "can_execute": target_mode.value == "action",
        },
        "message": f"模式已从 {old_mode.value} 切换为 {target_mode.value}",
    }


@router.get("/config")
async def get_mode_config(book_id: str):
    """获取模式配置（含两种模式的模型配置）。"""
    validate_book_id(book_id)
    manager = _get_manager(book_id)
    config = manager.get_mode_config(book_id)
    return {"success": True, "data": config}


@router.put("/config")
async def update_mode_config(req: UpdateModeConfigRequest):
    """更新指定模式的配置。"""
    validate_book_id(req.book_id)
    writing_mode_cls = _get_mode_enum()
    try:
        target_mode = writing_mode_cls(req.mode)
    except ValueError:
        return {"success": False, "message": f"无效模式: {req.mode}，仅支持 planning/action"}
    manager = _get_manager(req.book_id)
    manager.update_mode_config(req.book_id, target_mode, req.config)
    updated = manager.get_mode_config(req.book_id)
    mode_config = updated["configs"].get(target_mode.value, {})
    return {
        "success": True,
        "data": {"mode": target_mode.value, "config": mode_config},
        "message": f"模式 {target_mode.value} 配置已更新",
    }


@router.get("/can-execute")
async def can_execute(book_id: str):
    """当前模式是否允许执行实际写作。"""
    validate_book_id(book_id)
    manager = _get_manager(book_id)
    executable = manager.should_execute(book_id)
    mode = manager.get_mode(book_id)
    return {
        "success": True,
        "data": {
            "can_execute": executable,
            "current_mode": mode.value,
            "reason": "行动模式，允许执行" if executable else "规划模式，仅输出计划不执行",
        },
    }
