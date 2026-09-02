"""
论坛引擎 — 轻量级社区论坛

支持:
- 版块管理 (Category/Board)
- 帖子发布与回复 (Thread/Post)
- 帖子置顶/精华/锁定
- 标签分类
- 搜索

用法:
    forum = ForumEngine()
    thread = forum.create_thread(
        board_id="general",
        author_id="user_001",
        title="新书求点评",
        content="请大家看看我的新书开头...",
    )
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ThreadStatus(StrEnum):
    NORMAL = "normal"
    PINNED = "pinned"  # 置顶
    FEATURED = "featured"  # 精华
    LOCKED = "locked"  # 锁定
    HIDDEN = "hidden"  # 隐藏


@dataclass
class ForumPost:
    """论坛帖子（回复）"""

    id: str = ""
    thread_id: str = ""
    author_id: str = ""
    content: str = ""
    created_at: float = field(default_factory=time.time)
    edited_at: float = 0.0
    like_count: int = 0
    deleted: bool = False


@dataclass
class ForumThread:
    """论坛主题"""

    id: str = ""
    board_id: str = ""
    author_id: str = ""
    title: str = ""
    content: str = ""
    status: ThreadStatus = ThreadStatus.NORMAL
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    view_count: int = 0
    reply_count: int = 0
    like_count: int = 0
    last_reply_at: float = 0.0
    last_reply_by: str = ""


@dataclass
class ForumBoard:
    """论坛版块"""

    id: str = ""
    name: str = ""
    description: str = ""
    sort_order: int = 0
    thread_count: int = 0
    post_count: int = 0


class ForumEngine:
    """论坛引擎

    管理版块、主题、帖子，提供论坛核心功能。

    用法:
        forum = ForumEngine()
        forum.create_board("general", "综合讨论", "写作交流综合版块")
        thread = forum.create_thread("general", "user_001", "标题", "内容")
    """

    def __init__(self):
        self._boards: dict[str, ForumBoard] = {}
        self._threads: dict[str, ForumThread] = {}
        self._posts: dict[str, list[ForumPost]] = {}  # thread_id -> posts

        # 创建默认版块
        self._setup_default_boards()

    def _setup_default_boards(self) -> None:
        """创建默认版块"""
        defaults = [
            ("general", "综合讨论", "写作交流、创作心得、行业动态"),
            ("writing", "创作交流", "大纲设计、角色塑造、情节构思"),
            ("review", "作品点评", "求评、互评、专业点评"),
            ("tech", "技术讨论", "AI 工具使用、模型调试、插件开发"),
            ("market", "市场推广", "签约经验、推广策略、平台分析"),
            ("offtopic", "灌水区", "闲聊、八卦、日常"),
        ]
        for i, (bid, name, desc) in enumerate(defaults):
            self._boards[bid] = ForumBoard(
                id=bid,
                name=name,
                description=desc,
                sort_order=i,
            )

    def create_board(self, board_id: str, name: str, description: str = "") -> ForumBoard:
        """创建版块"""
        board = ForumBoard(
            id=board_id,
            name=name,
            description=description,
            sort_order=len(self._boards),
        )
        self._boards[board_id] = board
        return board

    def get_board(self, board_id: str) -> ForumBoard | None:
        return self._boards.get(board_id)

    def list_boards(self) -> list[ForumBoard]:
        return sorted(self._boards.values(), key=lambda b: b.sort_order)

    def create_thread(
        self,
        board_id: str,
        author_id: str,
        title: str,
        content: str,
        tags: list[str] | None = None,
    ) -> ForumThread | None:
        """创建主题"""
        board = self._boards.get(board_id)
        if not board:
            return None

        import uuid

        thread = ForumThread(
            id=str(uuid.uuid4())[:12],
            board_id=board_id,
            author_id=author_id,
            title=title,
            content=content,
            tags=tags or [],
        )
        self._threads[thread.id] = thread
        self._posts[thread.id] = []

        board.thread_count += 1
        return thread

    def get_thread(self, thread_id: str) -> ForumThread | None:
        return self._threads.get(thread_id)

    def list_threads(
        self,
        board_id: str = "",
        status: ThreadStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ForumThread]:
        """列出主题"""
        threads = list(self._threads.values())
        if board_id:
            threads = [t for t in threads if t.board_id == board_id]
        if status:
            threads = [t for t in threads if t.status == status]
        # 置顶优先，然后按最后回复时间排序
        threads.sort(
            key=lambda t: (
                0 if t.status == ThreadStatus.PINNED else 1,
                -(t.last_reply_at or t.created_at),
            )
        )
        return threads[offset : offset + limit]

    def reply_thread(
        self,
        thread_id: str,
        author_id: str,
        content: str,
    ) -> ForumPost | None:
        """回复主题"""
        thread = self._threads.get(thread_id)
        if not thread:
            return None
        if thread.status == ThreadStatus.LOCKED:
            return None

        import uuid

        post = ForumPost(
            id=str(uuid.uuid4())[:12],
            thread_id=thread_id,
            author_id=author_id,
            content=content,
        )

        self._posts.setdefault(thread_id, []).append(post)
        thread.reply_count += 1
        thread.last_reply_at = time.time()
        thread.last_reply_by = author_id
        thread.updated_at = time.time()

        board = self._boards.get(thread.board_id)
        if board:
            board.post_count += 1

        return post

    def get_posts(self, thread_id: str, limit: int = 100) -> list[ForumPost]:
        """获取主题的所有回复"""
        posts = self._posts.get(thread_id, [])
        return posts[-limit:] if limit > 0 else posts

    def set_thread_status(self, thread_id: str, status: ThreadStatus) -> bool:
        """设置主题状态"""
        thread = self._threads.get(thread_id)
        if not thread:
            return False
        thread.status = status
        return True

    def like_thread(self, thread_id: str) -> bool:
        """点赞主题"""
        thread = self._threads.get(thread_id)
        if not thread:
            return False
        thread.like_count += 1
        return True

    def increment_view(self, thread_id: str) -> None:
        """增加浏览量"""
        thread = self._threads.get(thread_id)
        if thread:
            thread.view_count += 1

    def search_threads(self, query: str, limit: int = 20) -> list[ForumThread]:
        """搜索主题"""
        query_lower = query.lower()
        results = [
            t
            for t in self._threads.values()
            if query_lower in t.title.lower()
            or query_lower in t.content.lower()
            or any(query_lower in tag.lower() for tag in t.tags)
        ]
        results.sort(key=lambda t: -t.created_at)
        return results[:limit]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_boards": len(self._boards),
            "total_threads": len(self._threads),
            "total_posts": sum(len(p) for p in self._posts.values()),
            "boards": [
                {
                    "id": b.id,
                    "name": b.name,
                    "thread_count": b.thread_count,
                    "post_count": b.post_count,
                }
                for b in self._boards.values()
            ],
        }
