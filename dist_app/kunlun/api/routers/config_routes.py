"""
昆仑创作引擎 —— 作品配置路由
/config/{book_id}, /config/{book_id}/auto-deduce, /config/{book_id}/auto-deduce-all
"""

from fastapi import APIRouter, Query

router = APIRouter(tags=["配置"])


@router.get("/config/{book_id}", summary="获取作品全量配置")
async def get_book_config(book_id: str) -> dict:
    """获取作品的所有可配置字段"""
    from kunlun.book_config import book_config_manager

    config = book_config_manager.get_all(book_id)
    return {"success": True, "config": config}


@router.post("/config/{book_id}", summary="更新作品配置")
async def update_book_config(book_id: str, updates: dict) -> dict:
    """部分更新作品配置（只传需要改的字段）"""
    from kunlun.book_config import book_config_manager

    book_config_manager.update(book_id, updates)
    return {"success": True, "message": f"{book_id} 配置已更新"}


@router.post("/config/{book_id}/auto-deduce", summary="LLM自动推演配置")
async def auto_deduce_config(
    book_id: str, field: str = Query(...), hint: str = Query(default="")
) -> dict:
    """
    对未设定的配置字段用 LLM 自动推演。

    用户问到或用到某个未配置的字段时调用此接口。
    AI会根据作品标题/体裁自动生成合理的配置值。
    """
    from kunlun.book_config import book_config_manager

    result = await book_config_manager.auto_deduce(book_id, field, hint)
    return {"success": True, "field": field, "result": result}


@router.post("/config/{book_id}/auto-deduce-all", summary="LLM自动推演所有未设定配置")
async def auto_deduce_all_config(book_id: str) -> dict:
    """自动推演所有未设定的配置字段（金手指/核心冲突/受众/风格等）"""
    from kunlun.book_config import book_config_manager

    results = await book_config_manager.auto_deduce_all_missing(book_id)
    return {"success": True, "deduced_fields": list(results.keys()), "results": results}
