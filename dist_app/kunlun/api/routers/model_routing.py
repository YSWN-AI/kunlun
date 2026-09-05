"""
昆仑创作引擎 — 模型路由摘要路由 (v2)

端点:
  GET /model-routing/summary — 模型路由摘要
  GET /model-routing/compare — 不同模型成本对比
"""

from fastapi import APIRouter

from kunlun.api.routers._shared import cached_import

router = APIRouter(prefix="/model-routing", tags=["模型路由"])


@router.get("/summary")
async def model_routing_summary():
    """获取模型路由摘要"""
    model_router = cached_import("kunlun.model_router", "model_router")
    return {"success": True, "data": model_router.get_tier_stats()}


@router.get("/compare")
async def model_routing_compare():
    """比较不同模型成本"""
    model_router = cached_import("kunlun.model_router", "model_router")
    return {"success": True, "data": model_router.get_costs()}
