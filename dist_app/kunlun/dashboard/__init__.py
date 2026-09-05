"""
dashboard 扩展模块
"""

from kunlun.dashboard.engine import (
    DashboardEngine,
    DashboardSnapshot,
    QualityRadar,
    WordStats,
    get_dashboard,
)

# 向后兼容别名
Dashboard = DashboardEngine  # deprecated: 保留旧名兼容

__all__ = [
    "Dashboard",
    "DashboardEngine",
    "DashboardSnapshot",
    "QualityRadar",
    "WordStats",
    "get_dashboard",
]
