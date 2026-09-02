"""
统一安全中间件
提供输入校验、路径穿越防护、敏感信息脱敏等功能。

基于 500 开源项目调研 — 三层拦截模式：
1. 输入层：参数校验 + 路径安全
2. 处理层：异常分类 + 统一响应
3. 输出层：敏感信息脱敏
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger

# ── 输入校验 ────────────────────────────────────────────

# 危险路径模式
UNSAFE_PATH_PATTERNS = [
    r"\.\.",  # 路径穿越
    r"~",  # 用户目录
    r"\x00",  # null byte
    r"[<>:\"|?*]",  # Windows 非法字符
]

# 危险 SQL/Cypher 注入模式
SQL_INJECTION_PATTERNS = [
    r"(?i)\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b",
    r"(?i)\b(UNION|EXEC|EXECUTE|CALL)\b",
    r"--",  # SQL 注释
    r";",  # 多语句分隔
]

# book_id 安全模式
BOOK_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")

# 章节号范围
CHAPTER_RANGE = (1, 100000)


def validate_book_id(book_id: str) -> str:
    """校验 book_id 安全性"""
    if not book_id or not book_id.strip():
        raise HTTPException(status_code=400, detail="book_id 不能为空")
    if not BOOK_ID_PATTERN.match(book_id):
        raise HTTPException(status_code=400, detail=f"无效 book_id: {book_id}")
    if len(book_id) > 128:
        raise HTTPException(status_code=400, detail="book_id 过长（最大128字符）")
    return book_id.strip()


def validate_chapter_number(chapter: int | str) -> int:
    """校验章节号"""
    try:
        ch = int(chapter)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"无效章节号: {chapter}") from None
    if not (CHAPTER_RANGE[0] <= ch <= CHAPTER_RANGE[1]):
        raise HTTPException(status_code=400, detail=f"章节号超出范围: {CHAPTER_RANGE}")
    return ch


def validate_safe_path(user_path: str, base_dir: Path) -> Path:
    """校验路径安全，防止路径穿越攻击"""
    try:
        resolved = (base_dir / user_path).resolve()
        if not str(resolved).startswith(str(base_dir.resolve())):
            raise HTTPException(status_code=403, detail="路径穿越攻击被阻止")
        return resolved
    except (ValueError, OSError) as e:
        raise HTTPException(status_code=400, detail=f"无效路径: {e}") from e


def sanitize_input(value: str, max_length: int = 1000) -> str:
    """输入清洗"""
    if not isinstance(value, str):
        return value
    # 截断过长输入
    if len(value) > max_length:
        value = value[:max_length]
    # 移除 null 字节
    value = value.replace("\x00", "")
    return value.strip()


def check_injection(value: str, context: str = "") -> None:
    """检查 SQL/Cypher 注入"""
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, value):
            logger.warning(f"[安全] 检测到注入尝试 [{context}]: {value[:100]}")
            raise HTTPException(status_code=403, detail="检测到潜在注入攻击")


# ── 敏感信息脱敏 ──────────────────────────────────────────

SENSITIVE_KEYS = {
    "api_key",
    "api_secret",
    "password",
    "token",
    "secret",
    "authorization",
    "auth",
    "credential",
    "private_key",
}


def mask_sensitive_data(data: dict[str, Any], max_depth: int = 3) -> dict[str, Any]:
    """递归脱敏敏感字段"""
    if max_depth <= 0:
        return {"__truncated__": True}

    result: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sk in key_lower for sk in SENSITIVE_KEYS):
            if isinstance(value, str) and len(value) > 8:
                result[key] = value[:4] + "****" + value[-4:]
            else:
                result[key] = "****"
        elif isinstance(value, dict):
            result[key] = mask_sensitive_data(value, max_depth - 1)
        elif isinstance(value, list):
            result[key] = [
                mask_sensitive_data(v, max_depth - 1) if isinstance(v, dict) else v
                for v in value[:10]  # 限制列表长度
            ]
        else:
            result[key] = value
    return result


# ── 统一异常响应 ──────────────────────────────────────────


def error_response(status_code: int, detail: str, error_type: str = "") -> JSONResponse:
    """统一的错误响应格式"""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": status_code,
                "type": error_type or "unknown",
                "message": detail,
            },
        },
    )


# ── 请求日志脱敏 ──────────────────────────────────────────


async def log_request_safe(request: Request) -> dict:
    """安全地记录请求信息（脱敏后）"""
    headers = dict(request.headers)
    # 脱敏 Authorization
    if "authorization" in headers:
        headers["authorization"] = "Bearer ****"
    if "x-api-key" in headers:
        headers["x-api-key"] = "****"

    return {
        "method": request.method,
        "path": request.url.path,
        "client": request.client.host if request.client else "unknown",
    }
