"""
昆仑创作引擎 —— 导出路由
/books/{book_id}/chapters/{chapter}/export, /books/{book_id}/export

支持 7 种格式: txt / epub / mobi / pdf / html / docx / md / submission
"""

from fastapi import APIRouter, HTTPException, Query, Request

from kunlun.api.rate_limit import get_limiter
from kunlun.config import settings
from kunlun.exporter.engine import ExportFormat, ExportLayout, exporter

router = APIRouter(tags=["导出"])
_limiter = get_limiter()
_export_rate_limit = (
    _limiter.limit(f"{settings.rate_limit_export_per_minute}/minute") if _limiter else lambda f: f
)


def _validate_book_id(book_id: str) -> None:
    """校验 book_id 格式，无效时抛 400"""
    try:
        settings.get_book_safe_path(book_id, "export")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# 支持的导出格式列表
_SUPPORTED_FORMATS = [
    ExportFormat.TXT.value,
    ExportFormat.EPUB.value,
    ExportFormat.MOBI.value,
    ExportFormat.PDF.value,
    ExportFormat.HTML.value,
    ExportFormat.DOCX.value,
    ExportFormat.MARKDOWN.value,
    ExportFormat.SUBMISSION.value,
]

# 无需额外依赖的格式
_NO_DEPS_FORMATS = {ExportFormat.TXT, ExportFormat.HTML, ExportFormat.MARKDOWN}


@router.get("/export/dependencies", summary="检测导出依赖")
async def check_dependencies() -> dict:
    """检测各导出格式的依赖是否就绪。

    Returns:
        {"epub": true/false, "pdf": true/false, "docx": true/false, "mobi": true/false}
    """
    return {"success": True, "dependencies": exporter.check_dependencies()}


@router.get("/export/formats", summary="列出支持的导出格式")
async def list_formats() -> dict:
    """列出所有支持的导出格式及依赖状态。"""
    deps = exporter.check_dependencies()
    formats = []
    for fv in _SUPPORTED_FORMATS:
        fmt = ExportFormat(fv)
        info = {
            "value": fv,
            "label": _format_label(fv),
            "available": fmt in _NO_DEPS_FORMATS or deps.get(fv, False),
            "needs_deps": fmt not in _NO_DEPS_FORMATS,
        }
        if fmt == ExportFormat.MOBI:
            info["available"] = deps.get("mobi", False)
        formats.append(info)
    return {"success": True, "formats": formats}


@router.get("/books/{book_id}/chapters/{chapter}/export", summary="导出单章")
@_export_rate_limit
async def export_chapter(
    book_id: str,
    chapter: int,
    request: Request = None,
    format: str = Query(default="txt", description=f"导出格式 ({'/'.join(_SUPPORTED_FORMATS)})"),
    layout: str = Query(default="standard", description="排版风格 (standard/compact/beautiful)"),
) -> dict:
    _validate_book_id(book_id)

    if format not in _SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的格式 '{format}'。支持: {', '.join(_SUPPORTED_FORMATS)}",
        )

    fmt = ExportFormat(format)
    if fmt == ExportFormat.SUBMISSION:
        raise HTTPException(status_code=400, detail="投稿包仅支持全书导出")

    try:
        layout_enum = ExportLayout(layout)
    except ValueError:
        layout_enum = ExportLayout.STANDARD

    result = exporter.export_chapter(book_id, chapter, fmt, layout_enum)

    if not result.success:
        status = 400 if result.missing_deps else 404
        error_detail = result.error
        if result.missing_deps:
            error_detail += "。安装命令: pip install -r requirements-export.txt"
        raise HTTPException(status_code=status, detail=error_detail)

    return {
        "success": True,
        "format": result.format,
        "path": result.path,
        "word_count": result.total_words,
    }


@router.get("/books/{book_id}/export", summary="导出全书")
@_export_rate_limit
async def export_book(
    book_id: str,
    request: Request = None,
    format: str = Query(default="txt", description=f"导出格式 ({'/'.join(_SUPPORTED_FORMATS)})"),
    _scope: str = Query(default="all", description="导出范围 (all/chapters)"),
    layout: str = Query(default="standard", description="排版风格 (standard/compact/beautiful)"),
) -> dict:
    _validate_book_id(book_id)

    if format not in _SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的格式 '{format}'。支持: {', '.join(_SUPPORTED_FORMATS)}",
        )

    fmt = ExportFormat(format)

    # 投稿包走特殊路径
    if fmt == ExportFormat.SUBMISSION:
        result = exporter.export_submission(book_id)
        if not result.success:
            raise HTTPException(status_code=404, detail=result.error)
        return {
            "success": True,
            "format": "submission",
            "path": result.path,
            "file_path": result.path,
            "chapters": result.chapters,
            "total_words": result.total_words,
        }

    try:
        layout_enum = ExportLayout(layout)
    except ValueError:
        layout_enum = ExportLayout.STANDARD

    result = exporter.export_book(book_id, fmt, layout_enum)

    if not result.success:
        status = 400 if result.missing_deps else 404
        error_detail = result.error
        if result.missing_deps:
            error_detail += "。安装命令: pip install -r requirements-export.txt"
        raise HTTPException(status_code=status, detail=error_detail)

    return {
        "success": True,
        "format": result.format,
        "path": result.path,
        "chapters": result.chapters,
        "total_words": result.total_words,
    }


def _format_label(fv: str) -> str:
    """格式值 → 中文标签"""
    labels = {
        "txt": "纯文本 (.txt)",
        "epub": "EPUB 电子书 (.epub)",
        "mobi": "MOBI 电子书 (.mobi)",
        "pdf": "PDF (.pdf)",
        "html": "HTML (.html)",
        "docx": "Word 文档 (.docx)",
        "md": "Markdown (.md)",
        "submission": "投稿包 (.zip)",
    }
    return labels.get(fv, fv)
