"""
插件商店 — 插件搜索/评分/安装/发布

支持:
- 插件分类 (PluginCategory) — 写作/审计/发布/数据/协作/社区
- 插件发布 (PluginPublish) — 开发者上传+审核
- 插件安装 (PluginInstall) — 一键安装到本地
- 插件搜索 (PluginSearch) — 关键词/分类/评分筛选
- 插件依赖 (PluginDependency) — 自动检查依赖兼容性
- 插件评分 (PluginRating) — 用户评分与评论

用法:
    from kunlun.plugin_store import PluginStoreEngine

    engine = PluginStoreEngine()
    plugins = engine.search(category="writing", query="大纲")
    engine.install("plg_001", user_id="user_001")
"""

from __future__ import annotations

import time
import tomllib
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class PluginCategory(StrEnum):
    """插件分类"""

    WRITING = "writing"  # 写作辅助
    AUDIT = "audit"  # 审计增强
    PUBLISH = "publish"  # 发布扩展
    DATA = "data"  # 数据分析
    COLLAB = "collab"  # 协作工具
    COMMUNITY = "community"  # 社区功能
    EXPORT = "export"  # 导出格式
    NOTIFY = "notify"  # 通知推送
    AI = "ai"  # AI 增强
    UTILITY = "utility"  # 工具类


class PluginStatus(StrEnum):
    """插件状态"""

    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    SUSPENDED = "suspended"


@dataclass
class PluginDependency:
    """插件依赖"""

    name: str = ""
    version: str = "*"  # semver range
    optional: bool = False


@dataclass
class PluginMeta:
    """插件元数据

    基于 pyproject.toml 的 [tool.kunlun.plugin] 字段
    """

    plugin_id: str = ""
    name: str = ""
    author: str = ""
    version: str = "0.1.0"
    category: PluginCategory = PluginCategory.UTILITY
    description: str = ""
    tags: list[str] = field(default_factory=list)
    # 安装信息
    package_name: str = ""  # pip 包名
    entry_point: str = ""  # 入口类路径, e.g. "my_plugin.MyPlugin"
    dependencies: list[PluginDependency] = field(default_factory=list)
    min_kunlun_version: str = "0.3.0"
    # 市场信息
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0
    price: int = 0  # 灵石
    status: PluginStatus = PluginStatus.DRAFT
    is_official: bool = False
    is_verified: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    # 文档
    readme: str = ""
    changelog: str = ""
    homepage: str = ""
    repository: str = ""


@dataclass
class PluginReview:
    """插件评价"""

    review_id: str = ""
    plugin_id: str = ""
    user_id: str = ""
    rating: float = 0.0
    title: str = ""
    content: str = ""
    version: str = ""
    created_at: float = field(default_factory=time.time)


