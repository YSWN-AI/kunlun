"""
WebSocket 处理器 — 实时协作通信

支持:
- 文档同步消息 (sync_update)
- 光标/选区 Awareness (awareness_update)
- 评论推送 (comment_added, comment_resolved)
- 用户加入/离开通知 (user_joined, user_left)

消息协议:
    {
        "type": "sync_update | awareness_update | comment_added | ...",
        "session_id": "session_xxx",
        "doc_id": "chapter_42",
        "user_id": "user_001",
        "data": { ... },
        "timestamp": 1234567890.0
    }
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CollabMessage:
    """协作消息"""

    type: str
    session_id: str = ""
    doc_id: str = ""
    user_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(
            {
                "type": self.type,
                "session_id": self.session_id,
                "doc_id": self.doc_id,
                "user_id": self.user_id,
                "data": self.data,
                "timestamp": self.timestamp,
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, raw: str | bytes) -> CollabMessage:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        return cls(
            type=data.get("type", ""),
            session_id=data.get("session_id", ""),
            doc_id=data.get("doc_id", ""),
            user_id=data.get("user_id", ""),
            data=data.get("data", {}),
            timestamp=data.get("timestamp", time.time()),
        )


@dataclass
class UserPresence:
    """用户在线状态"""

    user_id: str
    user_name: str = ""
    cursor_pos: int = 0  # 光标位置
    selection_start: int = 0  # 选区起始
    selection_end: int = 0  # 选区结束
    last_active: float = field(default_factory=time.time)
    is_online: bool = True


class CollabWebSocketHandler:
    """WebSocket 协作处理器

    管理 WebSocket 连接、消息路由、用户状态跟踪。

    用法:
        handler = CollabWebSocketHandler(engine)

        # 在 FastAPI WebSocket 端點中使用:
        @app.websocket("/ws/collab/{session_id}")
        async def collab_ws(websocket, session_id: str):
            await handler.handle(websocket, session_id, user_id)
    """

    MAX_CONNECTIONS_PER_SESSION = 20

    def __init__(self, engine=None):
        self._engine = engine
        # session_id -> user_id -> websocket
        self._connections: dict[str, dict[str, Any]] = {}
        # session_id -> user_id -> UserPresence
        self._presence: dict[str, dict[str, UserPresence]] = {}

    def register_engine(self, engine) -> None:
        self._engine = engine

    async def handle(
        self,
        websocket,
        session_id: str,
        user_id: str,
        user_name: str = "",
    ) -> None:
        """处理 WebSocket 连接"""
        if session_id not in self._connections:
            self._connections[session_id] = {}
            self._presence[session_id] = {}

        session_conns = self._connections[session_id]
        if len(session_conns) >= self.MAX_CONNECTIONS_PER_SESSION:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "data": {"message": "会话连接数已达上限"},
                    },
                    ensure_ascii=False,
                )
            )
            await websocket.close()
            return

        session_conns[user_id] = websocket
        self._presence[session_id][user_id] = UserPresence(
            user_id=user_id,
            user_name=user_name,
        )

        await self._broadcast_presence(session_id, user_id, "joined")

        try:
            while True:
                data = await websocket.receive_text()
                await self._handle_message(session_id, user_id, data)
        except Exception:
            logger.debug("WebSocket connection closed: %s/%s", session_id, user_id)
        finally:
            session_conns.pop(user_id, None)
            if user_id in self._presence.get(session_id, {}):
                self._presence[session_id][user_id].is_online = False
            await self._broadcast_presence(session_id, user_id, "left")

            if not session_conns:
                self._connections.pop(session_id, None)
                self._presence.pop(session_id, None)

    async def _handle_message(self, session_id: str, user_id: str, raw: str) -> None:
        """处理收到的消息"""
        try:
            msg = CollabMessage.from_json(raw)
        except json.JSONDecodeError:
            return

        msg.session_id = session_id
        msg.user_id = user_id

        if msg.type == "sync_update":
            await self._broadcast(session_id, msg, exclude=user_id)
        elif msg.type == "awareness_update":
            self._update_presence(session_id, user_id, msg.data)
            await self._broadcast(session_id, msg, exclude=user_id)
        elif msg.type in {"comment_added", "comment_resolved"}:
            await self._broadcast(session_id, msg)
        elif msg.type == "ping":
            await self._send_to(
                session_id,
                user_id,
                CollabMessage(
                    type="pong",
                    session_id=session_id,
                    user_id="system",
                ),
            )

    async def _broadcast(
        self,
        session_id: str,
        msg: CollabMessage,
        exclude: str = "",
    ) -> None:
        """广播消息到会话中所有用户"""
        connections = self._connections.get(session_id, {})
        payload = msg.to_json()
        for uid, ws in connections.items():
            if uid == exclude:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                logger.debug("Failed to send to %s", uid)

    async def _send_to(
        self,
        session_id: str,
        user_id: str,
        msg: CollabMessage,
    ) -> None:
        """发送消息到指定用户"""
        ws = self._connections.get(session_id, {}).get(user_id)
        if ws:
            try:
                await ws.send_text(msg.to_json())
            except Exception:
                logger.debug("Failed to send to %s", user_id)

    def _update_presence(
        self,
        session_id: str,
        user_id: str,
        data: dict[str, Any],
    ) -> None:
        """更新用户在线状态"""
        presence = self._presence.get(session_id, {}).get(user_id)
        if presence:
            presence.cursor_pos = data.get("cursor_pos", presence.cursor_pos)
            presence.selection_start = data.get("selection_start", presence.selection_start)
            presence.selection_end = data.get("selection_end", presence.selection_end)
            presence.last_active = time.time()

    async def _broadcast_presence(
        self,
        session_id: str,
        user_id: str,
        event_type: str,
    ) -> None:
        """广播用户状态变更"""
        presences = self._presence.get(session_id, {})
        msg = CollabMessage(
            type=f"user_{event_type}",
            session_id=session_id,
            user_id=user_id,
            data={
                "users": [
                    {
                        "user_id": p.user_id,
                        "user_name": p.user_name,
                        "cursor_pos": p.cursor_pos,
                        "selection_start": p.selection_start,
                        "selection_end": p.selection_end,
                        "is_online": p.is_online,
                    }
                    for p in presences.values()
                ],
            },
        )
        await self._broadcast(session_id, msg)

    def get_session_users(self, session_id: str) -> list[dict[str, Any]]:
        """获取会话中的用户列表"""
        presences = self._presence.get(session_id, {})
        return [
            {
                "user_id": p.user_id,
                "user_name": p.user_name,
                "cursor_pos": p.cursor_pos,
                "is_online": p.is_online,
                "last_active": p.last_active,
            }
            for p in presences.values()
        ]

    def get_stats(self) -> dict[str, Any]:
        return {
            "active_sessions": len(self._connections),
            "total_connections": sum(len(v) for v in self._connections.values()),
        }
