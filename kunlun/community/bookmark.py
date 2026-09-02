"""
书签/收藏/阅读进度 — 读者阅读管理

支持:
- 书签 (Bookmark) — 收藏书籍
- 阅读进度 (ReadingProgress) — 跨设备进度同步
- 阅读历史 (ReadingHistory) — 最近阅读
- 书架 (Bookshelf) — 分类管理

用法:
    bm = BookmarkManager()
    bm.add_bookmark("user_001", "book_001", shelf="追更中")
    bm.update_progress("user_001", "book_001", chapter_num=42, position=0.5)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ShelfCategory(StrEnum):
    """书架分类"""

    READING = "reading"  # 追更中
    COMPLETED = "completed"  # 已完结
    PLAN_TO_READ = "plan"  # 想看
    DROPPED = "dropped"  # 弃坑
    FAVORITE = "favorite"  # 收藏


@dataclass
class Bookmark:
    """书签/收藏"""

    user_id: str = ""
    book_id: str = ""
    shelf: ShelfCategory = ShelfCategory.READING
    added_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    notes: str = ""
    is_private: bool = False


@dataclass
class ReadingProgress:
    """阅读进度"""

    user_id: str = ""
    book_id: str = ""
    chapter_num: int = 0
    position: float = 0.0  # 章节内进度 (0.0-1.0)
    total_chapters: int = 0
    updated_at: float = field(default_factory=time.time)
    device: str = ""  # 设备标识


@dataclass
class ReadingHistory:
    """阅读历史"""

    user_id: str = ""
    book_id: str = ""
    chapter_num: int = 0
    read_at: float = field(default_factory=time.time)
    duration_seconds: float = 0.0  # 阅读时长


class BookmarkManager:
    """书签管理

    管理用户书架、阅读进度、阅读历史。

    用法:
        bm = BookmarkManager()
        bm.add_bookmark("user_001", "book_001")
        bm.update_progress("user_001", "book_001", 42, 0.5)
        shelf = bm.get_shelf("user_001")
    """

    def __init__(self):
        self._bookmarks: dict[str, dict[str, Bookmark]] = {}  # user_id -> {book_id: Bookmark}
        self._progress: dict[str, dict[str, ReadingProgress]] = {}  # user_id -> {book_id: progress}
        self._history: dict[str, list[ReadingHistory]] = {}  # user_id -> [history]
        self._max_history: int = 100

    def add_bookmark(
        self,
        user_id: str,
        book_id: str,
        shelf: ShelfCategory = ShelfCategory.READING,
        notes: str = "",
        is_private: bool = False,
    ) -> Bookmark:
        """添加书签"""
        bookmark = Bookmark(
            user_id=user_id,
            book_id=book_id,
            shelf=shelf,
            notes=notes,
            is_private=is_private,
        )
        self._bookmarks.setdefault(user_id, {})[book_id] = bookmark
        return bookmark

    def remove_bookmark(self, user_id: str, book_id: str) -> bool:
        """移除书签"""
        user_bookmarks = self._bookmarks.get(user_id, {})
        return user_bookmarks.pop(book_id, None) is not None

    def get_bookmark(self, user_id: str, book_id: str) -> Bookmark | None:
        return self._bookmarks.get(user_id, {}).get(book_id)

    def update_shelf(
        self,
        user_id: str,
        book_id: str,
        shelf: ShelfCategory,
    ) -> bool:
        """更新书架分类"""
        bookmark = self.get_bookmark(user_id, book_id)
        if not bookmark:
            return False
        bookmark.shelf = shelf
        bookmark.updated_at = time.time()
        return True

    def get_shelf(
        self,
        user_id: str,
        shelf: ShelfCategory | None = None,
    ) -> list[Bookmark]:
        """获取书架"""
        bookmarks = list(self._bookmarks.get(user_id, {}).values())
        if shelf:
            bookmarks = [b for b in bookmarks if b.shelf == shelf]
        return sorted(bookmarks, key=lambda b: -b.updated_at)

    def get_shelf_stats(self, user_id: str) -> dict[str, int]:
        """获取书架统计"""
        bookmarks = self._bookmarks.get(user_id, {}).values()
        stats: dict[str, int] = {}
        for b in bookmarks:
            stats[b.shelf.value] = stats.get(b.shelf.value, 0) + 1
        return stats

    def update_progress(
        self,
        user_id: str,
        book_id: str,
        chapter_num: int,
        position: float = 0.0,
        total_chapters: int = 0,
        device: str = "",
    ) -> ReadingProgress:
        """更新阅读进度"""
        progress = ReadingProgress(
            user_id=user_id,
            book_id=book_id,
            chapter_num=chapter_num,
            position=position,
            total_chapters=total_chapters,
            device=device,
        )
        self._progress.setdefault(user_id, {})[book_id] = progress
        return progress

    def get_progress(self, user_id: str, book_id: str) -> ReadingProgress | None:
        return self._progress.get(user_id, {}).get(book_id)

    def get_all_progress(self, user_id: str) -> list[ReadingProgress]:
        """获取所有阅读进度"""
        return list(self._progress.get(user_id, {}).values())

    def add_history(
        self,
        user_id: str,
        book_id: str,
        chapter_num: int,
        duration_seconds: float = 0.0,
    ) -> ReadingHistory:
        """添加阅读历史"""
        history = ReadingHistory(
            user_id=user_id,
            book_id=book_id,
            chapter_num=chapter_num,
            duration_seconds=duration_seconds,
        )
        self._history.setdefault(user_id, []).append(history)
        # 限制历史记录数量
        if len(self._history[user_id]) > self._max_history:
            self._history[user_id] = self._history[user_id][-self._max_history :]
        return history

    def get_history(
        self,
        user_id: str,
        limit: int = 50,
    ) -> list[ReadingHistory]:
        """获取阅读历史"""
        history = self._history.get(user_id, [])
        return list(reversed(history))[:limit]

    def get_recently_read(self, user_id: str, limit: int = 10) -> list[str]:
        """获取最近阅读的书"""
        history = self._history.get(user_id, [])
        seen: set[str] = set()
        recent: list[str] = []
        for h in reversed(history):
            if h.book_id not in seen:
                seen.add(h.book_id)
                recent.append(h.book_id)
            if len(recent) >= limit:
                break
        return recent

    def get_reading_stats(self, user_id: str) -> dict[str, Any]:
        """获取阅读统计"""
        history = self._history.get(user_id, [])
        total_duration = sum(h.duration_seconds for h in history)
        return {
            "total_books_read": len({h.book_id for h in history}),
            "total_chapters_read": len(history),
            "total_reading_time_seconds": total_duration,
            "total_reading_time_hours": round(total_duration / 3600, 1),
            "recent_books": self.get_recently_read(user_id, 5),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_users": len(self._bookmarks),
            "total_bookmarks": sum(len(v) for v in self._bookmarks.values()),
            "total_history": sum(len(v) for v in self._history.values()),
        }