class PluginStoreEngine:
    """插件商店引擎

    核心职责:
    - 插件索引与搜索
    - 插件安装/更新/卸载
    - 插件发布与审核
    - 依赖冲突检测
    - 评分与评价系统
    - 兼容性检查

    用法:
        store = PluginStoreEngine()
        store.publish_plugin(meta)
        results = store.search("协作 编辑")
    """

    def __init__(self):
        self._plugins: dict[str, PluginMeta] = {}
        self._installed: dict[str, dict[str, str]] = {}  # user_id -> {plugin_id: version}
        self._reviews: dict[str, list[PluginReview]] = {}  # plugin_id -> reviews
        self._categories: dict[PluginCategory, list[str]] = {}

        self._setup_presets()

    def _setup_presets(self) -> None:
        """预置官方插件"""
        import uuid

        presets = [
            (
                "大纲增强器",
                PluginCategory.WRITING,
                "自动生成章节大纲并支持分支情节",
                ["大纲", "分支", "写作"],
            ),
            (
                "AI查重器",
                PluginCategory.AUDIT,
                "检测文本相似度，防止内容重复",
                ["查重", "审计", "质量"],
            ),
            (
                "多格式导出器",
                PluginCategory.EXPORT,
                "一键导出为 EPUB/PDF/MOBI/HTML",
                ["导出", "格式"],
            ),
            (
                "写作统计面板",
                PluginCategory.DATA,
                "字数统计、写作速度、效率分析",
                ["统计", "数据", "效率"],
            ),
            (
                "实时协作白板",
                PluginCategory.COLLAB,
                "多人实时编辑同一个文档",
                ["协作", "实时", "编辑"],
            ),
            (
                "读者互动机器人",
                PluginCategory.COMMUNITY,
                "自动回复读者评论，生成互动报告",
                ["社区", "互动", "读者"],
            ),
            (
                "章节定时发布",
                PluginCategory.PUBLISH,
                "定时自动发布到多个平台",
                ["发布", "定时", "多平台"],
            ),
            ("飞书/微信通知", PluginCategory.NOTIFY, "重要事件推送到飞书/微信", ["通知", "推送"]),
        ]
        for name, category, desc, tags in presets:
            plg_id = f"official-{uuid.uuid4().hex[:8]}"
            self._plugins[plg_id] = PluginMeta(
                plugin_id=plg_id,
                name=name,
                author="official",
                category=category,
                description=desc,
                tags=tags,
                package_name=f"kunlun-plugin-{name.lower().replace(' ', '-')}",
                entry_point=f"kunlun_plugin_{plg_id[-6:]}.Plugin",
                is_official=True,
                is_verified=True,
                status=PluginStatus.PUBLISHED,
                downloads=50 + hash(name) % 450,
                rating=3.5 + (hash(name) % 15) / 10.0,
                rating_count=5 + hash(name) % 20,
            )
            self._categories.setdefault(category, []).append(plg_id)

    # ── 搜索与发现 ────────────────────────────────

    def search(
        self,
        query: str = "",
        category: str = "",
        sort_by: str = "downloads",
        limit: int = 20,
    ) -> list[PluginMeta]:
        """搜索插件

        Args:
            query: 搜索关键词
            category: 分类名
            sort_by: downloads / rating / newest
            limit: 返回数量
        """
        results: list[PluginMeta] = []

        for plg in self._plugins.values():
            if plg.status != PluginStatus.PUBLISHED:
                continue
            if category and plg.category != category:
                continue
            if query:
                q = query.lower()
                match = (
                    q in plg.name.lower()
                    or q in plg.description.lower()
                    or any(q in t.lower() for t in plg.tags)
                )
                if not match:
                    continue
            results.append(plg)

        if sort_by == "downloads":
            results.sort(key=lambda p: -p.downloads)
        elif sort_by == "rating":
            results.sort(key=lambda p: -p.rating)
        elif sort_by == "newest":
            results.sort(key=lambda p: -p.created_at)

        return results[:limit]

    def get_hot(self, limit: int = 10) -> list[PluginMeta]:
        return self.search(sort_by="downloads", limit=limit)

    def get_featured(self, limit: int = 5) -> list[PluginMeta]:
        official = [
            p
            for p in self._plugins.values()
            if p.is_official and p.status == PluginStatus.PUBLISHED
        ]
        official.sort(key=lambda p: -p.rating)
        return official[:limit]

    def get_by_category(self, category: PluginCategory) -> list[PluginMeta]:
        return self.search(category=category)

    def get_by_author(self, author: str) -> list[PluginMeta]:
        return [
            p
            for p in self._plugins.values()
            if p.author == author and p.status == PluginStatus.PUBLISHED
        ]

    def get_plugin(self, plugin_id: str) -> PluginMeta | None:
        return self._plugins.get(plugin_id)

    # ── 安装管理 ──────────────────────────────────

    def get_installed(self, user_id: str) -> dict[str, str]:
        """获取用户已安装插件 {plugin_id: version}"""
        return self._installed.get(user_id, {})

    def install(self, plugin_id: str, user_id: str) -> bool:
        """安装插件（模拟 — 实际需要 pip install）"""
        plg = self._plugins.get(plugin_id)
        if not plg or plg.status != PluginStatus.PUBLISHED:
            return False

        # 检查依赖兼容性
        if not self._check_compatibility(plugin_id, user_id):
            return False

        self._installed.setdefault(user_id, {})[plugin_id] = plg.version
        plg.downloads += 1
        return True

    def uninstall(self, plugin_id: str, user_id: str) -> bool:
        """卸载插件"""
        installed = self._installed.get(user_id)
        if not installed:
            return False
        installed.pop(plugin_id, None)
        return True

    def update(self, plugin_id: str, user_id: str) -> bool:
        """更新插件到最新版本"""
        installed = self._installed.get(user_id, {})
        if plugin_id not in installed:
            return False

        plg = self._plugins.get(plugin_id)
        if not plg:
            return False

        installed[plugin_id] = plg.version
        return True

    def is_installed(self, plugin_id: str, user_id: str) -> bool:
        return plugin_id in self._installed.get(user_id, {})

    def _check_compatibility(self, plugin_id: str, user_id: str) -> bool:
        """检查插件与已安装插件的兼容性"""
        plg = self._plugins.get(plugin_id)
        if not plg:
            return False

        installed = self._installed.get(user_id, {})
        for dep in plg.dependencies:
            if dep.optional:
                continue
            if dep.name not in installed and dep.name not in self._plugins:
                return False
        return True

    def check_updates(self, user_id: str) -> list[tuple[str, str, str]]:
        """检查已安装插件的可用更新
        Returns: [(plugin_id, installed_version, latest_version)]
        """
        updates = []
        installed = self._installed.get(user_id, {})
        for plg_id, current_ver in installed.items():
            plg = self._plugins.get(plg_id)
            if plg and plg.version != current_ver:
                updates.append((plg_id, current_ver, plg.version))
        return updates

    # ── 发布 ──────────────────────────────────────

    def publish_plugin(
        self,
        name: str,
        category: PluginCategory,
        description: str,
        author: str = "",
        tags: list[str] | None = None,
        package_name: str = "",
        entry_point: str = "",
        dependencies: list[PluginDependency] | None = None,
        min_kunlun_version: str = "0.3.0",
        readme: str = "",
    ) -> PluginMeta:
        """发布插件到商店"""
        import uuid

        plg = PluginMeta(
            plugin_id=f"community-{uuid.uuid4().hex[:8]}",
            name=name,
            author=author,
            category=category,
            description=description,
            tags=tags or [],
            package_name=package_name,
            entry_point=entry_point,
            dependencies=dependencies or [],
            min_kunlun_version=min_kunlun_version,
            readme=readme,
            status=PluginStatus.DRAFT,
        )
        self._plugins[plg.plugin_id] = plg
        self._categories.setdefault(category, []).append(plg.plugin_id)
        return plg

    def approve_plugin(self, plugin_id: str) -> bool:
        """审核通过插件"""
        plg = self._plugins.get(plugin_id)
        if not plg or plg.status != PluginStatus.DRAFT:
            return False
        plg.status = PluginStatus.PUBLISHED
        plg.is_verified = True
        return True

    def deprecate_plugin(self, plugin_id: str) -> bool:
        """废弃插件"""
        plg = self._plugins.get(plugin_id)
        if not plg:
            return False
        plg.status = PluginStatus.DEPRECATED
        return True

    # ── 评分与评价 ────────────────────────────────

    def rate(self, plugin_id: str, _user_id: str, rating: float) -> bool:
        """评分 (1-5)"""
        plg = self._plugins.get(plugin_id)
        if not plg:
            return False
        rating = max(1.0, min(5.0, rating))
        plg.rating = ((plg.rating * plg.rating_count) + rating) / (plg.rating_count + 1)
        plg.rating_count += 1
        return True

    def review(
        self,
        plugin_id: str,
        user_id: str,
        rating: float,
        title: str,
        content: str,
    ) -> PluginReview | None:
        """提交评价"""
        import uuid

        plg = self._plugins.get(plugin_id)
        if not plg:
            return None

        review_obj = PluginReview(
            review_id=str(uuid.uuid4())[:10],
            plugin_id=plugin_id,
            user_id=user_id,
            rating=rating,
            title=title,
            content=content,
            version=plg.version,
        )
        self._reviews.setdefault(plugin_id, []).append(review_obj)
        self.rate(plugin_id, user_id, rating)
        return review_obj

    def get_reviews(self, plugin_id: str) -> list[PluginReview]:
        return self._reviews.get(plugin_id, [])

    # ── 插件元数据解析 ─────────────────────────────

    def parse_plugin_toml(self, path: str) -> PluginMeta | None:
        """从 pyproject.toml 解析插件元数据

        期望格式:
            [tool.kunlun.plugin]
            name = "MyPlugin"
            category = "writing"
            entry_point = "my_plugin.MyPlugin"
        """
        try:
            with Path(path).open("rb") as f:
                data = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError):
            return None

        tool = data.get("tool", {}).get("kunlun", {}).get("plugin", {})
        if not tool:
            return None

        import uuid

        deps = []
        for dep_name, dep_spec in tool.get("dependencies", {}).items():
            deps.append(
                PluginDependency(
                    name=dep_name,
                    version=dep_spec if isinstance(dep_spec, str) else dep_spec.get("version", "*"),
                    optional=isinstance(dep_spec, dict) and dep_spec.get("optional", False),
                )
            )

        return PluginMeta(
            plugin_id=f"local-{uuid.uuid4().hex[:6]}",
            name=tool.get("name", ""),
            author=tool.get("author", ""),
            version=data.get("project", {}).get("version", "0.1.0"),
            category=PluginCategory(tool.get("category", "utility")),
            description=tool.get("description", ""),
            tags=tool.get("tags", []),
            package_name=data.get("project", {}).get("name", ""),
            entry_point=tool.get("entry_point", ""),
            dependencies=deps,
            min_kunlun_version=tool.get("min_kunlun_version", "0.3.0"),
            status=PluginStatus.DRAFT,
        )

    # ── 统计 ──────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_plugins": len(self._plugins),
            "published_plugins": sum(
                1 for p in self._plugins.values() if p.status == PluginStatus.PUBLISHED
            ),
            "official_plugins": sum(1 for p in self._plugins.values() if p.is_official),
            "categories": {cat.value: len(ids) for cat, ids in self._categories.items()},
            "total_downloads": sum(p.downloads for p in self._plugins.values()),
            "total_reviews": sum(len(r) for r in self._reviews.values()),
            "total_users": len(self._installed),
        }


# 全局单例
plugin_store_engine = PluginStoreEngine()
