"""
LLM 成本优化 API —— 缓存控制/压缩管理/费用追踪

端点：
  GET  /api/v2/optimization/cache/stats     —— 缓存统计
  POST /api/v2/optimization/cache/configure —— 配置缓存模式
  POST /api/v2/optimization/cache/clear     —— 清除缓存
  GET  /api/v2/optimization/compress/stats  —— 压缩统计
  POST /api/v2/optimization/compress/test   —— 测试压缩效果
  GET  /api/v2/optimization/cost/summary    —— 费用摘要
  GET  /api/v2/optimization/cost/report     —— 费用报告
  POST /api/v2/optimization/cost/budget     —— 设置预算
  GET  /api/v2/optimization/health          —— 优化健康检查
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kunlun.cost_tracker import cost_tracker
from kunlun.llm_cache import CacheMode, llm_cache
from kunlun.prompt_compressor import CompressionLevel, prompt_compressor

router = APIRouter(prefix="/optimization", tags=["成本优化"])


# ──────────── 请求模型 ─────────────────────────


class CacheConfigRequest(BaseModel):
    mode: str = Field("exact", description="缓存模式: disabled/exact/semantic/aggressive")


class CompressTestRequest(BaseModel):
    text: str = Field(..., description="待压缩文本")
    level: str = Field("standard", description="压缩级别: off/light/standard/aggressive")


class BudgetUpdateRequest(BaseModel):
    daily: float | None = Field(None, description="每日预算 ($)")
    monthly: float | None = Field(None, description="每月预算 ($)")
    project: float | None = Field(None, description="每本书预算 ($)")


class CacheClearRequest(BaseModel):
    older_than_hours: int = Field(0, description="仅清除超过N小时的缓存（0=全部）")


# ──────────── 缓存端点 ─────────────────────────


@router.get("/cache/stats")
async def get_cache_stats():
    """获取缓存统计"""
    stats = llm_cache.get_stats()
    return {
        "mode": llm_cache._mode.value,
        "total_requests": stats.total_requests,
        "exact_hits": stats.exact_hits,
        "semantic_hits": stats.semantic_hits,
        "misses": stats.misses,
        "hit_rate": round(stats.hit_rate, 3),
        "tokens_saved": stats.tokens_saved,
        "cost_saved_usd": round(stats.cost_saved_usd, 5),
        "avg_latency_saved_ms": round(stats.avg_latency_saved_ms, 1),
    }


@router.post("/cache/configure")
async def configure_cache(req: CacheConfigRequest):
    """配置缓存模式"""
    mode_map = {
        "disabled": CacheMode.DISABLED,
        "exact": CacheMode.EXACT,
        "semantic": CacheMode.SEMANTIC,
        "aggressive": CacheMode.AGGRESSIVE,
    }
    mode = mode_map.get(req.mode, CacheMode.EXACT)
    llm_cache.configure(mode)
    return {"status": "ok", "mode": mode.value}


@router.post("/cache/clear")
async def clear_cache(req: CacheClearRequest):
    """清除缓存"""
    count = llm_cache.clear(older_than_seconds=req.older_than_hours * 3600)
    return {"status": "ok", "cleared_entries": count}


# ──────────── 压缩端点 ─────────────────────────


@router.get("/compress/stats")
async def get_compress_stats():
    """获取压缩统计"""
    stats = prompt_compressor.get_stats()
    return {
        "total_compressed": stats.total_compressed,
        "total_tokens_original": stats.total_tokens_original,
        "total_tokens_saved": stats.total_tokens_saved,
        "saving_rate": round(stats.total_saving_rate, 3),
        "avg_ratio": stats.avg_ratio,
    }


@router.post("/compress/test")
async def test_compress(req: CompressTestRequest):
    """测试压缩效果（不修改实际数据）"""
    level_map = {
        "off": CompressionLevel.OFF,
        "light": CompressionLevel.LIGHT,
        "standard": CompressionLevel.STANDARD,
        "aggressive": CompressionLevel.AGGRESSIVE,
    }
    level = level_map.get(req.level, CompressionLevel.STANDARD)
    result = prompt_compressor.compress(req.text, level)

    return {
        "level": level.value,
        "original_tokens": result.original_tokens,
        "compressed_tokens": result.compressed_tokens,
        "saved_tokens": result.saved_tokens,
        "ratio": result.ratio,
        "saving_rate": round(1 - result.ratio if result.original_tokens > 0 else 0, 3),
        "compressed_preview": result.compressed[:500] + "..."
        if len(result.compressed) > 500
        else result.compressed,
        "stats": result.stats,
    }


# ──────────── 费用端点 ─────────────────────────


@router.get("/cost/summary")
async def get_cost_summary():
    """获取费用摘要"""
    return cost_tracker.get_summary()


@router.get("/cost/report")
async def get_cost_report(period: str = "daily", book_id: str = ""):
    """获取费用报告

    Args:
        period: daily/monthly/project
        book_id: 书籍ID（project模式必填）
    """
    report = cost_tracker.generate_report(period, book_id)
    return {
        "period": report.period,
        "total_cost": report.total_cost,
        "total_tokens": report.total_tokens,
        "by_model": report.by_model,
        "by_agent": report.by_agent,
        "by_action": report.by_action,
        "savings_from_cache": report.savings_from_cache,
        "savings_from_compression": report.savings_from_compression,
    }


@router.post("/cost/budget")
async def set_cost_budget(req: BudgetUpdateRequest):
    """设置预算"""
    cost_tracker.set_budget(
        daily=req.daily,
        monthly=req.monthly,
        project=req.project,
    )
    status = cost_tracker.get_budget_status()
    return {
        "status": "ok",
        "tier": status.tier.value,
        "daily": {"limit": status.daily_limit, "used": status.daily_used},
        "monthly": {"limit": status.monthly_limit, "used": status.monthly_used},
    }


@router.get("/health")
async def get_optimization_health():
    """优化模块健康检查"""
    cache_stats = llm_cache.get_stats()
    compress_stats = prompt_compressor.get_stats()
    cost_status = cost_tracker.get_budget_status()

    return {
        "cache": {
            "mode": llm_cache._mode.value,
            "hit_rate": round(cache_stats.hit_rate, 3),
            "tokens_saved": cache_stats.tokens_saved,
        },
        "compression": {
            "saving_rate": round(compress_stats.total_saving_rate, 3),
            "total_saved_tokens": compress_stats.total_tokens_saved,
        },
        "cost": {
            "tier": cost_status.tier.value,
            "daily_ratio": round(cost_status.daily_used / max(cost_status.daily_limit, 0.01), 3),
            "total_calls": cost_status.total_calls,
            "cached_ratio": round(cost_status.cached_calls / max(cost_status.total_calls, 1), 3),
        },
    }
