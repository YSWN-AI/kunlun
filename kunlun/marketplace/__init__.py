"""
模板市场 — 模板发现/安装/发布

支持:
- 模板分类 (TemplateCategory) — 大纲/角色/世界观/书籍/提示词
- 模板发布 (TemplatePublish) — 作者上传+审核
- 模板安装 (TemplateInstall) — 一键安装到本地
- 模板搜索 (TemplateSearch) — 关键词/分类/评分筛选
- 模板版本 (TemplateVersion) — 增量更新

用法:
    from kunlun.marketplace import MarketplaceEngine

    engine = MarketplaceEngine()
    templates = engine.search(category="outline", query="仙侠")
    engine.install("tpl_001", user_id="user_001")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TemplateCategory(StrEnum):
    """模板分类"""

    OUTLINE = "outline"  # 大纲模板
    CHARACTER = "character"  # 角色模板
    WORLD = "world"  # 世界观模板
    BOOK = "book"  # 书籍模板
    PROMPT = "prompt"  # 提示词模板
    STYLE = "style"  # 文风模板
    PLOT = "plot"  # 情节模板
    DIALOGUE = "dialogue"  # 对话模板


@dataclass
class TemplateMeta:
    """模板元数据"""

    template_id: str = ""
    name: str = ""
    author_id: str = ""
    category: TemplateCategory = TemplateCategory.OUTLINE
    description: str = ""
    tags: list[str] = field(default_factory=list)
    price: int = 0  # 0=免费, >0=灵石
    downloads: int = 0
    rating: float = 0.0  # 1-5 星
    rating_count: int = 0
    version: str = "1.0.0"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    is_official: bool = False
    is_verified: bool = False
    preview_images: list[str] = field(default_factory=list)
    content: str = ""  # 模板内容 (JSON/YAML)
    genre_tags: list[str] = field(default_factory=list)


@dataclass
class UserLibrary:
    """用户模板库"""

    user_id: str = ""
    installed: dict[str, str] = field(default_factory=dict)  # template_id -> version
    favorites: list[str] = field(default_factory=list)
    published: list[str] = field(default_factory=list)


class MarketplaceEngine:
    """模板市场引擎

    核心职责:
    - 模板索引与搜索
    - 模板安装/更新/卸载
    - 模板发布与审核
    - 用户模板库管理
    - 热门/推荐算法

    用法:
        market = MarketplaceEngine()
        market.publish_template(template)
        results = market.search("仙侠 大纲")
    """

    def __init__(self):
        self._templates: dict[str, TemplateMeta] = {}
        self._libraries: dict[str, UserLibrary] = {}
        self._categories: dict[TemplateCategory, list[str]] = {}

        # 预置模板
        self._setup_presets()

    def _setup_presets(self) -> None:
        """初始化官方预置模板"""
        import uuid

        presets = [
            (
                "仙侠大纲模板",
                TemplateCategory.OUTLINE,
                ["仙侠", "大纲"],
                "标准仙侠小说大纲模板，含境界体系、宗门设定、奇遇节点",
            ),
            (
                "都市人物模板",
                TemplateCategory.CHARACTER,
                ["都市", "角色"],
                "都市小说角色卡模板，含身份、职业、人际关系网",
            ),
            (
                "修真世界观模板",
                TemplateCategory.WORLD,
                ["修真", "世界观"],
                "修真世界观构建模板，含灵气体系、修炼等级、势力分布",
            ),
            (
                "悬疑情节模板",
                TemplateCategory.PLOT,
                ["悬疑", "情节"],
                "悬疑情节设计模板，含伏笔布局、误导线、揭秘节奏",
            ),
        ]
        for name, category, tags, desc in presets:
            tpl_id = str(uuid.uuid4())[:10]
            self._templates[tpl_id] = TemplateMeta(
                template_id=tpl_id,
                name=name,
                author_id="official",
                category=category,
                description=desc,
                tags=tags,
                is_official=True,
                is_verified=True,
                downloads=100 + hash(name) % 900,
                rating=4.0 + (hash(name) % 10) / 10.0,
                rating_count=10 + hash(name) % 50,
            )
            self._index_category(category, tpl_id)

    def _index_category(self, category: TemplateCategory, tpl_id: str) -> None:
        self._categories.setdefault(category, []).append(tpl_id)

    # ── 搜索与发现 ────────────────────────────────

    def search(
        self,
        query: str = "",
        category: str = "",
        sort_by: str = "downloads",
        limit: int = 20,
    ) -> list[TemplateMeta]:
        """搜索模板

        Args:
            query: 搜索关键词
            category: 分类筛选
            sort_by: downloads / rating / newest
            limit: 返回数量
        """
        results: list[TemplateMeta] = []

        for tpl in self._templates.values():
            # 分类筛选
            if category and tpl.category != category:
                continue

            # 关键词搜索
            if query:
                q = query.lower()
                match = (
                    q in tpl.name.lower()
                    or q in tpl.description.lower()
                    or any(q in t.lower() for t in tpl.tags)
                )
                if not match:
                    continue

            results.append(tpl)

        # 排序
        if sort_by == "downloads":
            results.sort(key=lambda t: -t.downloads)
        elif sort_by == "rating":
            results.sort(key=lambda t: -t.rating)
        elif sort_by == "newest":
            results.sort(key=lambda t: -t.created_at)

        return results[:limit]

    def get_hot(self, limit: int = 10) -> list[TemplateMeta]:
        """热门模板 (下载量排行)"""
        return self.search(sort_by="downloads", limit=limit)

    def get_featured(self, limit: int = 5) -> list[TemplateMeta]:
        """精选模板 (高评分官方模板)"""
        official = [t for t in self._templates.values() if t.is_official]
        official.sort(key=lambda t: -t.rating)
        return official[:limit]

    def get_recommended(self, user_id: str, limit: int = 10) -> list[TemplateMeta]:
        """个性化推荐 (基于已安装的喜好)"""
        library = self._libraries.get(user_id)
        if not library:
            return self.get_hot(limit)

        # 从已安装模板中提取偏好标签
        preferred_tags: set[str] = set()
        for tpl_id in library.installed:
            tpl = self._templates.get(tpl_id)
            if tpl:
                preferred_tags.update(tpl.tags)

        # 找类似标签的模板
        scored: list[tuple[int, TemplateMeta]] = []
        for tpl in self._templates.values():
            if tpl.template_id in library.installed:
                continue
            overlap = len(set(tpl.tags) & preferred_tags)
            scored.append((overlap, tpl))

        scored.sort(key=lambda x: -x[0])
        return [s[1] for s in scored[:limit]]

    def get_by_category(self, category: TemplateCategory) -> list[TemplateMeta]:
        return self.search(category=category)

    # ── 安装管理 ──────────────────────────────────

    def get_library(self, user_id: str) -> UserLibrary:
        """获取用户模板库"""
        if user_id not in self._libraries:
            self._libraries[user_id] = UserLibrary(user_id=user_id)
        return self._libraries[user_id]

    def install(self, template_id: str, user_id: str) -> bool:
        """安装模板"""
        tpl = self._templates.get(template_id)
        if not tpl:
            return False

        library = self.get_library(user_id)
        library.installed[template_id] = tpl.version
        tpl.downloads += 1
        return True

    def uninstall(self, template_id: str, user_id: str) -> bool:
        """卸载模板"""
        library = self._libraries.get(user_id)
        if not library:
            return False
        library.installed.pop(template_id, None)
        library.favorites = [f for f in library.favorites if f != template_id]
        return True

    def favorite(self, template_id: str, user_id: str) -> bool:
        """收藏模板"""
        library = self.get_library(user_id)
        if template_id not in library.favorites:
            library.favorites.append(template_id)
        return True

    def get_installed(self, user_id: str) -> list[TemplateMeta]:
        """获取用户已安装的模板"""
        library = self._libraries.get(user_id)
        if not library:
            return []
        return [self._templates[tid] for tid in library.installed if tid in self._templates]

    # ── 发布 ──────────────────────────────────────

    def publish_template(
        self,
        name: str,
        category: TemplateCategory,
        description: str,
        content: str,
        author_id: str = "",
        tags: list[str] | None = None,
        price: int = 0,
        genre_tags: list[str] | None = None,
    ) -> TemplateMeta:
        """发布模板"""
        import uuid

        tpl = TemplateMeta(
            template_id=str(uuid.uuid4())[:10],
            name=name,
            author_id=author_id,
            category=category,
            description=description,
            content=content,
            tags=tags or [],
            price=price,
            genre_tags=genre_tags or [],
        )
        self._templates[tpl.template_id] = tpl
        self._index_category(category, tpl.template_id)

        # 更新用户发布列表
        if author_id:
            library = self.get_library(author_id)
            library.published.append(tpl.template_id)

        return tpl

    def rate_template(self, template_id: str, rating: float) -> bool:
        """评分模板 (1-5)"""
        tpl = self._templates.get(template_id)
        if not tpl:
            return False
        rating = max(1.0, min(5.0, rating))
        tpl.rating = ((tpl.rating * tpl.rating_count) + rating) / (tpl.rating_count + 1)
        tpl.rating_count += 1
        return True

    # ── 统计 ──────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_templates": len(self._templates),
            "categories": {cat.value: len(ids) for cat, ids in self._categories.items()},
            "total_downloads": sum(t.downloads for t in self._templates.values()),
            "total_users": len(self._libraries),
            "featured_count": len(self.get_featured()),
        }


# 全局单例
marketplace_engine = MarketplaceEngine()
