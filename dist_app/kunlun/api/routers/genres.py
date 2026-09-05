"""
昆仑创作引擎 —— 体裁模板路由
/genres, /genres/{genre_name}
"""

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["体裁"])


@router.get("/genres", summary="列出所有支持的体裁")
async def list_genres_endpoint() -> dict:
    """列出所有支持的体裁及其配置（每章字数/章节类型/门槛权重/写作建议）"""
    from kunlun.genres import list_genres

    return {"success": True, "genres": list_genres()}


@router.get("/genres/{genre_name}", summary="获取体裁详情")
async def get_genre_endpoint(genre_name: str) -> dict:
    """获取指定体裁的完整配置"""
    from kunlun.genres import get_genre

    genre = get_genre(genre_name)
    if not genre:
        raise HTTPException(status_code=404, detail=f"不支持的体裁: {genre_name}")
    return {"success": True, "genre": genre.__dict__}
