"""
quality 扩展模块
"""

from kunlun.quality.dashboard import QualityDashboard, quality_dashboard
from kunlun.quality.engine import (
    ChapterQualityReport,
    QualityDimension,
    QualityEvaluator,
    QualityScore,
    QualityTrendTracker,
    get_quality_evaluator,
    get_quality_tracker,
)

__all__ = [
    "ChapterQualityReport",
    "QualityDashboard",
    "QualityDimension",
    "QualityEvaluator",
    "QualityScore",
    "QualityTrendTracker",
    "get_quality_evaluator",
    "get_quality_tracker",
    "quality_dashboard",
]
