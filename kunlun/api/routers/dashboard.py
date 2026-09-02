"""
昆仑创作引擎 — 仪表盘路由 (v2)
全书概览 + 质量雷达图 + 进度 + 快照拍摄/历史 + 导出

端点:
  GET  /dashboard-v2/{book_id}/overview   — 全书仪表盘概览
  GET  /dashboard-v2/{book_id}/radar      — 质量雷达图
  GET  /dashboard-v2/{book_id}/progress   — 全书进度
  POST /dashboard-v2/{book_id}/snapshot   — 拍摄仪表盘快照
  GET  /dashboard-v2/{book_id}/snapshots  — 历史快照列表
  GET  /dashboard-v2/{book_id}/export     — 导出完整摘要
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from kunlun.api.routers._shared import cached_import
from kunlun.api.security_middleware import validate_book_id

router = APIRouter(prefix="/dashboard-v2", tags=["仪表盘"])


class SnapshotRequest(BaseModel):
    label: str = Field(default="", description="快照标签")
    include_details: bool = Field(default=True, description="是否包含详细数据")


@router.get("/{book_id}/overview")
async def dashboard_overview(book_id: str):
    """全书仪表盘概览"""
    validate_book_id(book_id)
    dash = cached_import("kunlun.dashboard.engine", "DashboardEngine")
    engine = dash.get_factory(book_id)
    return {"success": True, "data": engine.get_overview()}


@router.get("/{book_id}/radar")
async def dashboard_radar(book_id: str):
    """质量雷达图数据"""
    validate_book_id(book_id)
    dash = cached_import("kunlun.dashboard.engine", "DashboardEngine")
    engine = dash.get_factory(book_id)
    return {"success": True, "data": engine.get_radar()}


@router.get("/{book_id}/progress")
async def dashboard_progress(book_id: str):
    """全书进度"""
    validate_book_id(book_id)
    dash = cached_import("kunlun.dashboard.engine", "DashboardEngine")
    engine = dash.get_factory(book_id)
    return {"success": True, "data": engine.get_progress()}


@router.post("/{book_id}/snapshot")
async def take_snapshot(book_id: str, req: SnapshotRequest = None):
    """拍摄仪表盘快照"""
    validate_book_id(book_id)
    dash = cached_import("kunlun.dashboard.engine", "DashboardEngine")
    engine = dash.get_factory(book_id)
    label = req.label if req else ""
    include = req.include_details if req else True
    snap = engine.take_snapshot(label, include)
    return {"success": True, "data": snap}


@router.get("/{book_id}/snapshots")
async def list_snapshots(book_id: str):
    """历史快照列表"""
    validate_book_id(book_id)
    dash = cached_import("kunlun.dashboard.engine", "DashboardEngine")
    engine = dash.get_factory(book_id)
    return {"success": True, "data": engine.list_snapshots()}


@router.get("/{book_id}/export")
async def export_dashboard(book_id: str):
    """导出仪表盘完整摘要"""
    validate_book_id(book_id)
    dash = cached_import("kunlun.dashboard.engine", "DashboardEngine")
    engine = dash.get_factory(book_id)
    return {"success": True, "data": engine.export_summary()}
