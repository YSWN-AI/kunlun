"""
昆仑创作引擎 — 题材模板库 (Genre Template Library)

灵感来源: webnovel-writer 37题材模板 + InkOS 题材规则库
对标: 网文平台 37 种主流题材分类体系
"""

from kunlun.genre.engine import (
    GENRE_LIBRARY,
    TOP10_TEMPLATES,
    AudienceLevel,
    GenreCategory,
    GenreConfig,
    GenreRuleEngine,
    GenreTemplate,
    PaceType,
    get_genre_engine,
)

__all__ = [
    "GENRE_LIBRARY",
    "TOP10_TEMPLATES",
    "AudienceLevel",
    "GenreCategory",
    "GenreConfig",
    "GenreRuleEngine",
    "GenreTemplate",
    "PaceType",
    "get_genre_engine",
]
