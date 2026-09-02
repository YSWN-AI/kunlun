"""
昆仑创作引擎 — Story Bible 路由 (v2)
对标 Sudowrite / NovelCrafter Codex，四区概览 + Codex 查询 + 上下文 + 创作计划

端点:
  GET  /story-bible/{book_id}/overview                   — 四区概览
  POST /story-bible/{book_id}/codex-query                — Codex 式实体/设定查询
  GET  /story-bible/{book_id}/chapter-context/{chapter}  — 获取某章 Bible 上下文
  GET  /story-bible/{book_id}/workflow-plan              — 获取创作管线计划
  POST /story-bible/{book_id}/workflow-plan              — 创建/更新创作计划
  POST /story-bible/{book_id}/initialize-from-template   — 从模板初始化
  GET  /story-bible/{book_id}/export-codex               — 导出 Codex JSON
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import
from kunlun.api.security_middleware import validate_book_id

router = APIRouter(prefix="/story-bible", tags=["Story Bible"])


class CodexQueryRequest(BaseModel):
    query: str = Field(..., description="自然语言查询", min_length=1)
    entity_types: list[str] = Field(default_factory=list, description="限定实体类型")
    limit: int = Field(default=10, ge=1, le=50)


class WorkflowPlanRequest(BaseModel):
    title: str = Field(default="", description="计划标题")
    steps: list[dict] = Field(default_factory=list, description="管线步骤")
    target_chapters: int = Field(default=100, description="目标章数")


class InitializeRequest(BaseModel):
    template_name: str = Field(default="default", description="模板名称")


@router.get("/{book_id}/overview")
async def story_bible_overview(book_id: str):
    """四区概览：人物/地点/事件/设定"""
    validate_book_id(book_id)
    bible = cached_import("kunlun.story_bible", "StoryBible")
    mgr = bible.get_factory(book_id)
    return {"success": True, "data": mgr.get_overview()}


@router.post("/{book_id}/codex-query")
async def codex_query(book_id: str, req: CodexQueryRequest):
    """Codex 式实体/设定查询"""
    validate_book_id(book_id)
    bible = cached_import("kunlun.story_bible", "StoryBible")
    mgr = bible.get_factory(book_id)
    results = mgr.codex_query(req.query, req.entity_types, req.limit)
    return {"success": True, "data": results}


@router.get("/{book_id}/chapter-context/{chapter}")
async def chapter_context(book_id: str, chapter: int):
    """获取某章的 Story Bible 上下文"""
    validate_book_id(book_id)
    bible = cached_import("kunlun.story_bible", "StoryBible")
    mgr = bible.get_factory(book_id)
    ctx = mgr.get_chapter_context(chapter)
    return {"success": True, "data": ctx}


@router.get("/{book_id}/workflow-plan")
async def get_workflow_plan(book_id: str):
    """获取创作管线计划"""
    validate_book_id(book_id)
    bible = cached_import("kunlun.story_bible", "StoryBible")
    mgr = bible.get_factory(book_id)
    return {"success": True, "data": mgr.get_workflow_plan()}


@router.post("/{book_id}/workflow-plan")
async def update_workflow_plan(book_id: str, req: WorkflowPlanRequest):
    """创建/更新创作计划"""
    validate_book_id(book_id)
    bible = cached_import("kunlun.story_bible", "StoryBible")
    mgr = bible.get_factory(book_id)
    mgr.update_workflow_plan(req.title, req.steps, req.target_chapters)
    return {"success": True, "message": "创作计划已更新"}


@router.post("/{book_id}/initialize-from-template")
async def initialize_from_template(book_id: str, req: InitializeRequest):
    """从模板初始化 story_bible.md"""
    validate_book_id(book_id)
    bible = cached_import("kunlun.story_bible", "StoryBible")
    mgr = bible.get_factory(book_id)
    mgr.initialize_from_template(req.template_name)
    return {"success": True, "message": f"Story Bible 已从模板 '{req.template_name}' 初始化"}


@router.get("/{book_id}/export-codex")
async def export_codex(book_id: str):
    """导出 Codex JSON"""
    validate_book_id(book_id)
    bible = cached_import("kunlun.story_bible", "StoryBible")
    mgr = bible.get_factory(book_id)
    return {"success": True, "data": mgr.export_codex()}
