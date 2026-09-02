"""
昆仑创作引擎 — 可观测性模块

提供：
1. 生成耗时统计（日志 + 内存指标）
2. OpenTelemetry 集成（可选，通过 OTEL_ENABLED 控制）
3. 结构化日志增强

定位：自用为主，商业化时 OpenTelemetry 可直接启用。
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import Any

from loguru import logger

# 内存指标（轻量，无需外部依赖）
_generation_stats: dict[str, list[float]] = {
    "architect": [],  # Architect 蓝图生成耗时
    "writer": [],  # Writer 生成耗时
    "auditor": [],  # Auditor 审计耗时
    "polisher": [],  # StyleEngineer 润色耗时
    "kg_snapshot": [],  # KG 快照耗时
    "total": [],  # 全流程耗时
}


def record_generation_step(step: str, duration_seconds: float) -> None:
    """记录生成管线各步骤耗时"""
    if step in _generation_stats:
        _generation_stats[step].append(duration_seconds)
        # 保留最近1000条
        if len(_generation_stats[step]) > 1000:
            _generation_stats[step] = _generation_stats[step][-1000:]


def get_generation_stats() -> dict:
    """获取生成统计摘要"""
    result = {}
    for step, durations in _generation_stats.items():
        if not durations:
            result[step] = {"count": 0, "avg": 0.0, "p95": 0.0, "max": 0.0}
            continue
        sorted_d = sorted(durations)
        p95_idx = int(len(sorted_d) * 0.95)
        result[step] = {
            "count": len(sorted_d),
            "avg": round(sum(sorted_d) / len(sorted_d), 2),
            "p95": round(sorted_d[min(p95_idx, len(sorted_d) - 1)], 2),
            "max": round(max(sorted_d), 2),
        }
    return result


def timed_step(step_name: str):
    """装饰器：自动记录函数耗时到生成统计"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                record_generation_step(step_name, duration)
                logger.debug(f"[Timing] {step_name}: {duration:.2f}s")

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                record_generation_step(step_name, duration)
                logger.debug(f"[Timing] {step_name}: {duration:.2f}s")

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def init_otel() -> Any:
    """初始化 OpenTelemetry（仅在 OTEL_ENABLED=true 时调用）"""
    try:
        from kunlun.config import settings

        if not settings.otel_enabled:
            logger.info("OpenTelemetry 未启用（OTEL_ENABLED=false）")
            return None

        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource(
            attributes={
                SERVICE_NAME: settings.otel_service_name,
            }
        )

        exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            insecure=True,
        )

        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        logger.info(
            f"OpenTelemetry 已启用: {settings.otel_service_name} → "
            f"{settings.otel_exporter_otlp_endpoint}"
        )
        return provider
    except ImportError:
        logger.warning(
            "OpenTelemetry SDK 未安装（pip install "
            "opentelemetry-exporter-otlp opentelemetry-instrumentation-fastapi）"
        )
        return None
    except Exception as e:
        logger.warning(f"OpenTelemetry 初始化失败: {e}")
        return None


def instrument_app(app: Any) -> None:
    """为 FastAPI app 添加 OpenTelemetry 自动插桩"""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI OpenTelemetry 自动插桩完成")
    except Exception as e:
        logger.debug(f"OpenTelemetry 插桩跳过: {e}")
