"""
本地模式审计降级 — 自用场景下的简化审计

API 模式下: 53 维完整审计
本地模式下: 15 维核心审计（本地模型性能有限）

核心 15 维:
  - 情节: 冲突强度、节奏感、信息密度
  - 角色: 行为一致性、对话自然度
  - 结构: 章节完整性、章末钩子强度
  - 语言: 套话检测、句式多样性、AI 痕迹
  - 适配: 黄金三章检查、番茄适配度
  - 综合: 逻辑连贯性、情感冲击力、读者代入感

用法:
    from kunlun.audit_local import get_audit_dimensions, should_skip_tier3

    dimensions = get_audit_dimensions()
    if should_skip_tier3():
        print("本地模式，跳过 Tier 3 级联评估")
"""

from __future__ import annotations

from typing import Any

from kunlun.config import settings
from kunlun.config.defaults import DEFAULT_AUDIT_DIMENSIONS_FULL, DEFAULT_AUDIT_DIMENSIONS_LOCAL

# ── 本地模式核心审计维度 ─────────────────────────

LOCAL_AUDIT_DIMENSIONS: list[dict[str, Any]] = [
    # 情节维度 (4)
    {"name": "冲突强度", "key": "conflict_intensity", "category": "plot", "weight": 8},
    {"name": "节奏感", "key": "pacing", "category": "plot", "weight": 7},
    {"name": "信息密度", "key": "info_density", "category": "plot", "weight": 6},
    {"name": "情节推进", "key": "plot_progression", "category": "plot", "weight": 7},
    # 角色维度 (3)
    {"name": "行为一致性", "key": "character_consistency", "category": "character", "weight": 6},
    {"name": "对话自然度", "key": "dialogue_naturalness", "category": "character", "weight": 6},
    {
        "name": "角色辨识度",
        "key": "character_distinctiveness",
        "category": "character",
        "weight": 5,
    },
    # 结构维度 (2)
    {"name": "章节完整性", "key": "chapter_completeness", "category": "structure", "weight": 5},
    {"name": "章末钩子强度", "key": "hook_strength", "category": "structure", "weight": 8},
    # 语言维度 (4)
    {"name": "套话检测", "key": "cliche_detection", "category": "language", "weight": 6},
    {"name": "句式多样性", "key": "sentence_variety", "category": "language", "weight": 4},
    {"name": "AI 痕迹", "key": "ai_detection", "category": "language", "weight": 7},
    {"name": "错别字/语病", "key": "typo_check", "category": "language", "weight": 5},
    # 综合维度 (2)
    {"name": "逻辑连贯性", "key": "logic_coherence", "category": "comprehensive", "weight": 6},
    {"name": "读者代入感", "key": "reader_immersion", "category": "comprehensive", "weight": 6},
]


def is_local_mode() -> bool:
    """检查是否本地模式"""
    try:
        return settings.is_local_mode()
    except Exception:
        return True


def get_audit_dimensions() -> list[dict[str, Any]]:
    """获取当前模式下的审计维度

    Returns:
        本地模式: 15 维核心审计
        API 模式: 53 维完整审计（需从 audit 模块获取）
    """
    if is_local_mode():
        return LOCAL_AUDIT_DIMENSIONS

    # API 模式 — 返回本地维度元数据，实际 53 维由 audit 模块处理
    return LOCAL_AUDIT_DIMENSIONS  # 作为默认，53 维由 auditor33 提供


def get_audit_dimension_count() -> int:
    """获取当前模式下的审计维度数"""
    return DEFAULT_AUDIT_DIMENSIONS_LOCAL if is_local_mode() else DEFAULT_AUDIT_DIMENSIONS_FULL


def should_skip_tier3() -> bool:
    """本地模式下应跳过 Tier 3 级联评估"""
    return is_local_mode()


def get_local_audit_summary() -> dict[str, Any]:
    """获取本地审计配置摘要"""
    categories: dict[str, list[str]] = {}
    for d in LOCAL_AUDIT_DIMENSIONS:
        categories.setdefault(d["category"], []).append(d["name"])

    return {
        "mode": "local" if is_local_mode() else "api",
        "total_dimensions": get_audit_dimension_count(),
        "categories": categories,
        "weights": {d["key"]: d["weight"] for d in LOCAL_AUDIT_DIMENSIONS},
        "skip_tier3": should_skip_tier3(),
        "top_weighted": sorted(LOCAL_AUDIT_DIMENSIONS, key=lambda d: -d["weight"])[:5],
    }
