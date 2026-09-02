"""
昆仑创作引擎 — 追读力系统 (Retention Engine)

基于 webnovel-writer 追读力系统 + InkOS 37维审计的最佳实践。
核心能力: Hook检测、爽点评分、微兑现追踪、无聊债务管理、平台适配评分、
         流失预测、钩子强度评分、留存优化。
"""

from __future__ import annotations

from kunlun.retention.debt import DebtTracker
from kunlun.retention.dropoff import DropOffPredictor
from kunlun.retention.engine import RetentionPredictor, get_retention_predictor
from kunlun.retention.features import ChapterFeatureExtractor
from kunlun.retention.hooks import HookDetector, HookStrengthScorer
from kunlun.retention.optimizer import RetentionOptimizer
from kunlun.retention.payoff import PayoffTracker
from kunlun.retention.platform import PlatformAdapter
from kunlun.retention.pleasure_scorer import PleasureScorer
from kunlun.retention.types import (
    ChapterFeatures,
    Debt,
    DebtType,
    DropOffPrediction,
    HookResult,
    HookStrengthReport,
    HookType,
    MicroPayoff,
    PleasureCategory,
    PleasurePoint,
    RetentionOptimizationPlan,
    RetentionReport,
    RiskLevel,
)

__all__ = [
    # 检测器
    "ChapterFeatureExtractor",
    # 数据模型
    "ChapterFeatures",
    "Debt",
    "DebtTracker",
    "DebtType",
    "DropOffPrediction",
    "DropOffPredictor",
    "HookDetector",
    "HookResult",
    "HookStrengthReport",
    "HookStrengthScorer",
    "HookType",
    "MicroPayoff",
    "PayoffTracker",
    "PlatformAdapter",
    "PleasureCategory",
    "PleasurePoint",
    "PleasureScorer",
    "RetentionOptimizationPlan",
    # 优化器
    "RetentionOptimizer",
    # 主引擎
    "RetentionPredictor",
    "RetentionReport",
    "RiskLevel",
    "get_retention_predictor",
]
