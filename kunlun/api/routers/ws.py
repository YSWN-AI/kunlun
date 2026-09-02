"""
昆仑创作引擎 — WebSocket 路由
/ws/{book_id}/{chapter}
"""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

router = APIRouter()


@router.websocket("/ws/{book_id}/{chapter}")
async def websocket_progress(websocket: WebSocket, book_id: str, chapter: int):
    """WebSocket 端点: 接收章节生成进度推送"""
    from kunlun.api.ws_manager import ws_manager

    await ws_manager.connect(websocket, book_id, chapter)
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "book_id": book_id,
                "chapter": chapter,
                "message": "已连接到进度推送通道",
            }
        )
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except TimeoutError:
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break
            except WebSocketDisconnect:
                break
    except Exception as e:
        logger.warning(f"WebSocket 异常: {e}")
    finally:
        await ws_manager.disconnect(websocket)
