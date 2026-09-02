"""
协作引擎 — 多人实时协作核心

管理协作会话、用户加入/离开、文档锁定、版本快照。

用法:
    engine = CollabEngine()

    # 创建协作会话
    session = engine.create_session(
        book_id="book_001",
        chapter_num=42,
        owner_id="user_001",
    )

    # 用户加入
    engine.join_session(session.id, user_id="user_002")

    # 锁定章节
    engine.lock_document(session.session_id, "user_001")

    # 保存版本
    engine.save_version(session.doc_id, content, "user_001")
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from kunlun.collab.comments import CommentSystem
from kunlun.collab.diff_engine import DiffEngine
from kunlun.collab.permissions import PermissionManager
from kunlun.collab.ws_handler import CollabWebSocketHandler

logger = logging.getLogger(__name__)

# ── 常量 ──
_MAX_USERS_PER_SESSION = 20
_SESSION_TIMEOUT_SECONDS = 3600  # 1 小时无活动后自动关闭


@dataclass
class CollabSession:
    """协作会话"""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    book_id: str = ""
    chapter_num: int = 0
    doc_id: str = ""
    owner_id: str = ""
    title: str = ""
    content: str = ""

    # 参与者
    participants: set[str] = field(default_factory=set)

    # 锁定
    locked_by: str = ""
    locked_at: float = 0.0

    # 时间
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    # 版本
    version_count: int = 0

    @property
    def is_locked(self) -> bool:
        return self.locked_by != ""

    @property
    def participant_count(self) -> int:
        return len(self.participants)

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.last_active) > _SESSION_TIMEOUT_SECONDS

    def touch(self) -> None:
        self.last_active = time.time()


class CollabEngine:
    """协作引擎

    核心职责:
    - 会话生命周期管理（创建/加入/离开/关闭）
    - 文档锁定管理
    - 版本快照自动保存
    - 权限集成
    - 评论系统集成

    用法:
        from kunlun.collab import CollabEngine

        engine = CollabEngine()
        session = engine.create_session("book_001", 42, "user_001")
    """

    def __init__(self):
        self._sessions: dict[str, CollabSession] = {}
        self._permissions = PermissionManager()
        self._comments = CommentSystem()
        self._diff = DiffEngine()
        self._ws_handler = CollabWebSocketHandler(self)

    # ── 属性 ──
    @property
    def permissions(self) -> PermissionManager:
        return self._permissions

    @property
    def comments(self) -> CommentSystem:
        return self._comments

    @property
    def diff_engine(self) -> DiffEngine:
        return self._diff

    @property
    def ws_handler(self) -> CollabWebSocketHandler:
        return self._ws_handler

    # ── 会话管理 ──

    def create_session(
        self,
        book_id: str,
        chapter_num: int,
        owner_id: str,
        content: str = "",
        title: str = "",
    ) -> CollabSession:
        """创建协作会话"""
        session = CollabSession(
            book_id=book_id,
            chapter_num=chapter_num,
            doc_id=f"{book_id}:ch{chapter_num}",
            owner_id=owner_id,
            content=content,
            title=title,
        )
        session.participants.add(owner_id)

        self._sessions[session.session_id] = session

        # 创建权限资源
        resource_id = f"collab:{session.session_id}"
        self._permissions.create_resource(resource_id, owner_id)

        # 保存初始版本
        if content:
            self._diff.save_snapshot(
                session.doc_id, content, author_id=owner_id, description="Initial version"
            )
            session.version_count = 1

        logger.info(
            "Collab session created: %s (book=%s, ch=%d)", session.session_id, book_id, chapter_num
        )
        return session

    def join_session(self, session_id: str, user_id: str) -> CollabSession | None:
        """加入协作会话"""
        session = self._sessions.get(session_id)
        if not session:
            return None
        if session.participant_count >= _MAX_USERS_PER_SESSION:
            return None
        session.participants.add(user_id)
        session.touch()
        return session

    def leave_session(self, session_id: str, user_id: str) -> None:
        """离开协作会话"""
        session = self._sessions.get(session_id)
        if not session:
            return
        session.participants.discard(user_id)
        if user_id == session.locked_by:
            session.locked_by = ""
            session.locked_at = 0.0
        session.touch()

    def close_session(self, session_id: str) -> bool:
        """关闭协作会话"""
        session = self._sessions.pop(session_id, None)
        if session:
            resource_id = f"collab:{session_id}"
            self._permissions.delete_resource(resource_id)
            logger.info("Collab session closed: %s", session_id)
            return True
        return False

    def get_session(self, session_id: str) -> CollabSession | None:
        return self._sessions.get(session_id)

    def list_sessions(self, book_id: str = "") -> list[CollabSession]:
        """列出会话"""
        sessions = list(self._sessions.values())
        if book_id:
            sessions = [s for s in sessions if s.book_id == book_id]
        return sorted(sessions, key=lambda s: s.created_at)

    # ── 文档锁定 ──

    def lock_document(self, session_id: str, user_id: str) -> bool:
        """锁定文档（互斥编辑）"""
        session = self._sessions.get(session_id)
        if not session:
            return False
        if session.is_locked and session.locked_by != user_id:
            return False
        session.locked_by = user_id
        session.locked_at = time.time()
        session.touch()
        return True

    def unlock_document(self, session_id: str, user_id: str) -> bool:
        """解锁文档"""
        session = self._sessions.get(session_id)
        if not session:
            return False
        if session.locked_by != user_id:
            return False
        session.locked_by = ""
        session.locked_at = 0.0
        session.touch()
        return True

    def force_unlock(self, session_id: str, user_id: str) -> bool:
        """强制解锁（仅 Owner）"""
        session = self._sessions.get(session_id)
        if not session:
            return False
        if user_id != session.owner_id:
            return False
        session.locked_by = ""
        session.locked_at = 0.0
        return True

    # ── 版本管理 ──

    def save_version(
        self,
        doc_id: str,
        content: str,
        author_id: str,
        description: str = "",
    ) -> str:
        """保存新版本，返回版本 ID"""
        snapshot = self._diff.save_snapshot(
            doc_id=doc_id,
            content=content,
            author_id=author_id,
            description=description,
        )

        # 更新会话版本计数
        for session in self._sessions.values():
            if session.doc_id == doc_id:
                session.version_count += 1
                session.content = content
                session.touch()
                break

        return snapshot.version_id

    def get_version_history(self, doc_id: str) -> list[dict[str, Any]]:
        return self._diff.get_version_history(doc_id)

    def get_diff(
        self,
        doc_id: str,
        version_old: str,
        version_new: str,
    ):
        """获取两个版本的差异"""
        return self._diff.compare_versions(doc_id, version_old, version_new)

    # ── 管理 ──

    def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        expired = [sid for sid, s in self._sessions.items() if s.is_expired]
        for sid in expired:
            self.close_session(sid)
        return len(expired)

    def get_stats(self) -> dict[str, Any]:
        return {
            "active_sessions": len(self._sessions),
            "sessions": [
                {
                    "session_id": s.session_id,
                    "book_id": s.book_id,
                    "chapter_num": s.chapter_num,
                    "participants": s.participant_count,
                    "is_locked": s.is_locked,
                    "locked_by": s.locked_by,
                    "version_count": s.version_count,
                    "created_at": s.created_at,
                    "last_active": s.last_active,
                }
                for s in self._sessions.values()
            ],
            "permissions": {
                "total_resources": len(self._permissions._resources),
            },
            "comments": {
                "total_threads": len(self._comments._threads),
            },
            "diff_engine": self._diff.get_stats(),
            "websocket": self._ws_handler.get_stats(),
        }


# 全局单例
collab_engine = CollabEngine()
