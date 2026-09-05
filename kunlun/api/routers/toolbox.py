"""
昆仑创作引擎 — 专业生成器工具箱 API 路由

/toolbox/generate/{generator_type}  — 通用生成接口
/toolbox/generators                  — 获取所有可用生成器
/toolbox/save                        — 保存生成结果到书籍
/toolbox/history                     — 获取生成历史
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from kunlun.toolbox.models import (
    GENERATOR_TYPES,
    GenericGenerateRequest,
    SaveRequest,
)

router = APIRouter(prefix="/toolbox", tags=["专业生成器工具箱"])


@router.post("/generate/{generator_type}", summary="通用生成接口")
async def generate_endpoint(
    generator_type: str,
    request: GenericGenerateRequest,
) -> dict:
    """
    调用指定生成器生成内容。

    generator_type 可选：title / synopsis / outline / chapter_outline /
    opening / cheat / name / character
    """
    if generator_type not in GENERATOR_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"未知的生成器类型: {generator_type}，可用: {', '.join(GENERATOR_TYPES)}",
        )

    from kunlun.toolbox.service import generate

    try:
        result = generate(generator_type, request)
        return {
            "success": True,
            "generator_type": generator_type,
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {e}") from e


@router.get("/generators", summary="获取所有可用生成器列表")
async def list_generators_endpoint() -> dict:
    """列出所有8种生成器及其描述。"""
    from kunlun.toolbox.service import list_generators

    generators = list_generators()
    return {
        "success": True,
        "count": len(generators),
        "generators": [g.model_dump() for g in generators],
    }


@router.post("/save", summary="保存生成结果到当前书籍项目")
async def save_result_endpoint(request: SaveRequest) -> dict:
    """
    将生成结果保存到 data/books/{book_id}/toolbox/ 目录。
    """
    from kunlun.toolbox.service import save_result

    try:
        result = save_result(request)
        if result.get("success"):
            return {"success": True, **result}
        raise HTTPException(status_code=500, detail=result.get("error", "保存失败"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/history", summary="获取生成历史")
async def get_history_endpoint(
    book_id: str = Query(default="", description="书籍ID，留空返回全部"),
    limit: int = Query(default=50, ge=1, le=200, description="返回条数"),
) -> dict:
    """获取生成历史记录，可按书籍筛选。"""
    from kunlun.toolbox.service import get_history

    records = get_history(book_id=book_id, limit=limit)
    return {
        "success": True,
        "count": len(records),
        "history": [r.model_dump(mode="json") for r in records],
    }
