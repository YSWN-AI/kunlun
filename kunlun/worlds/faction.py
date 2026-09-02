"""
昆仑创作引擎 — 势力关系网络 (FactionNetwork)

Dramatica 理论中的势力对抗模型。
"""

from __future__ import annotations

from pathlib import Path

from kunlun.config import settings
from kunlun.worlds.types import FactionNode, RelationType

# ══════════════════════════════════════════════════════
# FactionNetwork — 势力关系网络
# ══════════════════════════════════════════════════════


class FactionNetwork:
    """势力关系网络 — Dramatica 理论中的势力对抗模型"""

    def __init__(self, book_id: str = "") -> None:
        self.book_id = book_id
        self._factions: dict[str, FactionNode] = {}
        self._data_dir = Path(settings.DATA_DIR) / "worlds" / book_id if book_id else None

    def add_faction(self, faction: FactionNode) -> None:
        self._factions[faction.faction_id] = faction

    def get_faction(self, faction_id: str) -> FactionNode | None:
        return self._factions.get(faction_id)

    def set_relation(
        self, source_id: str, target_id: str, relation_type: RelationType, strength: int = 0
    ) -> bool:
        """设置势力间关系，自动双向同步"""
        source = self._factions.get(source_id)
        target = self._factions.get(target_id)
        if not source or not target:
            return False

        # 更新源势力
        existing = source.get_relation_with(target_id)
        if existing:
            existing["type"] = relation_type.value
            existing["strength"] = strength
        else:
            source.relationships.append(
                {
                    "target_id": target_id,
                    "type": relation_type.value,
                    "strength": strength,
                }
            )

        # 双向同步
        reverse_type = relation_type.value
        if relation_type == RelationType.HOSTILE:
            reverse_type = RelationType.HOSTILE.value
        elif relation_type == RelationType.VASSAL:
            reverse_type = "overlord"
        existing_t = target.get_relation_with(source_id)
        if existing_t:
            existing_t["type"] = reverse_type
            existing_t["strength"] = strength
        else:
            target.relationships.append(
                {
                    "target_id": source_id,
                    "type": reverse_type,
                    "strength": strength,
                }
            )
        return True

    def detect_conflicts(self, active_factions: list[str]) -> list[dict]:
        """检测活跃势力间的冲突"""
        conflicts = []
        for i, fid1 in enumerate(active_factions):
            f1 = self._factions.get(fid1)
            if not f1:
                continue
            for fid2 in active_factions[i + 1 :]:
                rel = f1.get_relation_with(fid2)
                if rel and rel["type"] in ("hostile", "blood_feud", "rivalry"):
                    conflicts.append(
                        {
                            "faction_a": fid1,
                            "faction_b": fid2,
                            "relation": rel["type"],
                            "strength": rel["strength"],
                        }
                    )
        return conflicts

    def analyze_balance(self) -> dict:
        """势力平衡分析 — 防止一方独大"""
        factions = list(self._factions.values())
        if not factions:
            return {"balanced": True, "summary": "无势力数据"}

        max_power = max(f.power_level for f in factions)
        avg_power = sum(f.power_level for f in factions) / len(factions)

        if max_power > avg_power * 2.5:
            dominant = [f.name for f in factions if f.power_level == max_power]
            return {
                "balanced": False,
                "summary": f"势力失衡：{'、'.join(dominant)} 过于强大",
                "max_power": max_power,
                "avg_power": round(avg_power, 1),
                "recommendation": "建议增加对抗势力或削弱主导势力",
            }
        return {"balanced": True, "summary": "势力分布相对均衡"}

    def get_network_data(self) -> dict:
        """生成关系网络图数据"""
        nodes = [
            {
                "id": f.faction_id,
                "name": f.name,
                "type": f.faction_type.value,
                "power": f.power_level,
            }
            for f in self._factions.values()
        ]
        edges = []
        seen = set()
        for f in self._factions.values():
            for rel in f.relationships:
                key = tuple(sorted([f.faction_id, rel["target_id"]]))
                if key not in seen:
                    seen.add(key)
                    edges.append(
                        {
                            "source": f.faction_id,
                            "target": rel["target_id"],
                            "type": rel["type"],
                            "strength": rel.get("strength", 0),
                        }
                    )
        return {"nodes": nodes, "edges": edges}
