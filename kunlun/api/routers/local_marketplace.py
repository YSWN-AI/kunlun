"""
昆仑创作引擎 — 本地技能包市场 API 路由

提供组合包的列表/详情/安装/卸载/已安装/热门/搜索端点。

端点:
  GET  /local-marketplace/list       — 列出可安装组合包
  GET  /local-marketplace/detail     — 获取组合包详情
  POST /local-marketplace/install    — 安装组合包
  POST /local-marketplace/uninstall  — 卸载组合包
  GET  /local-marketplace/installed  — 列出已安装
  GET  /local-marketplace/hot        — 热门组合包
  GET  /local-marketplace/search     — 搜索
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from loguru import logger
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import

router = APIRouter(prefix="/local-marketplace", tags=["本地技能包市场"])


# ─── 请求模型 ─────────────────────────────────────────────


class InstallRequest(BaseModel):
    book_id: str = Field(..., description="作品ID")
    pack_id: str = Field(..., description="组合包ID")


class UninstallRequest(BaseModel):
    book_id: str = Field(..., description="作品ID")
    pack_id: str = Field(..., description="组合包ID")


# ─── 路由端点 ─────────────────────────────────────────────


def _get_engine():
    """获取本地技能包市场引擎（延迟导入）"""
    return cached_import("kunlun.local_marketplace", "get_local_marketplace")()


@router.get("/list", summary="列出可安装组合包")
async def list_packs(
    category: str | None = Query(
        default=None,
        description="分类筛选: xuanhuan/xianxia/dushi/lishi/kehuan",
    ),
) -> dict:
    """列出所有可安装的组合包，可按分类筛选。"""
    engine = _get_engine()
    packs = engine.list_available(category=category)
    return {
        "success": True,
        "data": packs,
        "total": len(packs),
    }


@router.get("/detail", summary="获取组合包详情")
async def get_detail(
    pack_id: str = Query(..., description="组合包ID"),
) -> dict:
    """获取组合包详细信息，包含 Rule/Workflow/Skill 完整内容。"""
    engine = _get_engine()
    detail = engine.get_detail(pack_id)
    if not detail:
        return {"success": False, "error": f"组合包不存在: {pack_id}"}
    return {"success": True, "data": detail}


@router.post("/install", summary="安装组合包")
async def install_pack(req: InstallRequest) -> dict:
    """将组合包安装到指定书籍，写入 writing_packs.json。"""
    logger.info(f"[LocalMarketplace] 安装请求: book={req.book_id}, pack={req.pack_id}")
    engine = _get_engine()
    ok = engine.install(req.book_id, req.pack_id)
    if not ok:
        return {
            "success": False,
            "error": f"安装失败: 组合包 {req.pack_id} 不存在或写入失败",
        }
    return {
        "success": True,
        "message": f"组合包已安装到书籍 {req.book_id}",
        "data": {"book_id": req.book_id, "pack_id": req.pack_id},
    }


@router.post("/uninstall", summary="卸载组合包")
async def uninstall_pack(req: UninstallRequest) -> dict:
    """从指定书籍卸载组合包。"""
    logger.info(f"[LocalMarketplace] 卸载请求: book={req.book_id}, pack={req.pack_id}")
    engine = _get_engine()
    ok = engine.uninstall(req.book_id, req.pack_id)
    if not ok:
        return {
            "success": False,
            "error": f"卸载失败: 组合包 {req.pack_id} 未安装或删除失败",
        }
    return {
        "success": True,
        "message": f"组合包已从书籍 {req.book_id} 卸载",
        "data": {"book_id": req.book_id, "pack_id": req.pack_id},
    }


@router.get("/installed", summary="列出已安装组合包")
async def list_installed(
    book_id: str = Query(..., description="作品ID"),
) -> dict:
    """列出指定书籍已安装的所有组合包。"""
    engine = _get_engine()
    packs = engine.list_installed(book_id)
    return {
        "success": True,
        "data": packs,
        "total": len(packs),
    }


@router.get("/hot", summary="热门组合包")
async def get_hot(
    limit: int = Query(default=5, ge=1, le=20, description="返回数量"),
) -> dict:
    """获取热门组合包（按下载量排序）。"""
    engine = _get_engine()
    packs = engine.get_hot(limit=limit)
    return {
        "success": True,
        "data": packs,
        "total": len(packs),
    }


@router.get("/search", summary="搜索组合包")
async def search_packs(
    q: str = Query(..., description="搜索关键词"),
) -> dict:
    """按名称/描述/标签搜索组合包。"""
    engine = _get_engine()
    packs = engine.search(q)
    return {
        "success": True,
        "data": packs,
        "total": len(packs),
        "query": q,
    }
