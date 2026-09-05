"""
模块懒加载 — 按需加载非核心模块

自用模式下，以下模块默认不加载：
  - plugins (插件系统)
  - collab (实时协作)
  - community (社区)
  - publish_v2 (多平台发布)
  - tts (语音合成)
  - image_gen (图像生成)
  - openapi (开放 API)

企业模式下全部加载。

用法:
    from kunlun.model_lazy_loader import is_module_enabled, get_enabled_modules

    if is_module_enabled("community"):
        from kunlun.community import community_engine
"""

from __future__ import annotations

import logging
from typing import Any

from kunlun.config import settings

logger = logging.getLogger(__name__)

# ── 模块分类 ──────────────────────────────────────

# 核心模块（自用和企业模式都加载）
CORE_MODULES = {
    "agents",
    "api",
    "audit",
    "branch_plot",
    "character",
    "coherence",
    "config",
    "conflict",
    "continuity",
    "dialogue",
    "gacha",
    "genres",
    "golden_triple",
    "import_engine",
    "kg",
    "notify",
    "outline",
    "pipeline",
    "pleasure",
    "plot",
    "proofread",
    "quality",
    "recovery",
    "retention",
    "spacetime",
    "structure",
    "style",
    "vibe_writer",
    "worlds",
}

# 扩展模块（仅企业模式加载）
ENTERPRISE_MODULES = {
    "collab",  # 实时协作
    "community",  # 社区论坛
    "plugins",  # 插件系统
    "publish_v2",  # 多平台发布
    "tts",  # 语音合成
    "image_gen",  # 图像生成
    "openapi",  # 开放 API
    "monetize",  # 变现系统 (Phase 3)
    "marketplace",  # 模板市场 (Phase 3)
    "plugin_store",  # 插件商店 (Phase 3)
    "finetune",  # 模型微调 (Phase 3)
    "analytics",  # 数据看板 (Phase 3)
}

# 所有已知模块
ALL_MODULES = CORE_MODULES | ENTERPRISE_MODULES


def is_personal_mode() -> bool:
    """检查是否自用模式"""
    try:
        return settings.is_personal_mode()
    except Exception:
        return True  # 默认自用


def is_module_enabled(module_name: str) -> bool:
    """检查模块是否启用

    Args:
        module_name: 模块名（如 'community', 'collab'）

    Returns:
        True if the module should be loaded
    """
    if module_name in CORE_MODULES:
        return True
    if module_name in ENTERPRISE_MODULES:
        return not is_personal_mode()
    return True  # 未知模块默认启用


def get_enabled_modules() -> set[str]:
    """获取当前模式下的启用模块列表"""
    enabled = set(CORE_MODULES)
    if not is_personal_mode():
        enabled |= ENTERPRISE_MODULES
    return enabled


def get_disabled_modules() -> set[str]:
    """获取当前模式下的禁用模块列表"""
    if is_personal_mode():
        return ENTERPRISE_MODULES.copy()
    return set()


def get_module_status() -> dict[str, Any]:
    """获取模块加载状态详情"""
    personal = is_personal_mode()
    return {
        "mode": "personal" if personal else "enterprise",
        "core_modules": sorted(CORE_MODULES),
        "enterprise_modules": sorted(ENTERPRISE_MODULES),
        "enabled_modules": sorted(get_enabled_modules()),
        "disabled_modules": sorted(get_disabled_modules()),
        "total_enabled": len(get_enabled_modules()),
        "total_disabled": len(get_disabled_modules()),
    }


def print_module_status() -> None:
    """打印模块加载状态（用于 CLI）"""
    status = get_module_status()
    try:
        from colorama import Fore, Style

        y = Fore.YELLOW
        c = Fore.CYAN
        r = Style.RESET_ALL
    except ImportError:
        y = c = r = ""

    print(f"  运行模式: {c}{status['mode']}{r}")
    print(f"  已启用模块 ({status['total_enabled']}):")
    print(f"    {', '.join(status['enabled_modules'])}")
    if status["disabled_modules"]:
        print(f"  {y}已禁用模块 ({status['total_disabled']}):{r}")
        print(f"  {y}  {', '.join(status['disabled_modules'])}{r}")
        print(f"  {y}  提示: 设置 KUNLUN_MODE=enterprise 启用全部模块{r}")
