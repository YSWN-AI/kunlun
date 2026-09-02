"""
33维审计 — 共享数据定义

本模块不包含审计逻辑,仅提供:
  - AI_FATIGUE_WORDS: AI痕迹检测词表
  - DimResult: 单个维度审计结果
  - Audit33Report: 33维审计综合报告
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ─── AI痕迹检测词表 ───

AI_FATIGUE_WORDS = {
    "high_frequency": [
        "突然",
        "忽然",
        "仿佛",
        "似乎",
        "犹如",
        "宛如",
        "赫然",
        "竟然",
        "居然",
        "不由得",
        "忍不住",
        "不禁",
        "下意识",
        "自然而然",
        "显而易见",
        "总的来说",
        "综上所述",
        "总而言之",
        "简而言之",
        "换句话说",
        "不仅",
        "而且",
        "同时",
        "此外",
        "另外",
        "与此同时",
        "深深地",
        "紧紧地",
        "慢慢地",
        "渐渐地",
        "缓缓地",
        "轻轻地",
    ],
    "sentence_starters": [
        "他",
        "她",
        "它",
        "这",
        "那",
        "一",
        "在",
        "随",
        "接",
        "然",
        "于",
        "便",
    ],
    "over_summary_markers": [
        "通过这件事",
        "这次经历让",
        "从此以后",
        "从那以后",
        "这一",
        "值得注意",
        "不可否认",
        "毫无疑问",
        "显而易见",
    ],
    "weak_descriptors": [
        "非常",
        "十分",
        "极其",
        "格外",
        "特别",
        "相当",
        "比较",
        "有点",
        "略微",
        "稍微",
        "颇",
        "甚",
    ],
    "lazy_transitions": [
        "接着",
        "然后",
        "之后",
        "随后",
        "紧接着",
        "不一会儿",
        "就这样",
        "于是",
        "所以",
        "因此",
        "因而",
    ],
    "cliche_emotions": [
        "心中一惊",
        "心头一颤",
        "倒吸一口凉气",
        "瞳孔一缩",
        "脸色一变",
        "眉头一皱",
        "嘴角上扬",
        "眼中闪过一丝",
    ],
}


@dataclass
class DimResult:
    """单个维度的审计结果"""

    dim_id: str
    name: str
    score: float  # 0-100
    level: str  # PASS/WARN/FAIL
    detail: str
    suggestion: str = ""
    auto_fixable: bool = False


@dataclass
class Audit33Report:
    """33维审计综合报告"""

    chapter: int
    dimensions: list[DimResult] = field(default_factory=list)
    overall_score: float = 0.0
    passed: bool = False
    fatal_count: int = 0
    warn_count: int = 0
    ai_detection_score: float = 0.0  # 越低AI味越重
    summary: str = ""
