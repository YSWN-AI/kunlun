"""
昆仑创作引擎 — 书架作品管理 服务层

提供书籍列表扫描、分组管理、回收站、快速操作等功能。
书籍信息从 data/books/ 目录扫描获取，分组和回收站数据存储在 data/bookshelf/。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from kunlun.bookshelf.models import BookCard, GroupInfo, QuickActions


def _get_books_dir() -> Path:
    """获取书籍数据目录。"""
    from kunlun.config import settings

    return settings.DATA_DIR / "books"


def _get_bookshelf_dir() -> Path:
    """获取书架管理数据目录，不存在则创建。"""
    from kunlun.config import settings

    d = settings.DATA_DIR / "bookshelf"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_groups_file() -> Path:
    """获取分组数据文件路径。"""
    return _get_bookshelf_dir() / "groups.json"


def _get_recycle_file() -> Path:
    """获取回收站数据文件路径。"""
    return _get_bookshelf_dir() / "recycle.json"


def _load_json(path: Path, default: Any) -> Any:
    """安全加载JSON文件。"""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def _save_json(path: Path, data: Any) -> None:
    """安全保存JSON文件。"""
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_groups() -> dict[str, dict[str, Any]]:
    """加载分组数据。返回 {group_id: {name, created_at, books: [book_id]}}。"""
    data = _load_json(_get_groups_file(), {})
    if not isinstance(data, dict):
        data = {}
    # 确保默认分组存在
    if "default" not in data:
        data["default"] = {
            "name": "全部作品",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "books": [],
        }
    return data


def _save_groups(groups: dict[str, dict[str, Any]]) -> None:
    """保存分组数据。"""
    _save_json(_get_groups_file(), groups)


def _load_recycle() -> dict[str, dict[str, Any]]:
    """加载回收站数据。返回 {book_id: {deleted_at, reason}}。"""
    data = _load_json(_get_recycle_file(), {})
    if not isinstance(data, dict):
        data = {}
    return data


def _save_recycle(recycle: dict[str, dict[str, Any]]) -> None:
    """保存回收站数据。"""
    _save_json(_get_recycle_file(), recycle)


def _count_chapters(book_dir: Path) -> int:
    """统计书籍目录中的章节文件数量。"""
    count = sum(1 for _ in book_dir.glob("ch*.md"))
    chapters_dir = book_dir / "chapters"
    if chapters_dir.is_dir():
        count += sum(1 for _ in chapters_dir.glob("ch*.md"))
    published_dir = book_dir / "published"
    if published_dir.is_dir():
        count += sum(1 for _ in published_dir.glob("ch*.txt"))
    return count


def _count_words(book_dir: Path) -> int:
    """统计书籍总字数（从章节文件中读取）。"""
    total = 0
    for f in list(book_dir.glob("ch*.md")) + list(book_dir.glob("ch*.txt")):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            total += len(content)
        except Exception:
            continue
    chapters_dir = book_dir / "chapters"
    if chapters_dir.is_dir():
        for f in chapters_dir.glob("ch*.md"):
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                total += len(content)
            except Exception:
                continue
    return total


def _scan_book(book_dir: Path) -> BookCard | None:
    """扫描单个书籍目录，提取书籍信息。"""
    book_id = book_dir.name
    if not book_id.startswith("book_"):
        return None

    # 尝试读取 project.json
    project_file = book_dir / "project.json"
    project_data: dict[str, Any] = {}
    if project_file.exists():
        try:
            project_data = json.loads(project_file.read_text(encoding="utf-8"))
        except Exception:
            project_data = {}

    # 从目录名提取标题（book_xxx_1234 -> xxx）
    title = project_data.get("title", "")
    if not title:
        # 从目录名解析：book_标题_数字
        parts = book_id[5:].rsplit("_", 1)
        title = parts[0] if parts else book_id
        if not title or title == "未命名":
            title = "未命名作品"

    # 统计章节和字数
    chapter_count = project_data.get("total_chapters", 0)
    if not chapter_count:
        chapter_count = _count_chapters(book_dir)

    word_count = project_data.get("total_words", 0)
    if not word_count:
        word_count = _count_words(book_dir)

    # 计算进度
    target_chapters = project_data.get("target_chapters", 100)
    current_chapter = project_data.get("current_chapter", 0)
    progress = 0.0
    if target_chapters > 0:
        progress = round(min(current_chapter / target_chapters * 100, 100.0), 1)

    # 获取最后修改时间
    last_modified = ""
    try:
        mtime = book_dir.stat().st_mtime
        last_modified = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass

    # 检查封面
    cover = ""
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        cover_file = book_dir / f"cover{ext}"
        if cover_file.exists():
            cover = str(cover_file)
            break

    return BookCard(
        id=book_id,
        title=title,
        cover=cover,
        genre=project_data.get("genre", ""),
        word_count=word_count,
        progress=progress,
        last_modified=last_modified,
        group="default",
        tags=[],
        status=project_data.get("status", "创作中"),
        chapter_count=chapter_count,
        target_chapters=target_chapters,
        current_chapter=current_chapter,
        quality_score=project_data.get("quality_score", 0.0),
        outline_ready=project_data.get("outline_ready", False),
        world_ready=project_data.get("world_ready", False),
        characters_ready=project_data.get("characters_ready", False),
        in_recycle=False,
    )


def _apply_group_and_recycle(books: list[BookCard]) -> list[BookCard]:
    """为书籍列表应用分组和回收站状态。"""
    groups = _load_groups()
    recycle = _load_recycle()

    # 建立 book_id -> group_id 映射
    book_group_map: dict[str, str] = {}
    for gid, gdata in groups.items():
        for bid in gdata.get("books", []):
            book_group_map[bid] = gid

    result: list[BookCard] = []
    for book in books:
        book.group = book_group_map.get(book.id, "default")
        book.in_recycle = book.id in recycle
        result.append(book)
    return result


def list_books(
    group: str | None = None,
    sort_by: str | None = None,
    search: str | None = None,
    include_recycle: bool = False,
) -> list[BookCard]:
    """
    获取书架书籍列表。

    Args:
        group: 分组ID筛选，None表示全部
        sort_by: 排序字段（last_modified/word_count/progress/title），默认last_modified
        search: 关键词搜索（标题/题材）
        include_recycle: 是否包含回收站中的书籍
    """
    books_dir = _get_books_dir()
    books: list[BookCard] = []

    if books_dir.is_dir():
        for book_dir in books_dir.iterdir():
            if book_dir.is_dir() and book_dir.name.startswith("book_"):
                card = _scan_book(book_dir)
                if card is not None:
                    books.append(card)

    # 应用分组和回收站状态
    books = _apply_group_and_recycle(books)

    # 过滤回收站
    if not include_recycle:
        books = [b for b in books if not b.in_recycle]

    # 分组筛选
    if group and group != "all":
        books = [b for b in books if b.group == group]

    # 搜索筛选
    if search:
        keyword = search.lower()
        books = [b for b in books if keyword in b.title.lower() or keyword in b.genre.lower()]

    # 排序
    sort_field = sort_by or "last_modified"
    reverse = True  # 默认倒序
    if sort_field == "title":
        reverse = False
        books.sort(key=lambda b: b.title, reverse=reverse)
    elif sort_field == "word_count":
        books.sort(key=lambda b: b.word_count, reverse=reverse)
    elif sort_field == "progress":
        books.sort(key=lambda b: b.progress, reverse=reverse)
    else:  # last_modified
        books.sort(key=lambda b: b.last_modified, reverse=reverse)

    return books


def get_book(book_id: str) -> BookCard | None:
    """获取单本书籍详情。"""
    books_dir = _get_books_dir()
    book_dir = books_dir / book_id
    if not book_dir.is_dir():
        return None
    card = _scan_book(book_dir)
    if card is None:
        return None
    # 应用分组和回收站状态
    books = _apply_group_and_recycle([card])
    return books[0] if books else None


def create_group(name: str) -> str:
    """创建新分组，返回分组ID。"""
    groups = _load_groups()
    group_id = f"group_{uuid.uuid4().hex[:8]}"
    groups[group_id] = {
        "name": name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "books": [],
    }
    _save_groups(groups)
    return group_id


def list_groups() -> list[GroupInfo]:
    """获取所有分组列表（含书籍数量）。"""
    groups = _load_groups()
    books = list_books(include_recycle=True)

    # 统计每本书的分组
    book_group_count: dict[str, int] = {}
    for book in books:
        book_group_count[book.group] = book_group_count.get(book.group, 0) + 1

    result: list[GroupInfo] = []
    # 默认分组排第一
    if "default" in groups:
        g = groups["default"]
        result.append(
            GroupInfo(
                id="default",
                name=g.get("name", "全部作品"),
                book_count=book_group_count.get("default", 0),
                created_at=g.get("created_at", ""),
            )
        )
    # 其他分组
    for gid, gdata in groups.items():
        if gid == "default":
            continue
        result.append(
            GroupInfo(
                id=gid,
                name=gdata.get("name", ""),
                book_count=book_group_count.get(gid, 0),
                created_at=gdata.get("created_at", ""),
            )
        )
    return result


def move_to_group(book_id: str, group_id: str) -> bool:
    """移动书籍到指定分组。"""
    groups = _load_groups()
    if group_id != "default" and group_id not in groups:
        return False

    # 从所有分组中移除该书
    for gdata in groups.values():
        if book_id in gdata.get("books", []):
            gdata["books"].remove(book_id)

    # 添加到目标分组（默认分组不存储，空表示默认）
    if group_id != "default":
        groups[group_id].setdefault("books", []).append(book_id)

    _save_groups(groups)
    return True


def delete_group(group_id: str) -> bool:
    """删除分组。分组内的书籍移回默认分组。"""
    if group_id == "default":
        return False  # 不能删除默认分组
    groups = _load_groups()
    if group_id not in groups:
        return False
    # 分组内书籍移回默认（即从分组中移除）
    del groups[group_id]
    _save_groups(groups)
    return True


def get_recycle_bin() -> list[BookCard]:
    """获取回收站中的书籍列表。"""
    books = list_books(include_recycle=True)
    return [b for b in books if b.in_recycle]


def move_to_recycle(book_id: str) -> bool:
    """将书籍移到回收站。"""
    book = get_book(book_id)
    if book is None:
        return False
    recycle = _load_recycle()
    recycle[book_id] = {
        "deleted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reason": "用户删除",
    }
    _save_recycle(recycle)
    return True


def restore_from_recycle(book_id: str) -> bool:
    """从回收站恢复书籍。"""
    recycle = _load_recycle()
    if book_id not in recycle:
        return False
    del recycle[book_id]
    _save_recycle(recycle)
    return True


def permanently_delete(book_id: str) -> bool:
    """
    永久删除书籍（删除书籍目录）。

    注意：这是不可逆操作，会删除 data/books/book_id/ 整个目录。
    """
    books_dir = _get_books_dir()
    book_dir = books_dir / book_id
    if not book_dir.is_dir():
        return False

    # 从回收站移除记录
    recycle = _load_recycle()
    recycle.pop(book_id, None)
    _save_recycle(recycle)

    # 从分组中移除
    groups = _load_groups()
    for gdata in groups.values():
        if book_id in gdata.get("books", []):
            gdata["books"].remove(book_id)
    _save_groups(groups)

    # 删除目录
    import shutil

    shutil.rmtree(book_dir, ignore_errors=True)
    return True


def get_quick_actions(book_id: str) -> QuickActions | None:
    """获取书籍的快速操作信息。"""
    book = get_book(book_id)
    if book is None:
        return None

    # 继续写作信息
    next_chapter = book.current_chapter + 1 if book.current_chapter > 0 else 1
    continue_writing = {
        "available": True,
        "next_chapter": next_chapter,
        "current_progress": f"{book.current_chapter}/{book.target_chapters}章",
        "word_count": book.word_count,
    }

    # 查看大纲信息
    view_outline = {
        "available": book.outline_ready,
        "has_outline_file": _check_file_exists(book_id, "outline.json")
        or _check_file_exists(book_id, "大纲.md"),
    }

    # 质量报告信息
    quality_report = {
        "available": book.quality_score > 0,
        "score": book.quality_score,
        "has_report": _check_file_exists(book_id, "quality_report.json"),
    }

    # 导出信息
    export = {
        "available": book.chapter_count > 0,
        "formats": ["txt", "md", "epub"],
        "chapter_count": book.chapter_count,
    }

    return QuickActions(
        book_id=book_id,
        continue_writing=continue_writing,
        view_outline=view_outline,
        quality_report=quality_report,
        export=export,
    )


def _check_file_exists(book_id: str, filename: str) -> bool:
    """检查书籍目录中是否存在指定文件。"""
    books_dir = _get_books_dir()
    book_dir = books_dir / book_id
    if not book_dir.is_dir():
        return False
    # 检查根目录
    if (book_dir / filename).exists():
        return True
    # 检查子目录
    return any(sub.is_dir() and (sub / filename).exists() for sub in book_dir.iterdir())
