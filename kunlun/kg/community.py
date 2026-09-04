"""
昆仑创作引擎 — 社区检测（纯 Python 实现）

实现 Louvain 和 Leiden 社区检测算法，不依赖 networkx/igraph 等外部库。
用于从知识图谱中识别角色派系、阵营、社交圈等结构。
"""

from __future__ import annotations

import random
from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kunlun.kg.client import KGClient

# 关系类型权重映射：正值促进同社区，负值抑制同社区
RELATION_WEIGHTS: dict[str, float] = {
    "ALLY": 1.0,
    "MEMBER": 0.8,
    "MASTER": 0.7,
    "LOVE": 0.6,
    "FRIEND": 0.5,
    "TEACHER": 0.5,
    "RIVAL": -0.3,
    "ENEMY": -0.5,
    "HATE": -0.5,
}

DEFAULT_WEIGHT = 0.3


class CommunityDetector:
    """社区检测器

    纯 Python 实现 Louvain / Leiden 算法，支持从 KG 构建邻接表。
    """

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    # ─── 邻接表构建 ──────────────────────────────────

    def build_adjacency_from_kg(
        self,
        kg_client: KGClient,
        entity_type: str = "character",
    ) -> dict[str, dict[str, float]]:
        """从知识图谱构建邻接表

        关系权重 = 关系类型权重 + 出现次数加成（每多一次 +0.1，上限2.0）

        Args:
            kg_client: KG 客户端
            entity_type: 实体类型过滤（默认 character）

        Returns:
            邻接表 {node_id: {neighbor_id: weight}}
        """
        conn = kg_client._get_graph_conn()
        # 查询指定类型的节点
        cursor = conn.execute("SELECT id, name FROM nodes WHERE type = ?", (entity_type,))
        node_ids = {row["id"] for row in cursor.fetchall()}

        adjacency: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for nid in node_ids:
            adjacency[nid]  # 确保孤立节点也在图中

        # 查询所有边（源或目标属于指定类型）
        cursor = conn.execute("SELECT source_id, target_id, type, properties FROM edges")
        for row in cursor.fetchall():
            src, tgt = row["source_id"], row["target_id"]
            if src not in node_ids or tgt not in node_ids:
                continue
            rel_type = row["type"].upper()
            base_weight = RELATION_WEIGHTS.get(rel_type, DEFAULT_WEIGHT)
            # 出现次数加成
            adjacency[src][tgt] += base_weight
            adjacency[tgt][src] += base_weight  # 无向图

        # 转换为普通 dict，限制权重范围
        result: dict[str, dict[str, float]] = {}
        for node, neighbors in adjacency.items():
            result[node] = {n: min(w, 2.0) for n, w in neighbors.items() if w != 0}
        return result

    # ─── Louvain 算法 ─────────────────────────────────

    def louvain(
        self,
        adjacency_dict: dict[str, dict[str, float]],
        max_iter: int = 10,
        resolution: float = 1.0,
    ) -> dict[str, int]:
        """Louvain 社区检测算法

        步骤：
        1. 初始化每个节点为独立社区
        2. 局部移动：对每个节点，尝试移入邻居社区，选择模块度增益最大的
        3. 社区聚合：将每个社区压缩为新节点，边权聚合
        4. 重复直到收敛或达到 max_iter

        Args:
            adjacency_dict: 邻接表 {node: {neighbor: weight}}
            max_iter: 最大迭代轮数
            resolution: 分辨率参数（越大社区越小）

        Returns:
            {node_id: community_id}
        """
        if not adjacency_dict:
            return {}

        # 节点列表
        nodes = list(adjacency_dict.keys())
        # 社区分配：初始每个节点独立社区
        community: dict[str, int] = {node: i for i, node in enumerate(nodes)}
        # 节点映射（用于聚合后追踪原始节点）
        node_to_original: dict[str, list[str]] = {node: [node] for node in nodes}

        current_adj = self._normalize_adjacency(adjacency_dict)

        for _ in range(max_iter):
            # Phase 1: 局部移动优化
            improved = self._local_moving(current_adj, community, resolution)
            if not improved:
                break

            # Phase 2: 社区聚合
            current_adj, community, node_to_original = self._aggregate(
                current_adj, community, node_to_original
            )
            if len(current_adj) <= 1:
                break

        # 将聚合后的社区映射回原始节点
        result: dict[str, int] = {}
        for super_node, originals in node_to_original.items():
            cid = community.get(super_node, 0)
            for orig in originals:
                result[orig] = cid
        return result

    def _local_moving(
        self,
        adj: dict[str, dict[str, float]],
        community: dict[str, int],
        resolution: float,
    ) -> bool:
        """Louvain 第一阶段：局部移动优化模块度

        Returns:
            是否有节点发生移动
        """
        nodes = list(adj.keys())
        self._rng.shuffle(nodes)
        total_improved = False

        # 计算总边权 m
        m = self._total_weight(adj)
        if m == 0:
            return False

        for _ in range(3):  # 每轮多遍扫描
            improved_this_pass = False
            for node in nodes:
                current_c = community[node]
                best_c = current_c
                best_gain = 0.0

                # 候选社区：邻居所在社区
                neighbor_communities: set[int] = set()
                for nb in adj.get(node, {}):
                    neighbor_communities.add(community[nb])

                for cand_c in neighbor_communities:
                    if cand_c == current_c:
                        continue
                    gain = self._modularity_gain(
                        node, cand_c, current_c, adj, community, m, resolution
                    )
                    if gain > best_gain + 1e-10:
                        best_gain = gain
                        best_c = cand_c

                if best_c != current_c:
                    community[node] = best_c
                    improved_this_pass = True
                    total_improved = True

            if not improved_this_pass:
                break

        return total_improved

    def _modularity_gain(
        self,
        node: str,
        target_c: int,
        current_c: int,
        adj: dict[str, dict[str, float]],
        community: dict[str, int],
        m: float,
        resolution: float,
    ) -> float:
        """计算将 node 从 current_c 移入 target_c 的模块度增益

        使用标准 Louvain 增益公式：
        ΔQ = [ (Σ_in + 2*k_i_in)/(2m) - γ*((Σ_tot + k_i)/(2m))^2 ]
             - [ Σ_in/(2m) - γ*(Σ_tot/(2m))^2 - γ*(k_i/(2m))^2 ]
        """
        # k_i: 节点的总度数（边权和）
        k_i = sum(adj.get(node, {}).values())
        if k_i == 0:
            return 0.0

        # 计算节点到目标社区的边权和
        k_i_in_target = 0.0
        for nb, w in adj.get(node, {}).items():
            if community.get(nb) == target_c:
                k_i_in_target += w

        # 目标社区的总度数（含节点自身暂时不算）
        sigma_tot_target = 0.0
        sigma_in_target = 0.0
        for n, neighbors in adj.items():
            if community.get(n) == target_c:
                sigma_tot_target += sum(neighbors.values())
                for nb, w in neighbors.items():
                    if community.get(nb) == target_c and n < nb:
                        sigma_in_target += w

        # 节点当前社区的总度数
        sigma_tot_current = 0.0
        for n, neighbors in adj.items():
            if community.get(n) == current_c and n != node:
                sigma_tot_current += sum(neighbors.values())

        two_m = 2.0 * m
        # 移入目标社区后的 Q 贡献
        q_after = (sigma_in_target + 2 * k_i_in_target) / two_m - resolution * (
            (sigma_tot_target + k_i) / two_m
        ) ** 2
        # 移出当前社区前的 Q 贡献
        q_before = (
            sigma_in_target / two_m
            - resolution * (sigma_tot_target / two_m) ** 2
            - resolution * (sigma_tot_current / two_m) ** 2
        )
        return q_after - q_before

    def _aggregate(
        self,
        adj: dict[str, dict[str, float]],
        community: dict[str, int],
        node_to_original: dict[str, list[str]],
    ) -> tuple[dict[str, dict[str, float]], dict[str, int], dict[str, list[str]]]:
        """Louvain 第二阶段：社区聚合

        将每个社区压缩为一个超级节点，社区间边权聚合。
        """
        # 社区 -> 超级节点ID
        comm_to_super: dict[int, str] = {}
        super_to_original: dict[str, list[str]] = {}
        for node, cid in community.items():
            if cid not in comm_to_super:
                super_id = f"super_{cid}"
                comm_to_super[cid] = super_id
                super_to_original[super_id] = []
            super_to_original[comm_to_super[cid]].extend(node_to_original.get(node, [node]))

        # 构建新邻接表
        new_adj: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for super_id in super_to_original:
            new_adj[super_id]  # 确保存在

        for src, neighbors in adj.items():
            src_super = comm_to_super[community[src]]
            for tgt, w in neighbors.items():
                tgt_super = comm_to_super[community[tgt]]
                if src_super != tgt_super:
                    new_adj[src_super][tgt_super] += w
                    new_adj[tgt_super][src_super] += w
                else:
                    # 社区内部边：自环（权重的一半，因为无向图双边计数）
                    new_adj[src_super][src_super] += w * 0.5

        new_community = {sid: i for i, sid in enumerate(new_adj.keys())}
        return dict(new_adj), new_community, super_to_original

    # ─── Leiden 算法（简化版） ─────────────────────────

    def leiden(
        self,
        adjacency_dict: dict[str, dict[str, float]],
        max_iter: int = 5,
        resolution: float = 1.0,
    ) -> dict[str, int]:
        """Leiden 社区检测算法（简化纯 Python 实现）

        在 Louvain 基础上增加社区精炼阶段（refinement phase）：
        1. 局部移动（同 Louvain）
        2. 精炼：在每个社区内部寻找子社区，确保连通性
        3. 聚合（基于精炼后的分区）

        Args:
            adjacency_dict: 邻接表
            max_iter: 最大迭代轮数
            resolution: 分辨率参数

        Returns:
            {node_id: community_id}
        """
        if not adjacency_dict:
            return {}

        nodes = list(adjacency_dict.keys())
        community: dict[str, int] = {node: i for i, node in enumerate(nodes)}
        node_to_original: dict[str, list[str]] = {node: [node] for node in nodes}
        current_adj = self._normalize_adjacency(adjacency_dict)

        for _ in range(max_iter):
            # Phase 1: 局部移动
            improved = self._local_moving(current_adj, community, resolution)
            # Phase 2: 精炼（在社区内部找子分区）
            refined = self._refine_communities(current_adj, community, resolution)
            if refined:
                community = refined
            if not improved and not refined:
                break
            # Phase 3: 聚合
            current_adj, community, node_to_original = self._aggregate(
                current_adj, community, node_to_original
            )
            if len(current_adj) <= 1:
                break

        result: dict[str, int] = {}
        for super_node, originals in node_to_original.items():
            cid = community.get(super_node, 0)
            for orig in originals:
                result[orig] = cid
        return result

    def _refine_communities(
        self,
        adj: dict[str, dict[str, float]],
        community: dict[str, int],
        resolution: float,
    ) -> dict[str, int] | None:
        """Leiden 精炼阶段：在每个社区内部寻找更细的子分区

        对每个社区，检查是否可以拆分为多个连通子社区以提升模块度。
        返回新的社区分配，若无改进返回 None。
        """
        # 按社区分组
        comm_nodes: dict[int, list[str]] = defaultdict(list)
        for node, cid in community.items():
            comm_nodes[cid].append(node)

        new_community = dict(community)
        next_cid = max(community.values()) + 1 if community else 0
        refined_any = False

        for cid, members in comm_nodes.items():
            if len(members) < 3:
                continue
            # 在社区内部构建子图
            sub_adj: dict[str, dict[str, float]] = {}
            member_set = set(members)
            for node in members:
                sub_adj[node] = {nb: w for nb, w in adj.get(node, {}).items() if nb in member_set}
            # 对子图运行一次局部移动
            sub_community = {n: i for i, n in enumerate(members)}
            m = self._total_weight(sub_adj)
            if m == 0:
                continue
            improved = self._local_moving(sub_adj, sub_community, resolution)
            if improved and len(set(sub_community.values())) > 1:
                # 应用精炼结果：子社区中最大的保留原 cid，其余分配新 cid
                sub_groups: dict[int, list[str]] = defaultdict(list)
                for node, sc in sub_community.items():
                    sub_groups[sc].append(node)
                # 按规模降序，最大的保留原 cid
                sorted_groups = sorted(sub_groups.values(), key=len, reverse=True)
                for i, group in enumerate(sorted_groups):
                    assign_cid = cid if i == 0 else next_cid
                    if i > 0:
                        next_cid += 1
                    for node in group:
                        new_community[node] = assign_cid
                refined_any = True

        return new_community if refined_any else None

    # ─── 辅助方法 ────────────────────────────────────

    @staticmethod
    def _normalize_adjacency(
        adj: dict[str, dict[str, float]],
    ) -> dict[str, dict[str, float]]:
        """确保邻接表对称且所有节点都有 entry"""
        result: dict[str, dict[str, float]] = {n: {} for n in adj}
        for src, neighbors in adj.items():
            for tgt, w in neighbors.items():
                result[src][tgt] = w
                result.setdefault(tgt, {})[src] = w
        return result

    @staticmethod
    def _total_weight(adj: dict[str, dict[str, float]]) -> float:
        """计算图的总边权（无向图每条边计一次）"""
        seen: set[tuple[str, str]] = set()
        total = 0.0
        for src, neighbors in adj.items():
            for tgt, w in neighbors.items():
                if src == tgt:
                    total += w  # 自环计一次
                    continue
                key = (src, tgt) if src < tgt else (tgt, src)
                if key not in seen:
                    seen.add(key)
                    total += w
        return total

    def calculate_modularity(
        self,
        adjacency_dict: dict[str, dict[str, float]],
        communities: dict[str, int],
    ) -> float:
        """计算模块度得分 Q

        Q = (1/2m) * Σ[A_ij - k_i*k_j/(2m)] * δ(c_i, c_j)
        """
        adj = self._normalize_adjacency(adjacency_dict)
        m = self._total_weight(adj)
        if m == 0:
            return 0.0
        two_m = 2.0 * m
        # 节点度数
        degree: dict[str, float] = {n: sum(adj[n].values()) for n in adj}
        q = 0.0
        seen: set[tuple[str, str]] = set()
        for src in adj:
            for tgt in adj:
                key = (src, tgt) if src <= tgt else (tgt, src)
                if key in seen:
                    continue
                seen.add(key)
                if communities.get(src) != communities.get(tgt):
                    continue
                a_ij = adj[src].get(tgt, 0.0)
                if src == tgt:
                    # 自环在无向图中 A_ii 已计入，度数项 k_i*k_i/(2m)
                    q += a_ij - degree[src] * degree[tgt] / two_m
                else:
                    # 无向边贡献 2*(A_ij - k_i*k_j/(2m))
                    q += 2 * (a_ij - degree[src] * degree[tgt] / two_m)
        return q / two_m

    @staticmethod
    def get_community_members(community_id: int, communities: dict[str, int]) -> list[str]:
        """获取指定社区的成员列表"""
        return [node for node, cid in communities.items() if cid == community_id]

    def get_community_summary(
        self,
        communities: dict[str, int],
        kg_client: KGClient,
    ) -> list[dict[str, Any]]:
        """获取社区摘要

        每个社区返回：community_id, size, core_entities（度数最高的节点）,
        member_names, density（社区内部边密度）
        """
        conn = kg_client._get_graph_conn()
        # 获取节点名称
        cursor = conn.execute("SELECT id, name FROM nodes")
        name_map = {row["id"]: row["name"] for row in cursor.fetchall()}

        # 按社区分组
        comm_members: dict[int, list[str]] = defaultdict(list)
        for node, cid in communities.items():
            comm_members[cid].append(node)

        summaries: list[dict[str, Any]] = []
        for cid, members in sorted(comm_members.items()):
            member_set = set(members)
            # 计算内部边数和度数
            internal_edges = 0
            degree_map: dict[str, int] = dict.fromkeys(members, 0)
            cursor = conn.execute(
                "SELECT source_id, target_id FROM edges WHERE source_id IN ({})".format(
                    ",".join("?" * len(members))
                ),
                members,
            )
            for row in cursor.fetchall():
                src, tgt = row["source_id"], row["target_id"]
                if src in degree_map:
                    degree_map[src] += 1
                if tgt in member_set and src in member_set:
                    internal_edges += 1
            # 核心节点：度数最高的前3个
            sorted_by_degree = sorted(degree_map.items(), key=lambda x: x[1], reverse=True)
            core = [n for n, _ in sorted_by_degree[:3]]
            # 密度：实际内部边 / 最大可能边数
            n = len(members)
            max_edges = n * (n - 1) / 2 if n > 1 else 1
            density = internal_edges / max_edges if max_edges > 0 else 0.0

            summaries.append(
                {
                    "community_id": cid,
                    "size": n,
                    "core_entities": core,
                    "core_names": [name_map.get(c, c) for c in core],
                    "member_names": [name_map.get(m, m) for m in members],
                    "density": round(density, 4),
                    "internal_edges": internal_edges,
                }
            )
        return summaries

    def detect_factions(
        self,
        communities: dict[str, int],
        kg_client: KGClient,
    ) -> list[dict[str, Any]]:
        """识别派系/阵营

        基于社区检测结果 + 关系类型分析：
        - 内部 ALLY/MEMBER/MASTER 关系多 → 紧密派系
        - 与其他社区 ENEMY/RIVAL 关系多 → 对立阵营
        """
        summaries = self.get_community_summary(communities, kg_client)
        conn = kg_client._get_graph_conn()

        comm_members: dict[int, set[str]] = defaultdict(set)
        for node, cid in communities.items():
            comm_members[cid].add(node)

        factions: list[dict[str, Any]] = []
        for summary in summaries:
            cid = summary["community_id"]
            members = comm_members[cid]
            if not members:
                continue
            # 统计内部关系类型
            placeholders = ",".join("?" * len(members))
            cursor = conn.execute(
                f"SELECT type, COUNT(*) as cnt FROM edges "
                f"WHERE source_id IN ({placeholders}) AND target_id IN ({placeholders}) "
                f"GROUP BY type",
                list(members) + list(members),
            )
            internal_types = {row["type"]: row["cnt"] for row in cursor.fetchall()}

            # 统计对外敌对关系
            enemy_count = 0
            members_list = list(members)
            for rel_type in ("ENEMY", "RIVAL", "HATE"):
                cursor = conn.execute(
                    f"SELECT COUNT(*) as cnt FROM edges "
                    f"WHERE type = ? AND ("
                    f"(source_id IN ({placeholders}) AND target_id NOT IN ({placeholders})) "
                    f"OR (target_id IN ({placeholders}) AND source_id NOT IN ({placeholders}))"
                    f")",
                    [rel_type] + members_list * 4,
                )
                row = cursor.fetchone()
                enemy_count += row["cnt"] if row else 0

            cohesion_score = sum(
                internal_types.get(t, 0) for t in ("ALLY", "MEMBER", "MASTER", "LOVE")
            )
            is_faction = cohesion_score >= 2 or summary["density"] >= 0.3

            factions.append(
                {
                    "community_id": cid,
                    "name": f"派系_{cid}",
                    "members": summary["member_names"],
                    "core": summary["core_names"],
                    "size": summary["size"],
                    "cohesion_score": cohesion_score,
                    "enemy_relations": enemy_count,
                    "is_faction": is_faction,
                    "internal_relation_types": internal_types,
                }
            )
        return factions
