"""
昆仑创作引擎 — 世界观设定结构化管理模块

对标马良写作的世界观设定管理：
  - 30 类结构化字段
  - 按卷渐进开放（visible_from_volume）
  - 对 AI 隐藏防剧透（hidden_from_ai）
  - 版本历史追溯
  - RAG 可见性过滤

核心类:
    WorldSettingManager — 设定条目 CRUD + 版本 + 可见性过滤
    WORLD_SETTING_CATEGORIES — 30 类结构化字段 Schema

用法:
    from kunlun.world_setting import WorldSettingManager
    manager = WorldSettingManager("book_001")
    entry = manager.create_entry("power_system", "炼气期", {...})
"""

from __future__ import annotations

from kunlun.world_setting.manager import WorldSettingManager
from kunlun.world_setting.schema import (
    WORLD_SETTING_CATEGORIES,
    get_all_categories,
    get_category,
    get_category_count,
    get_field_types,
)

__all__ = [
    "WORLD_SETTING_CATEGORIES",
    "WorldSettingManager",
    "get_all_categories",
    "get_category",
    "get_category_count",
    "get_field_types",
]
