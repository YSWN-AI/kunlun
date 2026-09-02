"""
昆仑创作引擎 — API 认证模块

提供 API Key 认证依赖，支持按环境自动启停。
开发环境默认关闭认证，生产环境建议启用。
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader
from loguru import logger

from kunlun.config import settings

# API Key 从请求头 X-API-Key 中读取
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# 免认证路径白名单（即使启用认证也允许匿名访问）
_AUTH_WHITELIST = {
    "/health",
    "/api/v1/health",
    "/api/v1/status",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
}


def _is_whitelisted(path: str) -> bool:
    """检查路径是否在免认证白名单中"""
    return path in _AUTH_WHITELIST or path.startswith("/ws/")


async def verify_api_key(
    request: Request,
    api_key: str = Depends(_api_key_header),
) -> bool:
    """FastAPI 依赖：验证 API Key。

    认证逻辑：
    - 未启用 (api_auth_enabled=False)：直接放行
    - 白名单路径：直接放行
    - 未提供 Key 或 Key 不匹配：返回 401
    - Key 匹配：放行

    用法（全局应用或路由级别）：
        router = APIRouter(dependencies=[Depends(verify_api_key)])
    """
    # 认证未启用 → 直接放行
    if not settings.api_auth_enabled:
        return True

    # 白名单路径 → 免认证
    if _is_whitelisted(request.url.path):
        return True

    # 未提供 API Key
    if not settings.api_auth_key:
        logger.warning("API 认证已启用但未配置 api_auth_key，拒绝所有请求")
        raise HTTPException(status_code=503, detail="API 认证配置错误")

    if not api_key:
        raise HTTPException(status_code=401, detail="缺少 API Key，请在 X-API-Key 请求头中提供")

    # 常量时间比较防止时序攻击
    import hmac

    if not hmac.compare_digest(api_key, settings.api_auth_key):
        logger.warning(f"API 认证失败: {request.url.path} (来源: {request.client})")
        raise HTTPException(status_code=401, detail="API Key 无效")

    return True
