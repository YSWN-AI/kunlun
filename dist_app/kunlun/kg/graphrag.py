"""
昆仑创作引擎 — GraphRAG 检索增强

基于知识图谱的检索增强生成（GraphRAG），纯规则实现，不调用 LLM。
支持实体识别、关系扩展、时序过滤、社区上下文聚合。
"""

from __future__ import annotations

import json
import re
from collections import deque
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from kunlun.kg.client import KGClient
    from kunlun.kg.community import CommunityDetector
    from kunlun.kg.temporal import TemporalRelationManager


class GraphRAGRetriever:
    """GraphRAG 检索器

    从知识图谱中检索与查询相关的实体、关系、社区信息，
    聚合成可直接注入 LLM prompt 的结构化上下文。
    """

    def __init__(
        self,
        kg_client: KGClient,
        temporal_manager: TemporalRelationManager | None = None,
        community_detector: CommunityDetector | None = None,
    ):
        self.kg = kg_client
        if temporal_manager is None:
            from kunlun.kg.temporal import TemporalRelationManager

            temporal_manager = TemporalRelationManager(kg_client)
        self.temporal = temporal_manager
        if community_detector is None:
            from kunlun.kg.community import CommunityDetector

            community_detector = CommunityDetector()
        self.community = community_detector

    # ─── 实体识别（纯规则） ───────────────────────────

    def _extract_entity_keywords(self, query_text: str) -> list[str]:
        """从查询文本中提取实体关键词（纯规则）

        策略：
        1. 去除停用词和标点
        2. 提取 2-6 字的中文名词短语
        3. 与已知实体名做精确/子串匹配
        """
        # 基础清洗
        _punct = r"[，。！？、；：\u201c\u201d\u2018\u2019（）【】\s,.!?;:'\"()\[\]]+"
        text = re.sub(_punct, " ", query_text)
        # 提取中文片段（2-6字）
        candidates = re.findall(r"[\u4e00-\u9fa5]{2,6}", text)
        # 也提取英文/数字实体
        candidates.extend(re.findall(r"[A-Za-z0-9_]{2,20}", text))
        # 去重保序
        seen: set[str] = set()
        keywords: list[str] = []
        for c in candidates:
            if c not in seen and len(c) >= 2:
                seen.add(c)
                keywords.append(c)
        return keywords

    def _match_entities(
        self,
        keywords: list[str],
        query_text: str = "",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """通过关键词匹配知识图谱中的实体

        优先精确匹配 name，其次子串匹配，最后用已知实体名在查询文本中做子串匹配。
        """
        conn = self.kg._get_graph_conn()
        matched: dict[str, dict[str, Any]] = {}

        for kw in keywords:
            if len(matched) >= limit:
                break
            # 精确匹配 name
            cursor = conn.execute(
                "SELECT id, type, name, properties FROM nodes WHERE name = ? LIMIT ?",
                (kw, limit),
            )
            for row in cursor.fetchall():
                if row["id"] not in matched:
                    matched[row["id"]] = self._node_to_entity(row)
            # 子串匹配 name
            if len(matched) < limit:
                cursor = conn.execute(
                    "SELECT id, type, name, properties FROM nodes "
                    "WHERE name LIKE ? AND name != ? LIMIT ?",
                    (f"%{kw}%", kw, limit),
                )
                for row in cursor.fetchall():
                    if row["id"] not in matched and len(matched) < limit:
                        matched[row["id"]] = self._node_to_entity(row)

        # 兜底：用已知实体名在查询文本中做子串匹配
        if query_text and len(matched) < limit:
            cursor = conn.execute("SELECT id, type, name, properties FROM nodes")
            for row in cursor.fetchall():
                if len(matched) >= limit:
                    break
                name = row["name"]
                if name and len(name) >= 2 and name in query_text and row["id"] not in matched:
                    matched[row["id"]] = self._node_to_entity(row)

        return list(matched.values())[:limit]

    @staticmethod
    def _node_to_entity(row) -> dict[str, Any]:
        try:
            props = json.loads(row["properties"] or "{}")
        except (json.JSONDecodeError, TypeError):
            props = {}
        return {
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "description": props.get("description", ""),
            "properties": props,
        }

    # ─── 关系扩展 ────────────────────────────────────

    def _expand_subgraph(
        self,
        seed_entities: list[dict[str, Any]],
        max_depth: int = 2,
        current_chapter: int = 0,
    ) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        """从种子实体出发，BFS 扩展邻域子图

        Returns:
            (entities_dict, relations_list)
        """
        conn = self.kg._get_graph_conn()
        entities: dict[str, dict[str, Any]] = {}
        relations: list[dict[str, Any]] = []
        visited: set[str] = set()

        queue: deque[tuple[str, int]] = deque()
        for ent in seed_entities:
            entities[ent["id"]] = ent
            queue.append((ent["id"], 0))

        while queue:
            node_id, depth = queue.popleft()
            if node_id in visited or depth >= max_depth:
                continue
            visited.add(node_id)

            # 查询出边
            cursor = conn.execute(
                "SELECT e.id, e.source_id, e.target_id, e.type, e.properties, "
                "n.id as tid, n.type as ttype, n.name as tname, n.properties as tprops "
                "FROM edges e JOIN nodes n ON e.target_id = n.id "
                "WHERE e.source_id = ?",
                (node_id,),
            )
            for row in cursor.fetchall():
                rel = self._edge_to_relation(row)
                if current_chapter > 0 and not self._is_relation_valid(rel, current_chapter):
                    continue
                relations.append(rel)
                if row["tid"] not in entities:
                    entities[row["tid"]] = {
                        "id": row["tid"],
                        "name": row["tname"],
                        "type": row["ttype"],
                        "description": "",
                        "properties": self._safe_json(row["tprops"]),
                    }
                if depth + 1 < max_depth:
                    queue.append((row["tid"], depth + 1))

            # 查询入边
            cursor = conn.execute(
                "SELECT e.id, e.source_id, e.target_id, e.type, e.properties, "
                "n.id as sid, n.type as stype, n.name as sname, n.properties as sprops "
                "FROM edges e JOIN nodes n ON e.source_id = n.id "
                "WHERE e.target_id = ?",
                (node_id,),
            )
            for row in cursor.fetchall():
                rel = self._edge_to_relation(row)
                if current_chapter > 0 and not self._is_relation_valid(rel, current_chapter):
                    continue
                relations.append(rel)
                if row["sid"] not in entities:
                    entities[row["sid"]] = {
                        "id": row["sid"],
                        "name": row["sname"],
                        "type": row["stype"],
                        "description": "",
                        "properties": self._safe_json(row["sprops"]),
                    }
                if depth + 1 < max_depth:
                    queue.append((row["sid"], depth + 1))

        return entities, relations

    @staticmethod
    def _safe_json(raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}

    def _edge_to_relation(self, row) -> dict[str, Any]:
        props = self._safe_json(row["properties"])
        return {
            "id": row["id"],
            "source": row["source_id"],
            "target": row["target_id"],
            "type": row["type"],
            "properties": props,
            "valid_from": props.get("valid_from_chapter", 0),
            "valid_to": props.get("valid_to_chapter"),
        }

    @staticmethod
    def _is_relation_valid(rel: dict[str, Any], chapter: int) -> bool:
        """判断关系在指定章节是否有效"""
        vf = rel.get("valid_from", 0)
        vt = rel.get("valid_to")
        return vf <= chapter and (vt is None or chapter < vt)

    # ─── 主检索接口 ───────────────────────────────────

    def retrieve(
        self,
        query_text: str,
        current_chapter: int = 0,
        max_entities: int = 10,
        max_depth: int = 2,
        include_communities: bool = True,
    ) -> dict[str, Any]:
        """GraphRAG 检索

        流程：实体识别 → 实体检索 → 关系扩展 → 时序过滤 → 社区上下文 → 上下文聚合

        Args:
            query_text: 查询文本
            current_chapter: 当前章节（>0 时启用水序过滤）
            max_entities: 最大返回实体数
            max_depth: 关系扩展最大跳数
            include_communities: 是否包含社区检测结果

        Returns:
            结构化检索结果
        """
        # 1. 实体识别
        keywords = self._extract_entity_keywords(query_text)
        logger.debug(f"[GraphRAG] 提取关键词: {keywords}")

        # 2. 实体检索
        seed_entities = self._match_entities(keywords, query_text=query_text, limit=max_entities)
        logger.debug(f"[GraphRAG] 匹配种子实体: {len(seed_entities)} 个")

        if not seed_entities:
            return self._empty_result(current_chapter)

        # 3. 关系扩展 + 4. 时序过滤
        entities, relations = self._expand_subgraph(
            seed_entities, max_depth=max_depth, current_chapter=current_chapter
        )

        # 5. 社区上下文
        communities_info: list[dict[str, Any]] = []
        if include_communities and len(entities) >= 3:
            communities_info = self._get_communities(entities, relations)

        # 6. 上下文聚合
        entity_list = list(entities.values())[:max_entities]
        subgraph_summary = self._build_subgraph_summary(entity_list, relations)
        context_text = self.build_context_prompt(
            {
                "entities": entity_list,
                "relations": relations,
                "communities": communities_info,
                "subgraph_summary": subgraph_summary,
            }
        )

        return {
            "entities": entity_list,
            "relations": relations,
            "subgraph_summary": subgraph_summary,
            "communities": communities_info,
            "context_text": context_text,
            "chapter": current_chapter,
        }

    def _get_communities(
        self,
        entities: dict[str, dict[str, Any]],
        relations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """对子图运行社区检测"""
        # 构建邻接表
        adj: dict[str, dict[str, float]] = {}
        for eid in entities:
            adj[eid] = {}
        from kunlun.kg.community import DEFAULT_WEIGHT, RELATION_WEIGHTS

        for rel in relations:
            src, tgt = rel["source"], rel["target"]
            if src in adj and tgt in adj:
                w = RELATION_WEIGHTS.get(rel["type"].upper(), DEFAULT_WEIGHT)
                adj[src][tgt] = adj[src].get(tgt, 0) + w
                adj[tgt][src] = adj[tgt].get(src, 0) + w

        # 移除孤立节点
        adj = {k: v for k, v in adj.items() if v}
        if len(adj) < 3:
            return []

        communities = self.community.louvain(adj, max_iter=5)
        summaries = self.community.get_community_summary(communities, self.kg)
        # 补充社区描述
        return [
            {
                "community_id": s["community_id"],
                "members": s["member_names"],
                "core_entities": s["core_names"],
                "description": (
                    f"社区{s['community_id']}（{s['size']}人），"
                    f"核心：{'、'.join(s['core_names'][:3])}，"
                    f"内部密度{s['density']}"
                ),
            }
            for s in summaries
        ]

    @staticmethod
    def _build_subgraph_summary(
        entities: list[dict[str, Any]], relations: list[dict[str, Any]]
    ) -> str:
        """构建子图文本摘要"""
        if not entities:
            return "无子图数据"
        name_map = {e["id"]: e["name"] for e in entities}
        lines = [f"子图包含 {len(entities)} 个实体、{len(relations)} 条关系。"]
        lines.append("实体：" + "、".join(e["name"] for e in entities[:10]))
        if relations:
            rel_lines = []
            for r in relations[:10]:
                s = name_map.get(r["source"], r["source"])
                t = name_map.get(r["target"], r["target"])
                rel_lines.append(f"{s}—[{r['type']}]→{t}")
            lines.append("关系：" + "；".join(rel_lines))
        return "\n".join(lines)

    # ─── 专用检索接口 ──────────────────────────────────

    def retrieve_for_character(
        self,
        character_name: str,
        current_chapter: int = 0,
        depth: int = 2,
    ) -> dict[str, Any]:
        """针对角色的 GraphRAG 检索

        返回角色档案 + 关系网络 + 社区归属
        """
        conn = self.kg._get_graph_conn()
        cursor = conn.execute(
            "SELECT id, type, name, properties FROM nodes WHERE name = ? AND type = 'character'",
            (character_name,),
        )
        row = cursor.fetchone()
        if not row:
            # 尝试模糊匹配
            cursor = conn.execute(
                "SELECT id, type, name, properties FROM nodes "
                "WHERE name LIKE ? AND type = 'character' LIMIT 1",
                (f"%{character_name}%",),
            )
            row = cursor.fetchone()
        if not row:
            return self._empty_result(current_chapter)

        seed = [self._node_to_entity(row)]
        entities, relations = self._expand_subgraph(
            seed, max_depth=depth, current_chapter=current_chapter
        )
        communities_info = self._get_communities(entities, relations) if len(entities) >= 3 else []
        entity_list = list(entities.values())
        subgraph_summary = self._build_subgraph_summary(entity_list, relations)
        context_text = self.build_context_prompt(
            {
                "entities": entity_list,
                "relations": relations,
                "communities": communities_info,
                "subgraph_summary": subgraph_summary,
            }
        )
        return {
            "character": seed[0],
            "entities": entity_list,
            "relations": relations,
            "subgraph_summary": subgraph_summary,
            "communities": communities_info,
            "context_text": context_text,
            "chapter": current_chapter,
        }

    def retrieve_for_world_state(self, current_chapter: int = 0) -> dict[str, Any]:
        """世界观状态检索

        返回所有规则/地点/势力的当前状态（时序过滤）
        """
        conn = self.kg._get_graph_conn()
        world_types = ("location", "faction", "rule", "world", "organization", "item")
        placeholders = ",".join("?" * len(world_types))
        cursor = conn.execute(
            f"SELECT id, type, name, properties FROM nodes WHERE type IN ({placeholders})",
            list(world_types),
        )
        entities: list[dict[str, Any]] = []
        for row in cursor.fetchall():
            ent = self._node_to_entity(row)
            entities.append(ent)

        # 获取这些实体间的关系
        entity_ids = [e["id"] for e in entities]
        relations: list[dict[str, Any]] = []
        if entity_ids:
            ph = ",".join("?" * len(entity_ids))
            cursor = conn.execute(
                f"SELECT * FROM edges WHERE source_id IN ({ph}) AND target_id IN ({ph})",
                entity_ids + entity_ids,
            )
            for row in cursor.fetchall():
                rel = self._edge_to_relation(row)
                if current_chapter > 0 and not self._is_relation_valid(rel, current_chapter):
                    continue
                relations.append(rel)

        subgraph_summary = self._build_subgraph_summary(entities, relations)
        context_text = self.build_context_prompt(
            {
                "entities": entities,
                "relations": relations,
                "communities": [],
                "subgraph_summary": subgraph_summary,
            }
        )
        return {
            "entities": entities,
            "relations": relations,
            "subgraph_summary": subgraph_summary,
            "communities": [],
            "context_text": context_text,
            "chapter": current_chapter,
        }

    # ─── 上下文构建 ───────────────────────────────────

    def build_context_prompt(self, graphrag_result: dict[str, Any]) -> str:
        """将 GraphRAG 结果格式化为可注入 prompt 的文本"""
        sections: list[str] = []

        entities = graphrag_result.get("entities", [])
        if entities:
            lines = ["【知识图谱实体】"]
            for e in entities[:15]:
                desc = e.get("description", "")
                extra = ""
                if desc:
                    extra = f"，{desc[:50]}"
                lines.append(f"- {e['name']}（{e['type']}）{extra}")
            sections.append("\n".join(lines))

        relations = graphrag_result.get("relations", [])
        if relations:
            name_map = {e["id"]: e["name"] for e in entities}
            lines = ["【实体关系】"]
            for r in relations[:20]:
                s = name_map.get(r["source"], r["source"])
                t = name_map.get(r["target"], r["target"])
                temporal = ""
                if r.get("valid_from", 0) > 0 or r.get("valid_to"):
                    vt = r.get("valid_to") or "至今"
                    temporal = f"（第{r['valid_from']}章~{vt}）"
                lines.append(f"- {s} —[{r['type']}]→ {t}{temporal}")
            sections.append("\n".join(lines))

        communities = graphrag_result.get("communities", [])
        if communities:
            lines = ["【社区/派系】"]
            for c in communities[:5]:
                members = "、".join(c.get("members", [])[:5])
                lines.append(f"- 社区{c['community_id']}：{members}")
            sections.append("\n".join(lines))

        summary = graphrag_result.get("subgraph_summary", "")
        if summary:
            sections.append(f"【子图摘要】\n{summary}")

        return "\n\n".join(sections) if sections else "无相关图谱上下文。"

    @staticmethod
    def _empty_result(chapter: int) -> dict[str, Any]:
        return {
            "entities": [],
            "relations": [],
            "subgraph_summary": "未找到匹配实体",
            "communities": [],
            "context_text": "未在知识图谱中找到相关实体。",
            "chapter": chapter,
        }
