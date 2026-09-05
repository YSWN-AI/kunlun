"""
昆仑创作引擎 — KUNLUN.md 项目宪法路由

端点:
  POST /constitution/generate       — 生成 KUNLUN.md
  GET  /constitution/read           — 读取全文
  GET  /constitution/section        — 读取指定段落
  PUT  /constitution/section        — 更新指定段落
  POST /constitution/active-state   — 更新活跃写作状态
  POST /constitution/constraint     — 添加约束
  GET  /constitution/prompt-context — 获取 Prompt 摘要
  GET  /constitution/history        — 获取变更历史
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import
from kunlun.api.security_middleware import validate_book_id

router = APIRouter(prefix="/constitution", tags=["Constitution"])


# ─── 请求模型 ──────────────────────────────────────


class GenerateRequest(BaseModel):
    book_id: str = Field(..., description="作品 ID")
    metadata: dict = Field(default_factory=dict, description="作品元数据（project.json 内容）")


class ReadRequest(BaseModel):
    book_id: str = Field(..., description="作品 ID")


class SectionRequest(BaseModel):
    book_id: str = Field(..., description="作品 ID")
    section: str = Field(..., description="段落名（支持 1-8 序号、英文 key、中文别名）")


class UpdateSectionRequest(BaseModel):
    book_id: str = Field(..., description="作品 ID")
    section: str = Field(..., description="段落名")
    content: str = Field(..., description="新的段落正文")


class ActiveStateRequest(BaseModel):
    book_id: str = Field(..., description="作品 ID")
    state: dict = Field(
        default_factory=dict,
        description=(
            "活跃状态字典，支持 current_chapter/current_volume/"
            "protagonist_realm/protagonist_location/recent_plot/"
            "pending_threads/character_snapshots"
        ),
    )


class ConstraintRequest(BaseModel):
    book_id: str = Field(..., description="作品 ID")
    constraint: str = Field(..., description="约束内容", min_length=1)
    source: str = Field(default="用户", description="约束来源")


class PromptContextRequest(BaseModel):
    book_id: str = Field(..., description="作品 ID")


class HistoryRequest(BaseModel):
    book_id: str = Field(..., description="作品 ID")


# ─── 端点 ──────────────────────────────────────────


def _get_engine(book_id: str):
    """延迟导入并实例化 ConstitutionEngine。"""
    engine_cls = cached_import("kunlun.constitution", "ConstitutionEngine")
    return engine_cls(book_id)


@router.post("/generate")
async def generate_constitution(req: GenerateRequest):
    """生成 KUNLUN.md 初始模板。"""
    validate_book_id(req.book_id)
    engine = _get_engine(req.book_id)
    content = engine.generate_template(req.book_id, req.metadata)
    return {"success": True, "data": {"content": content, "path": str(engine.constitution_path)}}


@router.get("/read")
async def read_constitution(book_id: str):
    """读取 KUNLUN.md 全文。"""
    validate_book_id(book_id)
    engine = _get_engine(book_id)
    content = engine.read(book_id)
    return {"success": True, "data": {"content": content}}


@router.get("/section")
async def read_section(book_id: str, section: str):
    """读取指定段落。"""
    validate_book_id(book_id)
    engine = _get_engine(book_id)
    content = engine.read_section(book_id, section)
    return {"success": True, "data": {"section": section, "content": content}}


@router.put("/section")
async def update_section(req: UpdateSectionRequest):
    """更新指定段落。"""
    validate_book_id(req.book_id)
    engine = _get_engine(req.book_id)
    ok = engine.update_section(req.book_id, req.section, req.content)
    if not ok:
        return {"success": False, "message": f"段落 '{req.section}' 不存在或更新失败"}
    return {"success": True, "message": f"段落 '{req.section}' 已更新"}


@router.post("/active-state")
async def update_active_state(req: ActiveStateRequest):
    """更新活跃写作状态（写作会话后调用）。"""
    validate_book_id(req.book_id)
    engine = _get_engine(req.book_id)
    ok = engine.update_active_state(req.book_id, req.state)
    if not ok:
        return {"success": False, "message": "活跃状态更新失败"}
    return {"success": True, "message": "活跃写作状态已更新"}


@router.post("/constraint")
async def add_constraint(req: ConstraintRequest):
    """添加约束到关键笔记与软约束。"""
    validate_book_id(req.book_id)
    engine = _get_engine(req.book_id)
    ok = engine.add_constraint(req.book_id, req.constraint, req.source)
    if not ok:
        return {"success": False, "message": "约束添加失败"}
    return {"success": True, "message": "约束已添加"}


@router.get("/prompt-context")
async def get_prompt_context(book_id: str):
    """获取用于 LLM Prompt 的宪法摘要。"""
    validate_book_id(book_id)
    engine = _get_engine(book_id)
    context = engine.get_prompt_context(book_id)
    return {"success": True, "data": {"context": context, "length": len(context)}}


@router.get("/history")
async def get_history(book_id: str):
    """获取宪法变更历史。"""
    validate_book_id(book_id)
    engine = _get_engine(book_id)
    history = engine.get_version_history(book_id)
    return {"success": True, "data": {"history": history, "count": len(history)}}
