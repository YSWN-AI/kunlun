"""
昆仑创作引擎 —— 搜索路由
/search
"""

from fastapi import APIRouter, Query

from kunlun.kg.client import kg_client

router = APIRouter(tags=["搜索"])


@router.get("/search", summary="全文搜索")
async def search(
    q: str = Query(min_length=1, description="搜索关键词"),
    limit: int = Query(default=20, le=100, description="返回上限"),
) -> dict:
    """基于 FTS5 全文索引搜索实体（角色/物品/地点等）"""
    results = kg_client.search_entities(q, limit)
    return {"success": True, "data": {"query": q, "count": len(results), "results": results}}
