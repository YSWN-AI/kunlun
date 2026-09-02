"""
WebSocket 进度推送管理器

向连接的客户端广播章节生成全链路进度:
  Step 0: KG 快照拍摄
  Step 1: Architect 蓝图生成
  Step 2: Writer 多模型抽卡
  Step 3: Auditor 8道门禁
  Step 4: 审计修订 (最多3轮)
  Step 5: StyleEngineer 润色

使用:
    from kunlun.api.ws_manager import ws_manager
    await ws_manager.broadcast(book_id, chapter, "processing", {
        "step": "Step 2: Writer 抽卡生成",
        "progress": 0.4,
        "detail": "gpt-4o 正在生成...",
    })
"""

from __future__ import annotations

import asyncio
import contextlib
import time

from fastapi import WebSocket
from loguru import logger

HEARTBEAT_INTERVAL = 30


class WSProgressManager:
    """
    WebSocket 进度管理器

    管理 book_id + chapter 级别的 WebSocket 连接池，
    支持向特定通道广播进度消息。

    心跳: 每 {HEARTBEAT_INTERVAL}s 清理僵尸连接。
    """

    def __init__(self):
        # key: f"{book_id}:{chapter}" → set of WebSocket connections
        self._connections: dict[str, set[WebSocket]] = {}
        # 反向索引: WebSocket → channel key
        self._client_channels: dict[WebSocket, str] = {}
        self._heartbeat_task: asyncio.Task | None = None

    async def _ensure_heartbeat(self):
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        """定期 ping 所有连接，清理僵尸连接"""
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            dead = []
            for ws in list(self._client_channels):
                try:
                    await asyncio.wait_for(
                        ws.send_json({"type": "ping", "t": time.time()}),
                        timeout=5.0,
                    )
                except (TimeoutError, Exception):
                    dead.append(ws)
            for ws in dead:
                await self.disconnect(ws)
            if dead:
                logger.debug(f"[WS] 清理 {len(dead)} 个僵尸连接")

    async def connect(self, websocket: WebSocket, book_id: str, chapter: int) -> None:
        """注册新的 WebSocket 连接"""
        channel = f"{book_id}:{chapter}"
        await websocket.accept()

        if channel not in self._connections:
            self._connections[channel] = set()
        self._connections[channel].add(websocket)
        self._client_channels[websocket] = channel
        await self._ensure_heartbeat()

        logger.info(f"WS连接: channel={channel}, 当前{len(self._connections[channel])}个订阅者")

    async def disconnect_channel(self, book_id: str, chapter: int):
        """批量断开指定频道所有连接"""
        channel = f"{book_id}:{chapter}"
        for ws in list(self._connections.get(channel, set())):
            await self.disconnect(ws)

    async def disconnect(self, websocket: WebSocket) -> None:
        """移除 WebSocket 连接并关闭"""
        channel = self._client_channels.pop(websocket, None)
        if channel and channel in self._connections:
            self._connections[channel].discard(websocket)
            remaining = len(self._connections[channel])
            if not self._connections[channel]:
                del self._connections[channel]
            logger.info(f"WS断开: channel={channel}, 剩余{remaining}个订阅者")
        # 关闭 WebSocket 连接以释放资源
        with contextlib.suppress(Exception):
            await websocket.close()

    async def broadcast(
        self, book_id: str, chapter: int, status: str, payload: dict | None = None
    ) -> None:
        """
        向指定 book_id + chapter 的所有连接广播进度

        Args:
            book_id: 书籍ID
            chapter: 章节号
            status: 进度状态标签 (idle/processing/completed/failed)
            payload: 额外数据 (step, progress, detail, metrics 等)
        """
        channel = f"{book_id}:{chapter}"
        if channel not in self._connections:
            return

        message = {
            "type": "progress",
            "book_id": book_id,
            "chapter": chapter,
            "status": status,
            "timestamp": time.time(),
        }
        if payload:
            message.update(payload)

        # 快照连接集合，防止 await 期间集合被修改导致 RuntimeError
        connections_snapshot = list(self._connections.get(channel, set()))
        disconnected = []
        for ws in connections_snapshot:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            await self.disconnect(ws)

    async def broadcast_step(
        self, book_id: str, chapter: int, step_label: str, progress: float, detail: str = ""
    ) -> None:
        """便捷方法: 广播步骤进度"""
        await self.broadcast(
            book_id,
            chapter,
            "processing",
            {
                "step": step_label,
                "progress": progress,
                "detail": detail,
            },
        )

    async def broadcast_complete(
        self, book_id: str, chapter: int, metrics: dict | None = None
    ) -> None:
        """便捷方法: 广播完成"""
        await self.broadcast(
            book_id,
            chapter,
            "completed",
            {
                "step": "完成",
                "progress": 1.0,
                "metrics": metrics or {},
            },
        )

    async def broadcast_error(self, book_id: str, chapter: int, step: str, error: str) -> None:
        """便捷方法: 广播错误"""
        await self.broadcast(
            book_id,
            chapter,
            "failed",
            {
                "step": step,
                "progress": -1,
                "error": error,
            },
        )


# 全局单例
ws_manager = WSProgressManager()
