"""
Kunlun Creation Engine — FastAPI Application Package.

This package contains the REST API and WebSocket endpoints
for the Kunlun novel creation engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kunlun.api.routes import router
from kunlun.api.streaming import StreamingGenerator
from kunlun.api.ws_manager import WSProgressManager, ws_manager

if TYPE_CHECKING:
    from kunlun.api.main import app as _app
    from kunlun.api.main import lifespan as _lifespan

__all__ = [
    "StreamingGenerator",
    "WSProgressManager",
    "app",
    "lifespan",
    "router",
    "ws_manager",
]


def __getattr__(name: str) -> Any:
    """延迟导入 app 和 lifespan，避免包初始化时触发 main.py 完整导入。"""
    if name == "app":
        from kunlun.api.main import app

        return app
    if name == "lifespan":
        from kunlun.api.main import lifespan

        return lifespan
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
