"""
昆仑创作引擎 — AIGC 痕迹检测增强系统

基于已有 audit/ai_features.py (24+特征) 和 audit/post_write_validator.py (17条规则)，
提供更高层次的综合报告、跨章节统计趋势、批量检测和可操作性建议。
"""

from kunlun.aigc_detect.engine import (
    AIDetectDimension,
    AIGCDetector,
    AIGCDetectReport,
    AIGCTrendTracker,
    DimensionScore,
    get_detector,
    get_tracker,
)

__all__ = [
    "AIDetectDimension",
    "AIGCDetectReport",
    "AIGCDetector",
    "AIGCTrendTracker",
    "DimensionScore",
    "get_detector",
    "get_tracker",
]
