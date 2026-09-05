"""
昆仑创作引擎 — 世界观设定 API 路由

统一前缀 /world-setting，提供 30 类结构化世界观设定的 CRUD、
版本历史、按卷可见性过滤（RAG 用）和关键词搜索。

端点清单:
  GET    /world-setting/categories              获取所有类别 schema
  GET    /world-setting/entries                 列出设定条目（可按类别过滤）
  POST   /world-setting/entries                 创建条目
  GET    /world-setting/entries/{entry_id}      获取条目详情
  PUT    /world-setting/entries/{entry_id}      更新条目
  DELETE /world-setting/entries/{entry_id}      删除条目
  GET    /world-setting/entries/{entry_id}/history  版本历史
  GET    /world-setting/visible                 获取指定卷可见的设定（RAG 用）
  GET    /world-setting/search                  搜索设定
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter(prefix="/world-setting", tags=["世界观设定"])


# ─── 请求体模型 ─────────────────────────────────────────────────────────────
class WorldSettingCreateRequest(BaseModel):
    """创建设定条目请求体。"""

    book_id: str = Field(default="default", description="书籍 ID")
    category: str = Field(..., description="类别 ID（如 power_system）")
    name: str = Field(..., description="条目名称")
    fields: dict[str, Any] = Field(default_factory=dict, description="结构化字段值")
    visible_from_volume: int = Field(default=0, description="从第几卷可见，0=始终可见")
    hidden_from_ai: bool = Field(default=False, description="是否对 AI 隐藏防剧透")
    tags: list[str] = Field(default_factory=list, description="标签列表")


class WorldSettingUpdateRequest(BaseModel):
    """更新设定条目请求体。"""

    book_id: str = Field(default="default", description="书籍 ID")
    fields: dict[str, Any] = Field(default_factory=dict, description="新的字段值（全量替换）")
    change_note: str = Field(default="", description="变更说明")


# ─── 辅助函数 ───────────────────────────────────────────────────────────────
def _get_manager(book_id: str):
    """延迟导入并创建 WorldSettingManager 实例。"""
    from kunlun.world_setting.manager import WorldSettingManager

    return WorldSettingManager(book_id)


# ─── 类别 Schema ────────────────────────────────────────────────────────────
@router.get("/categories", summary="获取所有类别 schema")
async def get_categories() -> dict:
    """获取 30 类世界观设定的结构化字段定义。"""
    try:
        from kunlun.world_setting.schema import get_all_categories, get_category_count

        categories = get_all_categories()
        return {
            "success": True,
            "total": get_category_count(),
            "categories": categories,
        }
    except Exception as e:
        logger.error(f"[world-setting] categories 失败: {e}")
        return {"success": False, "error": str(e)}


# ─── 条目列表 ───────────────────────────────────────────────────────────────
@router.get("/entries", summary="列出设定条目")
async def list_entries(book_id: str = "default", category: str = "") -> dict:
    """列出设定条目，可按类别过滤。

    Args:
        book_id: 书籍 ID
        category: 类别 ID（可选，空字符串返回全部）
    """
    try:
        manager = _get_manager(book_id)
        cat = category if category else None
        entries = manager.list_entries(category=cat)
        return {"success": True, "entries": entries, "total": len(entries)}
    except Exception as e:
        logger.error(f"[world-setting] entries list 失败: {e}")
        return {"success": False, "error": str(e)}


# ─── 创建条目 ───────────────────────────────────────────────────────────────
@router.post("/entries", summary="创建设定条目")
async def create_entry(req: WorldSettingCreateRequest) -> dict:
    """创建新的世界观设定条目。"""
    try:
        manager = _get_manager(req.book_id)
        entry = manager.create_entry(
            category=req.category,
            name=req.name,
            fields=req.fields,
            visible_from_volume=req.visible_from_volume,
            hidden_from_ai=req.hidden_from_ai,
            tags=req.tags,
        )
        return {"success": True, "entry": entry, "id": entry["id"]}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"[world-setting] entry create 失败: {e}")
        return {"success": False, "error": str(e)}


# ─── 获取条目详情 ───────────────────────────────────────────────────────────
@router.get("/entries/{entry_id}", summary="获取条目详情")
async def get_entry(entry_id: str, book_id: str = "default") -> dict:
    """根据 ID 获取单个设定条目（含完整版本历史）。"""
    try:
        manager = _get_manager(book_id)
        entry = manager.get_entry(entry_id)
        if entry is None:
            return {"success": False, "error": "entry not found"}
        return {"success": True, "entry": entry}
    except Exception as e:
        logger.error(f"[world-setting] entry get 失败: {e}")
        return {"success": False, "error": str(e)}


# ─── 更新条目 ───────────────────────────────────────────────────────────────
@router.put("/entries/{entry_id}", summary="更新设定条目")
async def update_entry(entry_id: str, req: WorldSettingUpdateRequest) -> dict:
    """更新设定条目，自动记录版本历史。"""
    try:
        manager = _get_manager(req.book_id)
        entry = manager.update_entry(
            entry_id=entry_id,
            fields=req.fields,
            change_note=req.change_note,
        )
        if entry is None:
            return {"success": False, "error": "entry not found"}
        return {"success": True, "entry": entry}
    except Exception as e:
        logger.error(f"[world-setting] entry update 失败: {e}")
        return {"success": False, "error": str(e)}


# ─── 删除条目 ───────────────────────────────────────────────────────────────
@router.delete("/entries/{entry_id}", summary="删除设定条目")
async def delete_entry(entry_id: str, book_id: str = "default") -> dict:
    """删除设定条目。"""
    try:
        manager = _get_manager(book_id)
        deleted = manager.delete_entry(entry_id)
        if not deleted:
            return {"success": False, "error": "entry not found"}
        return {"success": True, "deleted": True}
    except Exception as e:
        logger.error(f"[world-setting] entry delete 失败: {e}")
        return {"success": False, "error": str(e)}


# ─── 版本历史 ───────────────────────────────────────────────────────────────
@router.get("/entries/{entry_id}/history", summary="获取条目版本历史")
async def get_entry_history(entry_id: str, book_id: str = "default") -> dict:
    """获取设定条目的版本历史追溯。"""
    try:
        manager = _get_manager(book_id)
        history = manager.get_entry_history(entry_id)
        return {"success": True, "history": history, "total": len(history)}
    except Exception as e:
        logger.error(f"[world-setting] entry history 失败: {e}")
        return {"success": False, "error": str(e)}


# ─── 可见性过滤（RAG 核心） ─────────────────────────────────────────────────
@router.get("/visible", summary="获取指定卷可见的设定（RAG 用）")
async def get_visible_settings(
    book_id: str = "default",
    volume: int = 0,
    include_hidden: bool = False,
) -> dict:
    """获取对当前卷可见的设定，RAG 检索时的核心过滤端点。

    过滤逻辑:
      visible_from_volume <= volume
      AND (not hidden_from_ai OR include_hidden)

    Args:
        book_id: 书籍 ID
        volume: 当前卷号
        include_hidden: 是否包含对 AI 隐藏的设定（仅人工查看时用 True）
    """
    try:
        manager = _get_manager(book_id)
        settings = manager.get_visible_settings(
            current_volume=volume,
            include_hidden=include_hidden,
        )
        return {"success": True, "settings": settings, "total": len(settings)}
    except Exception as e:
        logger.error(f"[world-setting] visible 失败: {e}")
        return {"success": False, "error": str(e)}


# ─── 搜索 ───────────────────────────────────────────────────────────────────
@router.get("/search", summary="搜索设定")
async def search_entries(
    book_id: str = "default",
    q: str = "",
    volume: int = 999,
) -> dict:
    """关键词搜索设定条目，自动应用可见性过滤。

    在条目名称、字段值、标签中进行不区分大小写的子串匹配。

    Args:
        book_id: 书籍 ID
        q: 搜索关键词
        volume: 当前卷号（用于可见性过滤，默认 999 表示全部可见）
    """
    try:
        manager = _get_manager(book_id)
        results = manager.search_entries(query=q, current_volume=volume)
        return {"success": True, "results": results, "total": len(results)}
    except Exception as e:
        logger.error(f"[world-setting] search 失败: {e}")
        return {"success": False, "error": str(e)}
