"""
昆仑创作引擎 — Token 用量路由
/usage/{book_id}
"""

from fastapi import APIRouter

router = APIRouter(tags=["运维"])


@router.get("/usage/{book_id}", summary="Token用量统计")
async def get_usage(book_id: str = "default") -> dict:
    """Token用量和费用统计"""
    from kunlun.token_tracker import token_tracker

    summary = token_tracker.get_summary(book_id)
    total = summary.get("_total", {})
    return {
        "success": True,
        "total_tokens": total.get("total_tokens", 0),
        "total_cost_usd": round(total.get("total_cost", 0), 4),
        "calls": total.get("calls", 0),
        "by_agent": {k: v for k, v in summary.items() if k != "_total"},
    }
