"""
健康检查 / 系统状态 API 路由
"""

from __future__ import annotations

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field

from kunlun.kg.client import kg_client

router = APIRouter()


class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="服务状态")
    version: str = Field(default="0.2.0", description="引擎版本")
    kg: str = Field(default="unknown", description="知识图谱状态")


class SystemStatusResponse(BaseModel):
    success: bool = Field(..., description="是否成功")
    data: dict = Field(default_factory=dict, description="kg/embedder 健康状态")


@router.get("/health", summary="健康检查", tags=["系统"])
async def health_check():
    """返回服务健康状态"""
    from kunlun import __version__

    kg_status = kg_client.health_check() if hasattr(kg_client, "health_check") else "unknown"
    return {"status": "ok", "version": __version__, "kg": str(kg_status)}


@router.get(
    "/status",
    response_model=SystemStatusResponse,
    summary="系统状态",
    description="返回 KG（Neo4j/QLite图/Qdrant/FTS5）和 Embedder 的健康状态。",
    tags=["运维"],
)
async def system_status() -> dict:
    from kunlun.kg.embedder import embedder

    try:
        _ = embedder.model
    except Exception as e:
        logger.warning(f"Embedder 模型加载失败（状态查询继续）: {e}")
    return {
        "success": True,
        "data": {
            "kg": kg_client.health_check(),
            "embedder": embedder.stats,
        },
    }
