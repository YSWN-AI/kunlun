"""
昆仑创作引擎 — 统一异常处理层

类型化异常 → HTTP 状态码精确映射。
替换 main.py 中简单的 400/500 兜底，提供更精确的状态码。
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger

from kunlun.common.alerter import alerter
from kunlun.config import settings
from kunlun.exceptions import (
    # Audit
    AuditError,
    AuditGateError,
    # Config
    ConfigError,
    ConfigValidationError,
    ExportDependencyError,
    # Export
    ExportError,
    ExportFormatError,
    # Gacha
    GachaError,
    GachaKeyExhaustedError,
    GachaModelError,
    GachaRateLimitError,
    KGConnectionError,
    KGEntityNotFoundError,
    # KG
    KGError,
    KunlunError,
    # Pipeline
    PipelineError,
    PipelineStepError,
    PipelineTimeoutError,
    WriterBudgetError,
    # Writer
    WriterError,
    WriterGenerationError,
    WriterRevisionError,
)

# 异常类型 → HTTP 状态码映射表
EXCEPTION_STATUS_MAP: dict[type[KunlunError], int] = {
    # Writer: 生成相关错误 → 422
    WriterError: 422,
    WriterBudgetError: 422,
    WriterRevisionError: 422,
    WriterGenerationError: 422,
    # Pipeline: 内部处理错误
    PipelineError: 500,
    PipelineStepError: 500,
    PipelineTimeoutError: 504,  # Gateway Timeout
    # Gacha: 上游 LLM API 问题
    GachaError: 502,
    GachaModelError: 502,
    GachaKeyExhaustedError: 503,
    GachaRateLimitError: 429,  # 上游限流 → Too Many Requests
    # KG: 数据库问题
    KGError: 500,
    KGConnectionError: 503,
    KGEntityNotFoundError: 404,
    # Export: 导出相关
    ExportError: 422,
    ExportFormatError: 400,
    ExportDependencyError: 501,  # Not Implemented
    # Audit: 审计相关
    AuditError: 422,
    AuditGateError: 422,
    # Config: 配置问题
    ConfigError: 400,
    ConfigValidationError: 400,
}


async def kunlun_exception_handler(request: Request, exc: KunlunError) -> JSONResponse:
    """KunlunError 统一处理：按类型映射 HTTP 状态码，保留 detail 字段"""
    status_code = EXCEPTION_STATUS_MAP.get(type(exc), 400)

    logger.warning(
        f"{request.method} {request.url.path} → {status_code} ({type(exc).__name__}): {exc}"
    )
    alerter.record_error(f"{type(exc).__name__}: {exc}"[:1000])

    content: dict = {
        "success": False,
        "error": str(exc),
        "error_type": type(exc).__name__,
    }
    if exc.detail:
        content["detail"] = exc.detail

    return JSONResponse(status_code=status_code, content=content)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """非 KunlunError 兜底处理：记录完整 traceback"""

    logger.opt(exception=True).error(f"未处理异常: {request.method} {request.url.path}")
    alerter.record_error(f"{type(exc).__name__}: {exc}"[:1000])

    is_dev = settings.app_env == "development"
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc) if is_dev else "服务器内部错误，请稍后重试",
            "error_type": "InternalError",
        },
    )


def register_exception_handlers(app):
    """注册所有 KunlunError 子类的精确处理器 + 兜底处理器"""
    for exc_cls in EXCEPTION_STATUS_MAP:
        app.add_exception_handler(exc_cls, kunlun_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    logger.info(f"异常处理器已注册: {len(EXCEPTION_STATUS_MAP)} 种类型化异常 + 通用兜底")
