"""
昆仑创作引擎 — 题材模板 v2 路由
37题材模板库 + 合并

端点:
  GET  /genres-v2             — 获取题材模板库
  GET  /genres-v2/{genre_id}  — 获取指定题材
  POST /genres-v2/merge       — 合并题材配置
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import

router = APIRouter(prefix="/genres-v2", tags=["题材"])


class MergeGenreRequest(BaseModel):
    genre_id: str = Field(...)
    overrides: dict = Field(default_factory=dict)


@router.get("")
async def genres_v2_list():
    """获取题材模板库（37题材）"""
    genre_engine = cached_import("kunlun.genre", "GenreEngine")
    return {"success": True, "data": genre_engine.list_all()}


@router.get("/{genre_id}")
async def genres_v2_get(genre_id: str):
    """获取指定题材配置"""
    genre_engine = cached_import("kunlun.genre", "GenreEngine")
    data = genre_engine.get(genre_id)
    if not data:
        return {"success": False, "error": f"题材 '{genre_id}' 不存在"}
    return {"success": True, "data": data}


@router.post("/merge")
async def genres_v2_merge(req: MergeGenreRequest):
    """合并题材配置"""
    genre_engine = cached_import("kunlun.genre", "GenreEngine")
    result = genre_engine.merge(req.genre_id, req.overrides)
    return {"success": True, "data": result}
