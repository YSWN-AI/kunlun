"""
共享 Mock 基础设施 — 可复用的测试夹具和辅助函数

提供:
- 临时目录夹具 (temp_dir)
- KG 客户端 mock (mock_kg_client)
- LLM 调用 mock (mock_llm_call)
- 异步方法 mock 辅助 (async_return)
- Settings 临时覆盖 (mock_settings)
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─── 临时目录 ────────────────────────────────────────


@pytest.fixture
def temp_dir():
    """创建临时目录，测试结束后自动清理"""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


# ─── Settings 临时覆盖 ────────────────────────────────


@pytest.fixture
def mock_settings(monkeypatch):
    """提供 monkeypatch 快捷方式，用于临时覆盖 settings 属性

    用法:
        def test_something(mock_settings):
            mock_settings("qdrant_path", "/tmp/test_qdrant")
            mock_settings("neo4j_uri", "bolt://localhost:7687")
    """

    def _set(attr: str, value: Any) -> None:
        from kunlun.config import settings
        monkeypatch.setattr(settings, attr, value)

    return _set


# ─── KG 客户端 Mock ─────────────────────────────────


@pytest.fixture
def mock_kg_client():
    """Mock KG 客户端，返回预设的 Cypher 查询结果

    用法:
        def test_entity_lookup(mock_kg_client):
            mock_kg_client.query_cypher.return_value = [
                {"uid": "e1", "type": "Character", "name": "主角"}
            ]
    """
    with patch("kunlun.ripple.detector.kg_client", autospec=True) as mock_kg:
        mock_kg.query_cypher = MagicMock(return_value=[])
        mock_kg.health_check = MagicMock(return_value={"neo4j": True, "qdrant": True, "sqlite": True})
        mock_kg.get_entity = MagicMock(return_value=None)
        mock_kg.upsert_entity = MagicMock(return_value=True)
        yield mock_kg


# ─── LLM 调用 Mock ──────────────────────────────────


@pytest.fixture
def mock_llm_call():
    """Mock LLM API 调用，返回预设文本

    用法:
        def test_generate(mock_llm_call):
            mock_llm_call.return_value = "这是一段生成的文本"
    """
    with patch("kunlun.model_router.ModelRouter.call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = "mock LLM response"
        yield mock


@pytest.fixture
def mock_llm_stream():
    """Mock LLM 流式调用

    用法:
        def test_stream(mock_llm_stream):
            mock_llm_stream.return_value = ["片段1", "片段2", "片段3"]
    """
    with patch("kunlun.model_router.ModelRouter.call_llm_stream", new_callable=AsyncMock) as mock:
        mock.return_value = ["mock chunk 1", "mock chunk 2"]
        yield mock


# ─── 异步辅助 ────────────────────────────────────────


def async_return(value: Any) -> AsyncMock:
    """创建返回指定值的 AsyncMock

    用法:
        mock = async_return("hello")
        result = await mock()  # "hello"
    """
    mock = AsyncMock()
    mock.return_value = value
    return mock


def async_side_effect(values: list[Any]) -> AsyncMock:
    """创建按顺序返回的 AsyncMock

    用法:
        mock = async_side_effect(["a", "b", "c"])
        await mock()  # "a"
        await mock()  # "b"
        await mock()  # "c"
    """
    mock = AsyncMock()
    mock.side_effect = values
    return mock


# ─── HTTP 响应 Mock ──────────────────────────────────


def make_httpx_response(status_code: int = 200, json_data: dict | None = None, text: str = "") -> MagicMock:
    """创建模拟的 httpx Response 对象"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp
