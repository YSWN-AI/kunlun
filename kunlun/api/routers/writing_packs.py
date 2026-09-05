"""
写作内容包 API 路由 — Rule / Workflow / Skill 三插件体系

端点:
  GET    /writing-packs/list              — 列出所有包（book_id, type可选过滤）
  GET    /writing-packs/get               — 获取单个包（book_id, pack_id）
  POST   /writing-packs/create            — 创建自定义包
  PUT    /writing-packs/update            — 更新包
  DELETE /writing-packs/delete            — 删除包
  POST   /writing-packs/toggle            — 启用/禁用包
  GET    /writing-packs/active-rules      — 获取活跃Rule列表（book_id）
  GET    /writing-packs/workflow-by-command — 按命令查找Workflow（book_id, command）
  GET    /writing-packs/skills-for-scene  — 按场景获取Skill（book_id, scene）
  POST   /writing-packs/inject-prompt     — 注入包上下文到Prompt（book_id, base_prompt）
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import
from kunlun.api.security_middleware import validate_book_id

router = APIRouter(prefix="/writing-packs", tags=["写作内容包"])


# ─── 请求模型 ──────────────────────────────────────────────


class CreatePackRequest(BaseModel):
    """创建包请求"""

    book_id: str = Field(..., description="作品ID")
    pack_data: dict = Field(..., description="包数据，包含 id/name/description/type 及类型特有字段")


class UpdatePackRequest(BaseModel):
    """更新包请求"""

    book_id: str = Field(..., description="作品ID")
    pack_id: str = Field(..., description="包ID")
    updates: dict = Field(..., description="更新字段")


class DeletePackRequest(BaseModel):
    """删除包请求"""

    book_id: str = Field(..., description="作品ID")
    pack_id: str = Field(..., description="包ID")


class TogglePackRequest(BaseModel):
    """启用/禁用包请求"""

    book_id: str = Field(..., description="作品ID")
    pack_id: str = Field(..., description="包ID")
    enabled: bool = Field(..., description="是否启用")


class InjectPromptRequest(BaseModel):
    """注入Prompt上下文请求"""

    book_id: str = Field(..., description="作品ID")
    base_prompt: str = Field(..., description="原始Prompt")
    scene: str | None = Field(default=None, description="可选场景名称，用于匹配Skill")


# ─── 辅助函数 ──────────────────────────────────────────────


def _get_manager(book_id: str):
    """获取 WritingPackManager 实例（延迟导入）"""
    manager_cls = cached_import("kunlun.writing_packs", "WritingPackManager")
    return manager_cls(book_id)


# ─── 端点实现 ──────────────────────────────────────────────


@router.get("/list")
async def list_packs(
    book_id: str = Query(..., description="作品ID"),
    pack_type: str | None = Query(default=None, description="包类型过滤: rule/workflow/skill"),
):
    """列出所有包（含内置+用户自定义），可按类型过滤"""
    validate_book_id(book_id)
    mgr = _get_manager(book_id)
    if pack_type:
        from kunlun.writing_packs.models import PackType

        try:
            ptype = PackType(pack_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效包类型: {pack_type}") from None
        packs = mgr.list_packs(ptype)
    else:
        packs = mgr.list_packs()
    return {"success": True, "data": packs, "total": len(packs)}


@router.get("/get")
async def get_pack(
    book_id: str = Query(..., description="作品ID"),
    pack_id: str = Query(..., description="包ID"),
):
    """获取单个包详情"""
    validate_book_id(book_id)
    mgr = _get_manager(book_id)
    pack = mgr.get_pack(pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail=f"包不存在: {pack_id}")
    return {"success": True, "data": pack}


@router.post("/create")
async def create_pack(req: CreatePackRequest):
    """创建自定义包"""
    validate_book_id(req.book_id)
    mgr = _get_manager(req.book_id)
    try:
        pack = mgr.create_pack(req.pack_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"success": True, "data": pack, "message": "包创建成功"}


@router.put("/update")
async def update_pack(req: UpdatePackRequest):
    """更新包（内置包仅允许修改 enabled）"""
    validate_book_id(req.book_id)
    mgr = _get_manager(req.book_id)
    ok = mgr.update_pack(req.pack_id, req.updates)
    if not ok:
        raise HTTPException(status_code=400, detail="更新失败：包不存在或内置包不允许修改该字段")
    pack = mgr.get_pack(req.pack_id)
    return {"success": True, "data": pack, "message": "包更新成功"}


@router.delete("/delete")
async def delete_pack(
    book_id: str = Query(..., description="作品ID"),
    pack_id: str = Query(..., description="包ID"),
):
    """删除自定义包（内置包不可删除）"""
    validate_book_id(book_id)
    mgr = _get_manager(book_id)
    ok = mgr.delete_pack(pack_id)
    if not ok:
        raise HTTPException(status_code=400, detail="删除失败：包不存在或为内置包")
    return {"success": True, "message": "包删除成功"}


@router.post("/toggle")
async def toggle_pack(req: TogglePackRequest):
    """启用/禁用包"""
    validate_book_id(req.book_id)
    mgr = _get_manager(req.book_id)
    ok = mgr.toggle_pack(req.pack_id, req.enabled)
    if not ok:
        raise HTTPException(status_code=400, detail="操作失败：包不存在")
    return {"success": True, "data": {"pack_id": req.pack_id, "enabled": req.enabled}}


@router.get("/active-rules")
async def active_rules(book_id: str = Query(..., description="作品ID")):
    """获取所有启用的 Rule 内容列表（用于 Prompt 注入）"""
    validate_book_id(book_id)
    mgr = _get_manager(book_id)
    rules = mgr.get_active_rules()
    return {"success": True, "data": rules, "count": len(rules)}


@router.get("/workflow-by-command")
async def workflow_by_command(
    book_id: str = Query(..., description="作品ID"),
    command: str = Query(..., description="触发命令，如 /revise"),
):
    """按触发命令查找启用的 Workflow"""
    validate_book_id(book_id)
    mgr = _get_manager(book_id)
    workflow = mgr.get_workflow_by_command(command)
    if workflow is None:
        raise HTTPException(status_code=404, detail=f"未找到触发命令为 '{command}' 的工作流")
    return {"success": True, "data": workflow}


@router.get("/skills-for-scene")
async def skills_for_scene(
    book_id: str = Query(..., description="作品ID"),
    scene: str = Query(..., description="场景名称，如 world_building/combat"),
):
    """按场景获取激活的 Skill 列表"""
    validate_book_id(book_id)
    mgr = _get_manager(book_id)
    skills = mgr.get_skills_for_scene(scene)
    return {"success": True, "data": skills, "count": len(skills)}


@router.post("/inject-prompt")
async def inject_prompt(req: InjectPromptRequest):
    """将活跃 Rule 和场景 Skill 注入到 Prompt"""
    validate_book_id(req.book_id)
    mgr = _get_manager(req.book_id)
    result = mgr.inject_prompt_context(req.base_prompt, req.scene)
    return {"success": True, "data": {"enhanced_prompt": result}}
