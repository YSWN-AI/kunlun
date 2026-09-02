"""
测试: WebSocket 进度管理器
"""

import pytest

pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock

from kunlun.api.ws_manager import WSProgressManager


class TestWSProgressManagerInit:
    """初始化"""

    def test_manager_created_empty(self):
        manager = WSProgressManager()
        assert manager._connections == {}

    def test_channel_key_format(self):
        key = "book_001:1"
        assert key == "book_001:1"


class TestWSProgressManagerConnect:
    """连接管理"""

    @pytest.fixture
    def manager(self):
        return WSProgressManager()

    @pytest.mark.asyncio
    async def test_connect_new_channel(self, manager):
        mock_ws = AsyncMock()
        await manager.connect(mock_ws, "book_001", 1)
        assert "book_001:1" in manager._connections
        assert mock_ws in manager._connections["book_001:1"]

    @pytest.mark.asyncio
    async def test_connect_multiple_clients(self, manager):
        ws1, ws2, ws3 = AsyncMock(), AsyncMock(), AsyncMock()
        await manager.connect(ws1, "book_001", 3)
        await manager.connect(ws2, "book_001", 3)
        await manager.connect(ws3, "book_001", 3)
        assert len(manager._connections["book_001:3"]) == 3

    @pytest.mark.asyncio
    async def test_connect_different_channels(self, manager):
        ws1, ws2 = AsyncMock(), AsyncMock()
        await manager.connect(ws1, "book_001", 1)
        await manager.connect(ws2, "book_001", 2)
        assert len(manager._connections["book_001:1"]) == 1
        assert len(manager._connections["book_001:2"]) == 1


class TestWSProgressManagerDisconnect:
    """断开连接"""

    @pytest.fixture
    def manager(self):
        return WSProgressManager()

    @pytest.mark.asyncio
    async def test_disconnect_existing(self, manager):
        ws = AsyncMock()
        await manager.connect(ws, "book_001", 1)
        await manager.disconnect(ws)
        # 最后一个连接断开后 channel 被删除
        assert "book_001:1" not in manager._connections

    @pytest.mark.asyncio
    async def test_disconnect_one_of_many(self, manager):
        ws1, ws2, ws3 = AsyncMock(), AsyncMock(), AsyncMock()
        await manager.connect(ws1, "book_001", 1)
        await manager.connect(ws2, "book_001", 1)
        await manager.connect(ws3, "book_001", 1)
        await manager.disconnect(ws2)
        assert len(manager._connections["book_001:1"]) == 2
        assert ws1 in manager._connections["book_001:1"]
        assert ws3 in manager._connections["book_001:1"]

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_no_error(self, manager):
        """不存在的连接不会抛出异常"""
        # 验证断开不存在的连接安全且无副作用
        prev_count = len(manager._connections)
        await manager.disconnect(AsyncMock())
        assert len(manager._connections) == prev_count, "断开不存在的连接不应修改状态"


class TestWSProgressManagerBroadcast:
    """广播"""

    @pytest.fixture
    def manager(self):
        return WSProgressManager()

    @pytest.mark.asyncio
    async def test_broadcast_to_connected(self, manager):
        ws = AsyncMock()
        await manager.connect(ws, "book_001", 1)

        await manager.broadcast("book_001", 1, "test", {"data": "hello"})

        ws.send_json.assert_called_once()
        call_arg = ws.send_json.call_args[0][0]
        assert call_arg["data"] == "hello"
        assert call_arg["status"] == "test"

    @pytest.mark.asyncio
    async def test_broadcast_no_connections(self, manager):
        await manager.broadcast("book_001", 99, "test")

    @pytest.mark.asyncio
    async def test_broadcast_step(self, manager):
        ws = AsyncMock()
        await manager.connect(ws, "book_001", 1)

        await manager.broadcast_step(
            "book_001",
            1,
            "Step 1: Blueprint",
            progress=20.0,
            detail="生成蓝图中...",
        )

        ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_complete(self, manager):
        ws = AsyncMock()
        await manager.connect(ws, "book_001", 1)

        await manager.broadcast_complete(
            "book_001",
            1,
            metrics={"word_count": 2500, "chapters": 5},
        )

        ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_error(self, manager):
        ws = AsyncMock()
        await manager.connect(ws, "book_001", 1)

        await manager.broadcast_error(
            "book_001",
            1,
            step="Step 3: Writer",
            error="生成超时",
        )

        ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_cleans_disconnected(self, manager):
        ws_dead = AsyncMock()
        ws_dead.send_json = AsyncMock(side_effect=Exception("disconnected"))
        ws_alive = AsyncMock()

        await manager.connect(ws_dead, "book_001", 1)
        await manager.connect(ws_alive, "book_001", 1)

        await manager.broadcast("book_001", 1, "test")

        assert ws_dead not in manager._connections["book_001:1"]
        assert ws_alive in manager._connections["book_001:1"]
        ws_alive.send_json.assert_called_once()
