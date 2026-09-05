"""
昆仑创作引擎 — AI拆书案例库 API 路由

/book-analysis/cases              — 案例列表（筛选+分页）
/book-analysis/cases/{case_id}    — 案例详情
/book-analysis/categories         — 题材分类及数量
/book-analysis/compare             — 多案例对比分析
/book-analysis/methodology         — 共性方法论提炼
/book-analysis/custom              — 创建自定义案例
/book-analysis/custom/{case_id}    — 更新/删除自定义案例
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from kunlun.book_analysis.models import (
    CompareRequest,
    CustomCaseCreateRequest,
    CustomCaseUpdateRequest,
    MethodologyRequest,
)

router = APIRouter(prefix="/book-analysis", tags=["AI拆书案例库"])


@router.get("/cases", summary="案例列表（支持筛选+分页）")
async def list_cases(
    genre: str = Query(default="", description="题材筛选"),
    platform: str = Query(default="", description="平台筛选"),
    tag: str = Query(default="", description="标签筛选"),
    search: str = Query(default="", description="关键词搜索（标题/作者/简介/标签）"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
) -> dict:
    """获取拆书案例列表，支持题材/平台/标签/关键词筛选和分页。"""
    from kunlun.book_analysis.service import search_cases

    cases, total = search_cases(
        genre=genre or None,
        platform=platform or None,
        tag=tag or None,
        search=search or None,
        page=page,
        page_size=page_size,
    )
    return {
        "success": True,
        "total": total,
        "page": page,
        "page_size": page_size,
        "count": len(cases),
        "cases": [c.model_dump() for c in cases],
    }


@router.get("/cases/{case_id}", summary="案例详情")
async def get_case_detail(case_id: str) -> dict:
    """根据ID获取单个拆书案例的完整详情。"""
    from kunlun.book_analysis.service import get_case

    case = get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"案例不存在: {case_id}")
    return {"success": True, "case": case.model_dump()}


@router.get("/categories", summary="获取题材分类及数量")
async def get_categories_endpoint() -> dict:
    """获取所有题材分类及其案例数量。"""
    from kunlun.book_analysis.service import get_categories

    categories = get_categories()
    return {
        "success": True,
        "count": len(categories),
        "categories": categories,
    }


@router.post("/compare", summary="多案例对比分析")
async def compare_cases_endpoint(req: CompareRequest) -> dict:
    """
    对多个案例进行对比分析，返回叙事节奏/爽点设置/情节结构/
    风格指纹/人物弧光各维度的对比矩阵。
    """
    if len(req.case_ids) < 2:
        raise HTTPException(status_code=400, detail="至少需要2个案例ID进行对比")

    from kunlun.book_analysis.service import compare_cases

    result = compare_cases(req.case_ids)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "对比失败"))
    return result


@router.post("/methodology", summary="提炼共性方法论")
async def extract_methodology_endpoint(req: MethodologyRequest) -> dict:
    """从多个案例中提炼通用写作技巧，按类别分组并标注跨案例共性模式。"""
    if not req.case_ids:
        raise HTTPException(status_code=400, detail="case_ids 不能为空")

    from kunlun.book_analysis.service import extract_methodology

    result = extract_methodology(req.case_ids)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "提炼失败"))
    return result


@router.post("/custom", summary="创建自定义拆书案例")
async def create_custom_case_endpoint(req: CustomCaseCreateRequest) -> dict:
    """创建用户自定义的拆书案例，存储到 data/book_analysis/ 目录。"""
    from kunlun.book_analysis.service import create_custom_case

    case = create_custom_case(req)
    return {
        "success": True,
        "message": "自定义案例创建成功",
        "case_id": case.id,
        "case": case.model_dump(),
    }


@router.put("/custom/{case_id}", summary="更新自定义案例")
async def update_custom_case_endpoint(case_id: str, req: CustomCaseUpdateRequest) -> dict:
    """更新用户自定义的拆书案例。仅允许更新自定义案例，内置案例不可修改。"""
    from kunlun.book_analysis.service import update_custom_case

    case = update_custom_case(case_id, req)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail=f"自定义案例不存在或不可修改: {case_id}",
        )
    return {
        "success": True,
        "message": "自定义案例更新成功",
        "case": case.model_dump(),
    }


@router.delete("/custom/{case_id}", summary="删除自定义案例")
async def delete_custom_case_endpoint(case_id: str) -> dict:
    """删除用户自定义的拆书案例。内置案例不可删除。"""
    from kunlun.book_analysis.service import delete_custom_case

    deleted = delete_custom_case(case_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"自定义案例不存在或不可删除: {case_id}",
        )
    return {"success": True, "message": f"自定义案例已删除: {case_id}"}
