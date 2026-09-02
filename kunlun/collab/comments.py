"""
评论系统 — 协作写作的评论/批注管理

支持:
- 行内评论 (inline comments)
- 批注 (annotations, 关联文本范围)
- 评论线程 (threaded discussions)
- 评论状态 (open/resolved/reopened)
- 回复嵌套

用法:
    cs = CommentSystem()
    thread = cs.create_thread(
        doc_id="chapter_42",
        author_id="user_001",
        content="这段对话可以再丰富一些",
        range_start=42,
        range_end=56,
    )
    cs.reply(thread.id, author_id="user_002", content="好建议，我来改")
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CommentStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    REOPENED = "reopened"


@dataclass
class Comment:
    """单条评论"""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    author_id: str = ""
    content: str = ""
    created_at: float = field(default_factory=time.time)
    edited_at: float = 0.0
    deleted: bool = False

    def edit(self, new_content: str) -> None:
        self.content = new_content
        self.edited_at = time.time()

    def soft_delete(self) -> None:
        self.deleted = True
        self.content = "[已删除]"


@dataclass
class CommentThread:
    """评论线程 — 包含主评论和所有回复"""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    doc_id: str = ""
    author_id: str = ""
    content: str = ""
    status: CommentStatus = CommentStatus.OPEN
    created_at: float = field(default_factory=time.time)
    resolved_at: float = 0.0
    resolved_by: str = ""

    # 文本范围关联（批注模式）
    range_start: int = 0
    range_end: int = 0
    range_text: str = ""

    # 回复列表
    replies: list[Comment] = field(default_factory=list)

    @property
    def reply_count(self) -> int:
        return len([r for r in self.replies if not r.deleted])

    def add_reply(self, comment: Comment) -> None:
        self.replies.append(comment)

    def resolve(self, user_id: str) -> None:
        self.status = CommentStatus.RESOLVED
        self.resolved_at = time.time()
        self.resolved_by = user_id

    def reopen(self) -> None:
        self.status = CommentStatus.REOPENED
        self.resolved_at = 0.0
        self.resolved_by = ""


class CommentSystem:
    """评论系统管理器

    管理多个文档的评论线程，提供评论 CRUD 和查询接口。

    用法:
        cs = CommentSystem()
        thread = cs.create_thread("doc_001", "user_001", "需要修改")
        cs.reply(thread.id, "user_002", "已修改")
        cs.resolve(thread.id, "user_001")
    """

    def __init__(self):
        self._threads: dict[str, CommentThread] = {}
        self._doc_index: dict[str, list[str]] = {}  # doc_id -> thread_ids

    def create_thread(
        self,
        doc_id: str,
        author_id: str,
        content: str,
        range_start: int = 0,
        range_end: int = 0,
        range_text: str = "",
    ) -> CommentThread:
        """创建评论线程"""
        thread = CommentThread(
            doc_id=doc_id,
            author_id=author_id,
            content=content,
            range_start=range_start,
            range_end=range_end,
            range_text=range_text,
        )
        self._threads[thread.id] = thread
        self._doc_index.setdefault(doc_id, []).append(thread.id)
        return thread

    def reply(self, thread_id: str, author_id: str, content: str) -> Comment | None:
        """回复评论线程"""
        thread = self._threads.get(thread_id)
        if not thread:
            return None
        comment = Comment(author_id=author_id, content=content)
        thread.add_reply(comment)
        return comment

    def resolve(self, thread_id: str, user_id: str) -> bool:
        """标记评论为已解决"""
        thread = self._threads.get(thread_id)
        if not thread:
            return False
        thread.resolve(user_id)
        return True

    def reopen(self, thread_id: str) -> bool:
        """重新打开评论"""
        thread = self._threads.get(thread_id)
        if not thread:
            return False
        thread.reopen()
        return True

    def get_thread(self, thread_id: str) -> CommentThread | None:
        return self._threads.get(thread_id)

    def get_doc_threads(
        self,
        doc_id: str,
        status: CommentStatus | None = None,
    ) -> list[CommentThread]:
        """获取文档的所有评论线程"""
        thread_ids = self._doc_index.get(doc_id, [])
        threads = [self._threads[tid] for tid in thread_ids if tid in self._threads]
        if status:
            threads = [t for t in threads if t.status == status]
        return sorted(threads, key=lambda t: t.created_at)

    def get_thread_stats(self, doc_id: str) -> dict[str, Any]:
        """获取文档评论统计"""
        threads = self.get_doc_threads(doc_id)
        return {
            "total": len(threads),
            "open": sum(1 for t in threads if t.status == CommentStatus.OPEN),
            "resolved": sum(1 for t in threads if t.status == CommentStatus.RESOLVED),
            "reopened": sum(1 for t in threads if t.status == CommentStatus.REOPENED),
            "total_replies": sum(t.reply_count for t in threads),
        }

    def delete_thread(self, thread_id: str) -> bool:
        """删除评论线程"""
        thread = self._threads.pop(thread_id, None)
        if thread and thread.doc_id in self._doc_index:
            self._doc_index[thread.doc_id] = [
                tid for tid in self._doc_index[thread.doc_id] if tid != thread_id
            ]
        return thread is not None
