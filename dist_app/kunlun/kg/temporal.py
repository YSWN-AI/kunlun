"""
昆仑创作引擎 — 时序关系管理

管理知识图谱中关系的时序属性（valid_from_chapter / valid_to_chapter），
支持关系的生命周期追踪、按章节查询、变更检测。

时序属性存储在 edges 表的 properties JSON 字段中，不修改表结构。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from kunlun.kg.client import KGClient


class TemporalRelationManager:
    """时序关系管理器

    通过 KGClient 操作 SQLite 图存储（或 Neo4j），在关系的 properties
    JSON 中维护 valid_from_chapter 和 valid_to_chapter。
    """

    def __init__(self, kg_client: KGClient):
        self.kg = kg_client

    # ─── 内部工具 ────────────────────────────────────

    def _get_graph_conn(self):
        """获取 KGClient 的图存储连接（SQLite 降级模式）"""
        return self.kg._get_graph_conn()

    @staticmethod
    def _parse_properties(raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}

    def _row_to_relation(self, row) -> dict[str, Any]:
        props = self._parse_properties(row["properties"])
        return {
            "id": row["id"],
            "source_id": row["source_id"],
            "target_id": row["target_id"],
            "type": row["type"],
            "properties": props,
            "valid_from_chapter": props.get("valid_from_chapter", 0),
            "valid_to_chapter": props.get("valid_to_chapter"),
        }

    # ─── 写入操作 ────────────────────────────────────

    def add_temporal_relation(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: dict | None = None,
        valid_from_chapter: int = 0,
        valid_to_chapter: int | None = None,
    ) -> bool:
        """添加带时序属性的关系

        Args:
            source_id: 源实体ID
            target_id: 目标实体ID
            rel_type: 关系类型
            properties: 附加属性
            valid_from_chapter: 关系生效起始章节
            valid_to_chapter: 关系失效章节（None 表示持续有效）

        Returns:
            是否创建成功
        """
        props = dict(properties or {})
        props["valid_from_chapter"] = valid_from_chapter
        props["valid_to_chapter"] = valid_to_chapter
        success = self.kg.create_relationship(source_id, target_id, rel_type, props)
        if success:
            logger.debug(
                f"[Temporal] 添加时序关系 {source_id} -[{rel_type}]-> {target_id} "
                f"(ch{valid_from_chapter}~{valid_to_chapter})"
            )
        return success

    def end_relation(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        end_chapter: int,
    ) -> int:
        """结束指定关系（设置 valid_to_chapter）

        会更新所有匹配 source/target/type 且尚未结束的关系。

        Args:
            source_id: 源实体ID
            target_id: 目标实体ID
            rel_type: 关系类型
            end_chapter: 结束章节

        Returns:
            更新的关系数量
        """
        conn = self._get_graph_conn()
        cursor = conn.execute(
            "SELECT id, properties FROM edges WHERE source_id = ? AND target_id = ? AND type = ?",
            (source_id, target_id, rel_type),
        )
        rows = cursor.fetchall()
        updated = 0
        for row in rows:
            props = self._parse_properties(row["properties"])
            # 仅更新尚未结束的关系
            if props.get("valid_to_chapter") is None:
                props["valid_to_chapter"] = end_chapter
                conn.execute(
                    "UPDATE edges SET properties = ? WHERE id = ?",
                    (json.dumps(props, ensure_ascii=False), row["id"]),
                )
                updated += 1
        conn.commit()
        if updated:
            logger.debug(
                f"[Temporal] 结束关系 {source_id} -[{rel_type}]-> {target_id} "
                f"于 ch{end_chapter}（更新{updated}条）"
            )
        return updated

    # ─── 查询操作 ────────────────────────────────────

    def get_relations_at_chapter(self, source_id: str, chapter: int) -> list[dict[str, Any]]:
        """获取指定章节时有效的所有关系（出边）

        有效条件：valid_from_chapter <= chapter < valid_to_chapter
        （valid_to_chapter 为 None 表示持续有效）
        """
        conn = self._get_graph_conn()
        cursor = conn.execute(
            "SELECT * FROM edges WHERE source_id = ?",
            (source_id,),
        )
        results = []
        for row in cursor.fetchall():
            rel = self._row_to_relation(row)
            vf = rel["valid_from_chapter"]
            vt = rel["valid_to_chapter"]
            if vf <= chapter and (vt is None or chapter < vt):
                results.append(rel)
        return results

    def get_relation_history(self, source_id: str, target_id: str) -> list[dict[str, Any]]:
        """获取两实体间关系的完整历史（含过期关系，按起始章节排序）"""
        conn = self._get_graph_conn()
        cursor = conn.execute(
            "SELECT * FROM edges WHERE source_id = ? AND target_id = ? "
            "ORDER BY json_extract(properties, '$.valid_from_chapter')",
            (source_id, target_id),
        )
        return [self._row_to_relation(row) for row in cursor.fetchall()]

    def get_active_relations(self, source_id: str, current_chapter: int) -> list[dict[str, Any]]:
        """获取当前活跃关系（出边 + 入边）"""
        conn = self._get_graph_conn()
        cursor = conn.execute(
            "SELECT * FROM edges WHERE source_id = ? OR target_id = ?",
            (source_id, source_id),
        )
        results = []
        for row in cursor.fetchall():
            rel = self._row_to_relation(row)
            vf = rel["valid_from_chapter"]
            vt = rel["valid_to_chapter"]
            if vf <= current_chapter and (vt is None or current_chapter < vt):
                results.append(rel)
        return results

    def detect_relation_changes(
        self, entity_id: str, from_chapter: int, to_chapter: int
    ) -> dict[str, list[dict[str, Any]]]:
        """检测实体在 [from_chapter, to_chapter] 区间内的关系变更

        Returns:
            {"added": [...], "ended": [...], "changed": [...]}
            - added: 在区间内新生效的关系
            - ended: 在区间内结束的关系
            - changed: properties 发生变化的关系（同一对实体同类型多条记录）
        """
        conn = self._get_graph_conn()
        cursor = conn.execute(
            "SELECT * FROM edges WHERE source_id = ? OR target_id = ?",
            (entity_id, entity_id),
        )
        all_rels = [self._row_to_relation(row) for row in cursor.fetchall()]

        added: list[dict[str, Any]] = []
        ended: list[dict[str, Any]] = []
        changed: list[dict[str, Any]] = []

        # 按 (source, target, type) 分组检测变更
        groups: dict[tuple[str, str, str], list[dict]] = {}
        for rel in all_rels:
            key = (rel["source_id"], rel["target_id"], rel["type"])
            groups.setdefault(key, []).append(rel)

        for rel in all_rels:
            vf = rel["valid_from_chapter"]
            vt = rel["valid_to_chapter"]
            # 新增：起始章节落在区间内
            if from_chapter <= vf <= to_chapter:
                added.append(rel)
            # 结束：终止章节落在区间内
            if vt is not None and from_chapter <= vt <= to_chapter:
                ended.append(rel)

        # 变更：同一对实体同类型存在多条记录（属性可能变化）
        for rels in groups.values():
            if len(rels) > 1:
                changed.extend(rels)

        return {"added": added, "ended": ended, "changed": changed}
