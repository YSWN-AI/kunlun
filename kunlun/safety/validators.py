"""
昆仑创作引擎 — 参数校验器

提供统一的输入校验，防止路径穿越、注入等安全风险。
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import HTTPException, Request

from kunlun.config import settings

# book_id 仅允许字母、数字、下划线、短横线，长度 1-64
_BOOK_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


def validate_book_id(book_id: str) -> str:
    """校验 book_id 格式，防止路径穿越和其他注入。

    Args:
        book_id: 待校验的书籍 ID

    Returns:
        校验通过的 book_id（原样返回）

    Raises:
        ValueError: book_id 格式不合法
    """
    if not book_id or not _BOOK_ID_PATTERN.match(book_id):
        raise ValueError(
            f"book_id 格式不合法: '{book_id}'。仅允许字母、数字、下划线和短横线，长度 1-64 字符。"
        )
    # 额外安全检查：防止特殊路径模式
    if book_id in (".", "..") or book_id.startswith("."):
        raise ValueError(f"book_id 不允许以 '.' 开头: '{book_id}'")
    return book_id


def get_book_safe_path(book_id: str, *subdirs: str) -> Path:
    """创建安全的书籍目录路径，自动校验 book_id 并防止路径穿越。

    Args:
        book_id: 已校验的书籍 ID
        *subdirs: 子目录名（仅允许通过 _SANITIZE_SUBDIR 的目录名）

    Returns:
        Path 对象，指向 safe_path = DATA_DIR / subdirs / book_id

    Raises:
        ValueError: book_id 或子目录名不合法
    """
    book_id = validate_book_id(book_id)
    p = settings.DATA_DIR.joinpath(*subdirs, book_id).resolve()
    data_root = settings.DATA_DIR.resolve()
    if not str(p).startswith(str(data_root)):
        raise ValueError(f"路径穿越检测: 路径 '{p}' 不在数据目录 '{data_root}' 内")
    return p


# ─── FastAPI 依赖：从路径参数中提取并校验 book_id ───


async def require_valid_book_id(request: Request) -> str:
    """FastAPI 依赖：从路径参数中提取 book_id 并进行安全校验。

    用法:
        @router.get("/books/{book_id}")
        async def get_book(book_id: str = Depends(require_valid_book_id)):
            ...
    """
    book_id = request.path_params.get("book_id", "")
    try:
        return validate_book_id(book_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
