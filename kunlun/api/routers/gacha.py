"""
昆仑创作引擎 —— 抽卡引擎路由
/gacha/models
"""

from fastapi import APIRouter

router = APIRouter(tags=["抽卡"])


@router.get("/gacha/models", summary="抽卡引擎: 列出可用模型")
async def list_gacha_models() -> dict:
    """列出所有可用的抽卡模型及其评分维度"""
    from kunlun.gacha.engine import gacha_engine

    models = [
        {
            "name": getattr(m, "name", "unknown"),
            "score": getattr(m, "score", 0.0),
        }
        for m in getattr(gacha_engine, "_models", [])
    ]

    return {
        "success": True,
        "models": models,
        "default_mode": "gacha_parallel_3",
    }
