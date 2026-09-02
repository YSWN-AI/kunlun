"""
昆仑创作引擎 — API 路由兼容层

⚠️ 所有 106 个端点已迁移到 kunlun/api/routers/ (40 个模块化 v2 路由文件)。
   v2 路由已在 main.py 中以更高优先级挂载到 /api/v1，同时提供 /api/v2 前缀访问。
   本文件仅保留 APIRouter 对象供 main.py 和 __init__.py 向后兼容。
   外部依赖：
     - main.py: from kunlun.api.routes import router
     - __init__.py: from kunlun.api.routes import router
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()
