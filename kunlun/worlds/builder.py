"""
昆仑创作引擎 — 世界观构建引擎 (World Builder)

深度融合 StoryCraftr 的 RAG 知识管理 + StoryCraft Studio 的交互式图集设计。
四大核心模块: WorldBuilder / WorldAtlas / FactionNetwork / TimelineEngine

与 engine.py 无缝集成: 调用 WorldConsistencyChecker 做内部矛盾检测。
"""

from __future__ import annotations

from typing import ClassVar

from loguru import logger

from kunlun.worlds.atlas import WorldAtlas
from kunlun.worlds.engine import (
    Dimension,
    Severity,
    WorldConsistencyChecker,
    WorldSetting,
    get_world_manager,
)
from kunlun.worlds.faction import FactionNetwork
from kunlun.worlds.timeline import TimelineEngine
from kunlun.worlds.types import (
    FactionNode,
    FactionType,
    LocationCard,
    LocationType,
)

# ══════════════════════════════════════════════════════
# WorldBuilder — 世界观构建引擎
# ══════════════════════════════════════════════════════


class WorldBuilder:
    """世界观构建引擎 — 整合所有子模块的主入口

    深度融合 StoryCraftr 的 RAG 知识管理理念：
    - 结构化知识条目
    - 两阶段检索（关键词→语义）
    """

    GENRE_TEMPLATES: ClassVar[dict[str, dict]] = {
        "xianxia": {
            "name": "修真仙侠",
            "dimensions": ["power_system", "geography", "culture_rules", "item_artifact"],
            "power_system": "灵气修炼体系，境界划分：炼气→筑基→金丹→元婴→化神→合体→大乘→渡劫",
            "default_locations": ["凡间", "修真界", "仙界"],
            "default_factions": ["正道联盟", "魔教", "散修盟"],
        },
        "xuanhuan": {
            "name": "东方玄幻",
            "dimensions": ["power_system", "magic_tech", "creature_species", "economy"],
            "power_system": "斗气/魔力/血脉体系",
            "default_locations": ["边陲小镇", "帝都", "魔兽山脉", "学院"],
            "default_factions": ["帝国", "宗门", "佣兵工会", "魔兽森林"],
        },
        "urban": {
            "name": "都市",
            "dimensions": ["economy", "culture_rules", "geography"],
            "power_system": "财富/权力/人脉体系",
            "default_locations": ["都市", "公司", "家族"],
            "default_factions": ["商业集团", "地下势力", "官方组织"],
        },
    }

    def __init__(self, book_id: str = "", genre: str = "xuanhuan") -> None:
        self.book_id = book_id
        self.genre = genre
        self.atlas = WorldAtlas(book_id)
        self.factions = FactionNetwork(book_id)
        self.timeline = TimelineEngine(book_id)
        self._world_manager = get_world_manager(book_id) if book_id else None
        self._consistency_checker = WorldConsistencyChecker()

    def init_from_template(self) -> dict:
        """从体裁模板初始化世界观"""
        template = self.GENRE_TEMPLATES.get(self.genre, self.GENRE_TEMPLATES["xuanhuan"])

        # 初始化地点
        for i, loc_name in enumerate(template.get("default_locations", [])):
            self.atlas.add_location(
                LocationCard(
                    location_id=f"loc_{i:03d}",
                    name=loc_name,
                    location_type=LocationType.REGION if i == 0 else LocationType.CITY,
                    description=f"{loc_name} — {template['name']}世界观的核心区域",
                )
            )

        # 初始化势力
        for i, fac_name in enumerate(template.get("default_factions", [])):
            self.factions.add_faction(
                FactionNode(
                    faction_id=f"fac_{i:03d}",
                    name=fac_name,
                    faction_type=FactionType.SECT if i < 2 else FactionType.OTHER,
                    power_level=80 - i * 15,
                )
            )

        # 初始化世界设定
        if self._world_manager:
            for dim_name in template.get("dimensions", []):
                try:
                    dim = Dimension(dim_name)
                    self._world_manager.add_setting(
                        WorldSetting(
                            key=f"auto_{dim_name}",
                            dimension=dim,
                            name=dim_name,
                            description=template.get(dim_name, ""),
                        )
                    )
                except ValueError:
                    pass

        return {
            "genre": self.genre,
            "locations_count": len(self.atlas._locations),
            "factions_count": len(self.factions._factions),
            "template": template["name"],
        }

    def auto_detect_contradictions(self) -> dict:
        """自动检测内部矛盾"""
        settings = self._world_manager.list_settings() if self._world_manager else []
        if not settings:
            return {"contradictions": [], "score": 100, "summary": "无设定数据"}

        report = self._consistency_checker.audit("", settings)
        return {
            "contradictions": [
                {"dimension": d, "score": s, "severity": v}
                for d, s, v in zip(
                    report.dimension_scores.keys(),
                    report.dimension_scores.values(),
                    [Severity.INFO.value] * len(report.dimension_scores),
                    strict=False,
                )
            ],
            "score": report.overall_score,
            "summary": f"总体得分 {report.overall_score}/100",
        }

    def get_full_world_summary(self) -> dict:
        """获取世界观完整摘要"""
        atlas_stats = self.atlas.get_statistics()
        faction_balance = self.factions.analyze_balance()
        contradictions = self.auto_detect_contradictions()

        return {
            "genre": self.genre,
            "atlas": atlas_stats,
            "factions": {
                "total": len(self.factions._factions),
                "balance": faction_balance,
            },
            "timeline": {
                "total_events": len(self.timeline._events),
                "eras": self.timeline._eras,
            },
            "contradictions": contradictions,
        }

    def export_story_bible(self) -> str:
        """导出为 story_bible.md 格式"""
        lines = [f"# 世界观设定 — {self.genre}\n"]
        lines.append("## 地点图集\n")
        for loc in self.atlas.sort_by_completeness():
            lines.append(f"### {loc.name}（{loc.location_type.value}，完整度 {loc.completeness}%）")
            if loc.description:
                lines.append(f"- {loc.description}")
            if loc.ruler:
                lines.append(f"- 统治者：{loc.ruler}")
            if loc.population:
                lines.append(f"- 人口：{loc.population}")
            lines.append("")

        lines.append("## 势力网络\n")
        for fac in self.factions._factions.values():
            lines.append(f"### {fac.name}（{fac.faction_type.value}，实力 {fac.power_level}）")
            if fac.description:
                lines.append(f"- {fac.description}")
            if fac.goal:
                lines.append(f"- 目标：{fac.goal}")
            lines.append("")

        lines.append("## 历史时间线\n")
        lines.append(self.timeline.export_markdown())

        return "\n".join(lines)


# ══════════════════════════════════════════════════════
# 模块级便捷函数
# ══════════════════════════════════════════════════════


def create_world_builder(book_id: str = "", genre: str = "xuanhuan") -> WorldBuilder:
    """创建世界观构建器并自动初始化"""
    builder = WorldBuilder(book_id=book_id, genre=genre)
    builder.init_from_template()
    logger.info(
        f"WorldBuilder: 初始化 {genre} 世界观"
        f"（{builder.atlas.get_statistics()['total']}地点，"
        f"{len(builder.factions._factions)}势力）"
    )
    return builder
