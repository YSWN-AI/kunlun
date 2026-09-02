"""
实时协作模块 — CRDT-based 协同编辑 + 评论批注 + 权限系统

支持多人实时协作写作，包括:
- CRDT 文档同步 (基于 Yjs 协议)
- 用户在线状态/光标同步 (Awareness)
- 评论/批注系统
- 版本差异对比
- 权限管理 (Owner/Editor/Commenter/Viewer)
- WebSocket 实时通信

用法:
    from kunlun.collab import CollabEngine, Permission, CommentSystem

    engine = CollabEngine()
    await engine.create_session(book_id="book_001", chapter_num=42)
"""

from __future__ import annotations

from kunlun.collab.comments import Comment, CommentSystem, CommentThread
from kunlun.collab.diff_engine import DiffEngine, DiffResult
from kunlun.collab.engine import CollabEngine, CollabSession
from kunlun.collab.permissions import Permission, PermissionManager, PermissionRole
from kunlun.collab.ws_handler import CollabWebSocketHandler

__all__ = [
    "CollabEngine",
    "CollabSession",
    "CollabWebSocketHandler",
    "Comment",
    "CommentSystem",
    "CommentThread",
    "DiffEngine",
    "DiffResult",
    "Permission",
    "PermissionManager",
    "PermissionRole",
]
