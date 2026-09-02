"""
Kunlun Creation Engine — FastAPI Application Package.

This package contains the REST API and WebSocket endpoints
for the Kunlun novel creation engine.
"""

from kunlun.api.main import app, lifespan
from kunlun.api.routes import router
from kunlun.api.streaming import StreamingGenerator
from kunlun.api.ws_manager import WSProgressManager, ws_manager

__all__ = [
    "StreamingGenerator",
    "WSProgressManager",
    "app",
    "lifespan",
    "router",
    "ws_manager",
]
