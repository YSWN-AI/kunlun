"""
昆仑创作引擎 — 管理路由
/health, /status 等运维端点
"""

from fastapi import APIRouter

from kunlun import __version__
from kunlun.config import settings
from kunlun.kg.client import kg_client
from kunlun.observability import get_generation_stats

router = APIRouter(tags=["管理"])


@router.get("/health", include_in_schema=False)
async def health() -> dict:
    """健康检查"""
    try:
        kg_status = kg_client.health_check()
    except Exception as e:
        kg_status = {"error": str(e)}
    return {
        "status": "ok",
        "version": __version__,
        "env": settings.app_env,
        "kg": kg_status,
        "generation_stats": get_generation_stats(),
        "auth_enabled": settings.api_auth_enabled,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
    }


@router.get("/status", summary="系统状态", tags=["管理"])
async def system_status() -> dict:
    """获取系统完整状态（代码版本、KG 连接、向量数据库状态等）"""
    try:
        from kunlun.agents import __all__ as agent_list
    except Exception:
        agent_list = []
    return {
        "success": True,
        "data": {
            "version": __version__,
            "env": settings.app_env,
            "uptime": "running",
            "agents": agent_list,
            "kg": kg_client.health_check(),
        },
    }
