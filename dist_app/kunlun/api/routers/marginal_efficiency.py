"""
边际收益监控 API — 优化效果量化与健康检查

提供以下端点：
  GET  /api/pipeline/marginal-efficiency/report   — 当前优化报告
  GET  /api/pipeline/marginal-efficiency/health    — 系统健康摘要
  POST /api/pipeline/marginal-efficiency/analyze   — 触发分析
  GET  /api/pipeline/marginal-efficiency/history   — 优化历史
"""

from fastapi import APIRouter

from kunlun.marginal_efficiency import (
    OptimizationMetrics,
    marginal_analyzer,
    optimization_monitor,
    resource_reallocator,
)

router = APIRouter(prefix="/marginal-efficiency", tags=["边际收益优化"])


@router.get("/report")
async def get_optimization_report():
    """获取当前边际收益优化报告"""
    report = resource_reallocator.execute_optimization()

    return {
        "round": report.round_number,
        "modules_analyzed": report.modules_analyzed,
        "low_efficiency_modules": report.low_efficiency_modules,
        "directives": [
            {
                "module": d.module_name,
                "action": d.action.value,
                "target": d.target,
                "reason": d.reason,
                "expected_saving_lines": d.expected_saving_lines,
                "expected_saving_ms": d.expected_saving_ms,
                "priority": d.priority,
            }
            for d in report.directives
        ],
        "reallocations": [
            {
                "from": r.from_module,
                "to": r.to_module,
                "resource": r.resource_type,
                "amount": r.amount,
                "expected_roi_gain": round(r.expected_roi_gain, 3),
            }
            for r in report.reallocations
        ],
        "total_lines_saved": report.total_lines_saved,
        "total_ms_saved": report.total_ms_saved,
        "overall_roi_improvement": round(report.overall_roi_improvement, 3),
    }


@router.get("/health")
async def get_marginal_health():
    """获取系统边际收益健康摘要"""
    summary = optimization_monitor.get_health_summary()

    return {
        "status": summary["status"],
        "code_efficiency_ratio": round(summary["cer"], 3),
        "avg_roi": round(summary["roi"], 2),
        "roi_change_from_baseline": round(summary["roi_change_from_baseline"], 3),
        "low_efficiency_ratio": round(summary["low_efficiency_ratio"], 3),
        "total_lines": summary["total_lines"],
        "optimization_rounds": summary["optimization_rounds"],
        "marginal_roi_warning": summary["marginal_roi_warning"],
    }


@router.post("/analyze")
async def trigger_analysis():
    """触发一次边际收益分析（含监控快照）"""
    report = resource_reallocator.execute_optimization()

    # 记录优化快照
    baseline_lines = sum(m.code_lines for m in marginal_analyzer._module_metrics.values())
    low_count = len(report.low_efficiency_modules)
    total = report.modules_analyzed

    metrics = OptimizationMetrics(
        total_lines=baseline_lines - report.total_lines_saved,
        dead_code_lines=0,  # 需要在代码扫描中填充
        duplicate_lines=0,
        swallowed_exceptions=0,
        todo_count=0,
        avg_roi=(
            sum(m.roi_score for m in marginal_analyzer._module_metrics.values()) / max(total, 1)
        ),
        low_efficiency_ratio=low_count / max(total, 1),
    )
    delta = optimization_monitor.record_snapshot(metrics)

    return {
        "report": {
            "round": report.round_number,
            "low_efficiency_count": len(report.low_efficiency_modules),
            "directives_count": len(report.directives),
            "reallocations_count": len(report.reallocations),
        },
        "delta": delta,
    }


@router.get("/history")
async def get_optimization_history():
    """获取优化历史"""
    history = [
        {
            "round": report.round_number,
            "modules_analyzed": report.modules_analyzed,
            "low_efficiency_count": len(report.low_efficiency_modules),
            "total_lines_saved": report.total_lines_saved,
            "overall_roi_improvement": round(report.overall_roi_improvement, 3),
            "timestamp": report.timestamp,
        }
        for report in marginal_analyzer._optimization_history
    ]

    return {
        "total_rounds": len(history),
        "history": history,
    }
