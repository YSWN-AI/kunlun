"""
昆仑创作引擎 — 交互式世界图集 (WorldAtlas)

管理所有地点卡片，支持搜索、排序、统计、力导向关系数据。
"""

from __future__ import annotations

import json
from pathlib import Path

from kunlun.config import settings
from kunlun.worlds.types import LocationCard, LocationType

# ══════════════════════════════════════════════════════
# WorldAtlas — 交互式世界图集
# ══════════════════════════════════════════════════════


class WorldAtlas:
    """交互式世界图集 — StoryCraft Studio 设计理念

    管理所有地点卡片，支持搜索、排序、统计、力导向关系数据。
    """

    def __init__(self, book_id: str = "") -> None:
        self.book_id = book_id
        self._locations: dict[str, LocationCard] = {}
        self._data_dir = Path(settings.DATA_DIR) / "worlds" / book_id if book_id else None

    def add_location(self, location: LocationCard) -> None:
        location.completeness = location.calculate_completeness()
        self._locations[location.location_id] = location

    def get_location(self, location_id: str) -> LocationCard | None:
        return self._locations.get(location_id)

    def list_locations(self, location_type: LocationType | None = None) -> list[LocationCard]:
        result = list(self._locations.values())
        if location_type:
            result = [loc for loc in result if loc.location_type == location_type]
        return result

    def search(self, query: str) -> list[LocationCard]:
        query_lower = query.lower()
        return [
            loc
            for loc in self._locations.values()
            if query_lower in loc.name.lower() or query_lower in loc.description.lower()
        ]

    def sort_by_completeness(self, descending: bool = True) -> list[LocationCard]:
        return sorted(
            self._locations.values(), key=lambda loc: loc.completeness, reverse=descending
        )

    def get_statistics(self) -> dict:
        locations = list(self._locations.values())
        if not locations:
            return {"total": 0, "developed": 0, "avg_completeness": 0}
        developed = sum(1 for loc in locations if loc.completeness >= 50)
        avg = sum(loc.completeness for loc in locations) / len(locations)
        by_type: dict[str, int] = {}
        for loc in locations:
            t = loc.location_type.value
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "total": len(locations),
            "developed": developed,
            "avg_completeness": round(avg, 1),
            "by_type": by_type,
        }

    def get_force_graph_data(self) -> dict:
        """生成力导向图数据（节点+边）"""
        nodes = [
            {
                "id": loc.location_id,
                "name": loc.name,
                "type": loc.location_type.value,
                "completeness": loc.completeness,
            }
            for loc in self._locations.values()
        ]
        edges = [
            {
                "source": loc.location_id,
                "target": conn["to_id"],
                "type": conn.get("type", "adjacent"),
            }
            for loc in self._locations.values()
            for conn in loc.connections
            if conn.get("to_id") in self._locations
        ]
        return {"nodes": nodes, "edges": edges}

    def save(self) -> None:
        if not self._data_dir:
            return
        self._data_dir.mkdir(parents=True, exist_ok=True)
        data = {
            lid: {
                "location_id": loc.location_id,
                "name": loc.name,
                "location_type": loc.location_type.value,
                "parent_id": loc.parent_id,
                "description": loc.description,
                "climate": loc.climate,
                "population": loc.population,
                "ruler": loc.ruler,
                "resources": loc.resources,
                "connections": loc.connections,
                "completeness": loc.completeness,
            }
            for lid, loc in self._locations.items()
        }
        with (self._data_dir / "atlas.json").open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self) -> None:
        if not self._data_dir:
            return
        path = self._data_dir / "atlas.json"
        if path.exists():
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            for lid, d in data.items():
                self._locations[lid] = LocationCard(
                    location_id=d["location_id"],
                    name=d["name"],
                    location_type=LocationType(d.get("location_type", "other")),
                    parent_id=d.get("parent_id", ""),
                    description=d.get("description", ""),
                    climate=d.get("climate", ""),
                    population=d.get("population", ""),
                    ruler=d.get("ruler", ""),
                    resources=d.get("resources", []),
                    connections=d.get("connections", []),
                    completeness=d.get("completeness", 0),
                )
