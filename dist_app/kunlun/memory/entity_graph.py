"""
昆仑创作引擎 — 实体关系图谱 (L3 语义记忆增强)

为语义记忆提供结构化的实体关系图，支持：
  - 带时序属性的关系（valid_from / valid_to）
  - 入/出/双向关系查询
  - 关系路径查找（BFS）
  - 邻域子图提取（GraphRAG 用）
  - 关系历史变更追踪
  - 序列化/反序列化

纯规则零 LLM，无外部服务依赖。

Author: 昆仑创作引擎
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any

# ══════════════════════════════════════════════════════
# 关系类型常量
# ══════════════════════════════════════════════════════


class RelationType:
    """实体关系类型常量"""

    ALLY = "ally"  # 盟友
    ENEMY = "enemy"  # 敌人
    MEMBER = "member"  # 成员（属于某势力）
    MASTER = "master"  # 师徒
    LOVE = "love"  # 恋情
    RIVAL = "rival"  # 对手
    LOCATED_IN = "located_in"  # 位于
    OWNS = "owns"  # 拥有
    KNOWS = "knows"  # 知晓（信息/秘密）
    REVEALED_TO = "revealed_to"  # 揭示给

    ALL_TYPES = [
        ALLY,
        ENEMY,
        MEMBER,
        MASTER,
        LOVE,
        RIVAL,
        LOCATED_IN,
        OWNS,
        KNOWS,
        REVEALED_TO,
    ]


# ══════════════════════════════════════════════════════
# 关系数据结构
# ══════════════════════════════════════════════════════


@dataclass
class EntityRelation:
    """实体关系（带时序属性）"""

    id: str
    source_id: str
    target_id: str
    rel_type: str
    attributes: dict[str, Any] = field(default_factory=dict)
    valid_from_chapter: int = 0
    valid_to_chapter: int | None = None  # None 表示持续有效
    created_at: float = field(default_factory=time.time)

    def is_valid_at(self, chapter: int) -> bool:
        """判断关系在指定章节是否有效"""
        if chapter < self.valid_from_chapter:
            return False
        return not (self.valid_to_chapter is not None and chapter > self.valid_to_chapter)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityRelation:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ══════════════════════════════════════════════════════
# 实体关系图谱
# ══════════════════════════════════════════════════════


class EntityRelationGraph:
    """实体关系图谱 — 支持时序、路径、邻域的结构化关系图"""

    def __init__(self):
        self.relations: dict[str, EntityRelation] = {}
        # 邻接表：entity_id -> [relation_id]（出边）
        self._outgoing: dict[str, list[str]] = {}
        # 逆邻接表：entity_id -> [relation_id]（入边）
        self._incoming: dict[str, list[str]] = {}
        # 关系历史：(source, target, rel_type) -> [relation_id]（按时间顺序）
        self._history: dict[tuple[str, str, str], list[str]] = {}
        self._relation_counter: int = 0

    def _next_relation_id(self) -> str:
        self._relation_counter += 1
        return f"rel_{self._relation_counter}_{int(time.time() * 1000) % 100000}"

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        attributes: dict[str, Any] | None = None,
        valid_from_chapter: int = 0,
        valid_to_chapter: int | None = None,
    ) -> EntityRelation:
        """添加带时序属性的关系

        Args:
            source_id: 源实体 ID
            target_id: 目标实体 ID
            rel_type: 关系类型（RelationType 常量）
            attributes: 关系属性字典
            valid_from_chapter: 关系起始章节
            valid_to_chapter: 关系结束章节（None 表示持续）

        Returns:
            创建的 EntityRelation 对象
        """
        rel_id = self._next_relation_id()
        relation = EntityRelation(
            id=rel_id,
            source_id=source_id,
            target_id=target_id,
            rel_type=rel_type,
            attributes=attributes or {},
            valid_from_chapter=valid_from_chapter,
            valid_to_chapter=valid_to_chapter,
        )
        self.relations[rel_id] = relation
        self._outgoing.setdefault(source_id, []).append(rel_id)
        self._incoming.setdefault(target_id, []).append(rel_id)

        history_key = (source_id, target_id, rel_type)
        self._history.setdefault(history_key, []).append(rel_id)
        return relation

    def get_relations(
        self,
        entity_id: str,
        direction: str = "both",
        rel_type: str | None = None,
    ) -> list[EntityRelation]:
        """获取实体的关系

        Args:
            entity_id: 实体 ID
            direction: "out"（出边）/ "in"（入边）/ "both"（双向）
            rel_type: 可选关系类型过滤

        Returns:
            关系列表
        """
        result: list[EntityRelation] = []

        if direction in ("out", "both"):
            for rel_id in self._outgoing.get(entity_id, []):
                rel = self.relations.get(rel_id)
                if rel and (rel_type is None or rel.rel_type == rel_type):
                    result.append(rel)

        if direction in ("in", "both"):
            for rel_id in self._incoming.get(entity_id, []):
                rel = self.relations.get(rel_id)
                if rel and (rel_type is None or rel.rel_type == rel_type):
                    # 避免双向时重复
                    if direction == "both" and rel.source_id == entity_id:
                        continue
                    result.append(rel)

        return result

    def get_relations_at_chapter(self, entity_id: str, chapter: int) -> list[EntityRelation]:
        """获取指定章节时有效的关系（时序过滤）

        Args:
            entity_id: 实体 ID
            chapter: 章节号

        Returns:
            在该章节有效的关系列表
        """
        all_relations = self.get_relations(entity_id, direction="both")
        return [r for r in all_relations if r.is_valid_at(chapter)]

    def get_relationship_path(
        self, source_id: str, target_id: str, max_depth: int = 3
    ) -> list[EntityRelation]:
        """查找两实体间的关系路径（BFS）

        Args:
            source_id: 起始实体 ID
            target_id: 目标实体 ID
            max_depth: 最大搜索深度

        Returns:
            路径上的关系列表（从 source 到 target），找不到返回空列表
        """
        if source_id == target_id:
            return []

        # BFS：queue 元素为 (current_entity, path_relations)
        queue: deque[tuple[str, list[EntityRelation]]] = deque()
        queue.append((source_id, []))
        visited: set[str] = {source_id}

        while queue:
            current, path = queue.popleft()
            if len(path) >= max_depth:
                continue

            for rel in self.get_relations(current, direction="out"):
                next_entity = rel.target_id
                if next_entity in visited:
                    continue
                new_path = [*path, rel]
                if next_entity == target_id:
                    return new_path
                visited.add(next_entity)
                queue.append((next_entity, new_path))

        return []

    def get_neighborhood(self, entity_id: str, depth: int = 1) -> dict[str, Any]:
        """获取实体邻域子图（GraphRAG 用）

        Args:
            entity_id: 中心实体 ID
            depth: 扩展深度

        Returns:
            含 entities（实体 ID 集合）和 relations（关系列表）的字典
        """
        visited_entities: set[str] = {entity_id}
        collected_relations: list[EntityRelation] = []
        current_frontier: set[str] = {entity_id}

        for _ in range(depth):
            next_frontier: set[str] = set()
            for ent in current_frontier:
                for rel in self.get_relations(ent, direction="both"):
                    if rel.id in {r.id for r in collected_relations}:
                        continue
                    collected_relations.append(rel)
                    other = rel.target_id if rel.source_id == ent else rel.source_id
                    if other not in visited_entities:
                        visited_entities.add(other)
                        next_frontier.add(other)
            current_frontier = next_frontier
            if not current_frontier:
                break

        return {
            "center": entity_id,
            "depth": depth,
            "entities": sorted(visited_entities),
            "relations": [r.to_dict() for r in collected_relations],
            "entity_count": len(visited_entities),
            "relation_count": len(collected_relations),
        }

    def get_relation_history(
        self, source_id: str, target_id: str, rel_type: str
    ) -> list[EntityRelation]:
        """获取关系的历史变更（时序版本）

        Args:
            source_id: 源实体 ID
            target_id: 目标实体 ID
            rel_type: 关系类型

        Returns:
            该关系的历史版本列表（按创建时间排序）
        """
        history_key = (source_id, target_id, rel_type)
        rel_ids = self._history.get(history_key, [])
        return [self.relations[rid] for rid in rel_ids if rid in self.relations]

    def update_relation_validity(
        self, relation_id: str, valid_to_chapter: int
    ) -> EntityRelation | None:
        """结束关系（如角色死亡、势力覆灭）

        Args:
            relation_id: 关系 ID
            valid_to_chapter: 关系结束章节

        Returns:
            更新后的关系对象，找不到返回 None
        """
        rel = self.relations.get(relation_id)
        if rel:
            rel.valid_to_chapter = valid_to_chapter
        return rel

    def get_all_entity_ids(self) -> set[str]:
        """获取图谱中所有实体 ID"""
        all_ids: set[str] = set()
        for rel in self.relations.values():
            all_ids.add(rel.source_id)
            all_ids.add(rel.target_id)
        return all_ids

    def to_dict(self) -> dict[str, Any]:
        """序列化图谱"""
        return {
            "relations": {k: v.to_dict() for k, v in self.relations.items()},
            "relation_counter": self._relation_counter,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityRelationGraph:
        """从字典反序列化图谱"""
        graph = cls()
        graph._relation_counter = data.get("relation_counter", 0)
        for rel_id, rel_data in data.get("relations", {}).items():
            relation = EntityRelation.from_dict(rel_data)
            graph.relations[rel_id] = relation
            graph._outgoing.setdefault(relation.source_id, []).append(rel_id)
            graph._incoming.setdefault(relation.target_id, []).append(rel_id)
            history_key = (relation.source_id, relation.target_id, relation.rel_type)
            graph._history.setdefault(history_key, []).append(rel_id)
        return graph
