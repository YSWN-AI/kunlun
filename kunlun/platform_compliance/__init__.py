"""
昆仑创作引擎 — 平台合规检测与适配系统

灵感来源: 2025-2026 中文网文平台 AI 政策收紧
对标: 起点/番茄/七猫/飞卢/晋江等主流平台的 AI 合规要求
"""

from kunlun.platform_compliance.engine import (
    AIPolicyStrictness,
    ChinesePlatform,
    ComplianceChecker,
    ComplianceItem,
    ComplianceLevel,
    MultiPlatformChecker,
    PlatformComplianceReport,
    PlatformPolicy,
    PlatformRegistry,
    get_compliance_checker,
    get_multi_platform_checker,
)

__all__ = [
    "AIPolicyStrictness",
    "ChinesePlatform",
    "ComplianceChecker",
    "ComplianceItem",
    "ComplianceLevel",
    "MultiPlatformChecker",
    "PlatformComplianceReport",
    "PlatformPolicy",
    "PlatformRegistry",
    "get_compliance_checker",
    "get_multi_platform_checker",
]
