"""
昆仑创作引擎 — 本地技能包市场 (Local Marketplace)

管理本地技能组合包（Combo Pack），每个组合包包含 Rule + Workflow + Skill 集合。
对标灵蟹创作 Marketplace 组合包，支持安装/卸载/搜索/热门排行。

用法:
    from kunlun.local_marketplace import LocalMarketplaceEngine, get_local_marketplace

    engine = get_local_marketplace()
    packs = engine.list_available(category="xuanhuan")
    engine.install("book_001", "pack_xuanhuan_shuangwen")
"""

from kunlun.local_marketplace.engine import (
    LocalMarketplaceEngine,
    get_local_marketplace,
)
from kunlun.local_marketplace.presets import COMBO_PACKS, get_all_packs, get_pack_by_id

__all__ = [
    "COMBO_PACKS",
    "LocalMarketplaceEngine",
    "get_all_packs",
    "get_local_marketplace",
    "get_pack_by_id",
]
