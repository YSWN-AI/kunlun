"""
昆仑创作引擎 — 质量路由
/quality/trends, /quality/check, /quality/fanqie, /quality/refine
"""

from fastapi import APIRouter, Query

router = APIRouter(tags=["质量"])


@router.get("/quality/trends/{book_id}", summary="质量趋势")
async def get_quality_trends(book_id: str) -> dict:
    """获取作品质量趋势"""
    from kunlun.quality.tracker import QualityTracker

    tracker = QualityTracker(book_id)
    return {"success": True, "data": tracker.get_summary()}


@router.post("/quality/check", summary="质量看板检查")
async def quality_check(
    _book_id: str = Query(default="", description="作品ID"),
    chapter: int = Query(default=0, description="章节号"),
    text: str = Query(default="", description="正文"),
) -> dict:
    """运行质量看板检查"""
    if not text:
        return {"success": False, "error": "缺少text参数"}
    from kunlun.quality import quality_dashboard

    report = quality_dashboard.analyze_chapter(text, chapter=chapter)
    return {"success": True, "data": report.to_dict()}


@router.post("/quality/fanqie", summary="番茄流量门禁检查")
async def fanqie_check(
    _book_id: str = Query(default="", description="作品ID"),
    chapter: int = Query(default=1, description="章节号"),
    text: str = Query(default="", description="正文"),
    is_first_three: bool = Query(default=False),
) -> dict:
    """运行番茄平台流量适配检查"""
    if not text:
        return {"success": False, "error": "缺少text参数"}
    from kunlun.audit.fanqie_gates import fanqie_optimizer

    report = fanqie_optimizer.check_chapter(text, chapter=chapter, is_first_three=is_first_three)
    return {"success": True, "data": report.to_dict()}


@router.post("/quality/refine", summary="文本精炼")
async def refine_text(
    _book_id: str = Query(default="", description="作品ID"),
    text: str = Query(default="", description="正文"),
    analyze_only: bool = Query(default=False),
) -> dict:
    """运行文本精炼（去套路词）"""
    if not text:
        return {"success": False, "error": "缺少text参数"}
    from kunlun.style.refiner import text_refiner

    if analyze_only:
        report = text_refiner.analyze(text)
        return {
            "success": True,
            "action": "analyze",
            "total_issues": report.total_fixes,
            "by_category": report.fixes_by_category,
            "details": report.details[:20],
        }
    refined, report = text_refiner.refine(text)
    return {
        "success": True,
        "action": "refine",
        "original_length": len(text),
        "refined_length": len(refined),
        "changes": report.total_fixes,
        "refined_text": refined,
    }
