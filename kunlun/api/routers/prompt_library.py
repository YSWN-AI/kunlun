"""
昆仑创作引擎 — 提示词模板库 API 路由

/prompt-library/templates              — 获取模板列表（筛选+分页）
/prompt-library/templates/{id}         — 获取单个模板详情
/prompt-library/categories             — 获取所有分类及数量
/prompt-library/templates/{id}/use     — 记录使用
/prompt-library/templates/{id}/rate    — 评分
/prompt-library/favorites              — 获取收藏列表
/prompt-library/favorites/{id}         — 收藏/取消收藏
/prompt-library/custom                 — 创建自定义模板
/prompt-library/custom/{id}            — 更新/删除自定义模板
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from kunlun.prompt_library.models import (
    CustomTemplateCreate,
    CustomTemplateUpdate,
    RateRequest,
)

router = APIRouter(prefix="/prompt-library", tags=["提示词模板库"])


@router.get("/templates", summary="获取模板列表")
async def list_templates_endpoint(
    category: str = Query(default="", description="分类筛选"),
    search: str = Query(default="", description="关键词搜索"),
    tag: str = Query(default="", description="标签筛选"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
) -> dict:
    """获取提示词模板列表，支持分类/搜索/标签筛选和分页。"""
    from kunlun.prompt_library.service import list_templates

    templates, total = list_templates(
        category=category,
        search=search,
        tag=tag,
        page=page,
        page_size=page_size,
    )

    return {
        "success": True,
        "templates": [t.model_dump(mode="json") for t in templates],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": page * page_size < total,
    }


@router.get("/templates/{template_id}", summary="获取单个模板详情")
async def get_template_endpoint(template_id: str) -> dict:
    """获取指定模板的完整详情。"""
    from kunlun.prompt_library.service import get_template, is_favorite

    template = get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"模板不存在: {template_id}")

    data = template.model_dump(mode="json")
    data["is_favorite"] = is_favorite(template_id)
    return {"success": True, "template": data}


@router.get("/categories", summary="获取所有分类及数量")
async def get_categories_endpoint() -> dict:
    """获取所有分类及其模板数量。"""
    from kunlun.prompt_library.service import get_categories

    categories = get_categories()
    return {
        "success": True,
        "categories": [c.model_dump() for c in categories],
        "total": len(categories),
    }


@router.post("/templates/{template_id}/use", summary="记录模板使用")
async def use_template_endpoint(template_id: str) -> dict:
    """记录模板使用次数，usage_count +1。"""
    from kunlun.prompt_library.service import record_usage

    if not record_usage(template_id):
        raise HTTPException(status_code=404, detail=f"模板不存在: {template_id}")

    return {"success": True, "template_id": template_id, "message": "使用记录已更新"}


@router.post("/templates/{template_id}/rate", summary="评分模板")
async def rate_template_endpoint(template_id: str, request: RateRequest) -> dict:
    """为模板评分（1-5星）。"""
    from kunlun.prompt_library.service import rate_template

    if not rate_template(template_id, request):
        raise HTTPException(status_code=404, detail=f"模板不存在: {template_id}")

    return {
        "success": True,
        "template_id": template_id,
        "rating": request.rating,
        "message": "评分已记录",
    }


@router.get("/favorites", summary="获取收藏列表")
async def get_favorites_endpoint() -> dict:
    """获取当前收藏的所有模板。"""
    from kunlun.prompt_library.service import get_favorites

    favorites = get_favorites()
    return {
        "success": True,
        "favorites": [t.model_dump(mode="json") for t in favorites],
        "count": len(favorites),
    }


@router.post("/favorites/{template_id}", summary="收藏/取消收藏")
async def toggle_favorite_endpoint(template_id: str) -> dict:
    """切换模板的收藏状态。"""
    from kunlun.prompt_library.service import toggle_favorite

    is_fav = toggle_favorite(template_id)
    if is_fav is None:
        raise HTTPException(status_code=404, detail=f"模板不存在: {template_id}")

    return {
        "success": True,
        "template_id": template_id,
        "is_favorite": is_fav,
        "message": "已收藏" if is_fav else "已取消收藏",
    }


@router.post("/custom", summary="创建自定义模板")
async def create_custom_template_endpoint(request: CustomTemplateCreate) -> dict:
    """创建一个新的自定义提示词模板。"""
    from kunlun.prompt_library.service import create_custom_template

    template = create_custom_template(request)
    return {
        "success": True,
        "template": template.model_dump(mode="json"),
        "message": "自定义模板已创建",
    }


@router.put("/custom/{template_id}", summary="更新自定义模板")
async def update_custom_template_endpoint(
    template_id: str,
    request: CustomTemplateUpdate,
) -> dict:
    """更新自定义模板内容。"""
    from kunlun.prompt_library.service import update_custom_template

    template = update_custom_template(template_id, request)
    if template is None:
        raise HTTPException(
            status_code=404,
            detail=f"自定义模板不存在或非自定义模板: {template_id}",
        )

    return {
        "success": True,
        "template": template.model_dump(mode="json"),
        "message": "模板已更新",
    }


@router.delete("/custom/{template_id}", summary="删除自定义模板")
async def delete_custom_template_endpoint(template_id: str) -> dict:
    """删除自定义模板（内置模板不可删除）。"""
    from kunlun.prompt_library.service import delete_custom_template

    if not delete_custom_template(template_id):
        raise HTTPException(
            status_code=404,
            detail=f"自定义模板不存在或非自定义模板: {template_id}",
        )

    return {
        "success": True,
        "template_id": template_id,
        "message": "模板已删除",
    }
