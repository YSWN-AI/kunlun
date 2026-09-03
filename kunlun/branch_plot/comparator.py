"""
分支对比与合并决策模块

提供多分支对比、合并可行性评估、合并策略推荐与执行、分支网络分析等能力。
全部基于规则/算法实现，零LLM调用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from kunlun.branch_plot.types import BranchNode, BranchTree


@dataclass
class MergeDecision:
    """分支合并决策"""

    branch_ids: list[str]
    merge_strategy: str  # canon_absorb / parallel_merge / timeline_split / reject
    confidence: float = 0.0
    reason: str = ""
    merged_outline: str = ""
    risks: list[str] = field(default_factory=list)


class BranchComparator:
    """分支对比器与合并决策引擎"""

    def __init__(self, branch_engine: Any = None):
        self.branch_engine = branch_engine

    def _get_tree(self, tree: BranchTree | None = None) -> BranchTree | None:
        """获取分支树"""
        if tree is not None:
            return tree
        if self.branch_engine is not None:
            return getattr(self.branch_engine, "tree", None)
        return None

    def _get_node_metrics(self, node: BranchNode, tree: BranchTree) -> dict:
        """提取分支节点的对比指标"""
        # 子树深度
        subtree_depth = self._subtree_depth(node.id, tree)
        # 子树宽度 (所有后代节点数)
        subtree_width = self._subtree_width(node.id, tree)

        btype = node.branch_type
        btype_str = btype.value if hasattr(btype, "value") else str(btype)

        return {
            "id": node.id,
            "name": node.name,
            "quality_score": node.quality_score,
            "popularity_score": node.popularity_score,
            "composite_score": node.composite_score,
            "pleasure_point_count": node.pleasure_point_count,
            "word_count_estimate": node.word_count_estimate,
            "chapter": node.chapter,
            "branch_type": btype_str,
            "condition_count": len(node.conditions),
            "character_ids": list(node.character_ids),
            "conflict_ids": list(node.conflict_ids),
            "is_canon": node.is_canon,
            "is_dead_end": node.is_dead_end,
            "subtree_depth": subtree_depth,
            "subtree_width": subtree_width,
            "reader_votes": node.reader_votes,
        }

    def _subtree_depth(self, node_id: str, tree: BranchTree, visited: set | None = None) -> int:
        """计算子树深度"""
        if visited is None:
            visited = set()
        if node_id in visited:
            return 0
        visited.add(node_id)
        node = tree.nodes.get(node_id)
        if not node or not node.children:
            return 1
        return 1 + max(
            (self._subtree_depth(cid, tree, visited.copy()) for cid in node.children),
            default=0,
        )

    def _subtree_width(self, node_id: str, tree: BranchTree) -> int:
        """计算子树宽度 (后代节点总数)"""
        count = 0
        stack = [node_id]
        visited = set()
        while stack:
            nid = stack.pop()
            if nid in visited:
                continue
            visited.add(nid)
            node = tree.nodes.get(nid)
            if node:
                for cid in node.children:
                    if cid not in visited:
                        count += 1
                        stack.append(cid)
        return count

    # ─── 分支对比 ──────────────────────────────────

    def compare_branches(
        self, branch_a_id: str, branch_b_id: str, tree: BranchTree | None = None
    ) -> dict:
        """对比两个分支节点"""
        t = self._get_tree(tree)
        if t is None:
            return {"error": "no_tree_available"}

        node_a = t.nodes.get(branch_a_id)
        node_b = t.nodes.get(branch_b_id)
        if not node_a or not node_b:
            return {"error": "branch_not_found", "missing": [
                bid for bid, n in [(branch_a_id, node_a), (branch_b_id, node_b)] if n is None
            ]}

        metrics_a = self._get_node_metrics(node_a, t)
        metrics_b = self._get_node_metrics(node_b, t)

        # 计算各维度差异 (a - b)
        comparison = {
            "quality_score": round(metrics_a["quality_score"] - metrics_b["quality_score"], 4),
            "popularity_score": round(
                metrics_a["popularity_score"] - metrics_b["popularity_score"], 4
            ),
            "composite_score": round(
                metrics_a["composite_score"] - metrics_b["composite_score"], 4
            ),
            "pleasure_point_count": (
                metrics_a["pleasure_point_count"] - metrics_b["pleasure_point_count"]
            ),
            "word_count_estimate": (
                metrics_a["word_count_estimate"] - metrics_b["word_count_estimate"]
            ),
            "chapter_diff": metrics_a["chapter"] - metrics_b["chapter"],
            "condition_count_diff": metrics_a["condition_count"] - metrics_b["condition_count"],
            "subtree_depth_diff": metrics_a["subtree_depth"] - metrics_b["subtree_depth"],
            "subtree_width_diff": metrics_a["subtree_width"] - metrics_b["subtree_width"],
        }

        # 判定胜者 (基于综合得分)
        score_a = metrics_a["composite_score"]
        score_b = metrics_b["composite_score"]
        if abs(score_a - score_b) < 0.01:
            winner = "tie"
            reason = "两分支综合得分接近，建议并行发展或根据剧情需要选择"
        elif score_a > score_b:
            winner = "a"
            reason = self._build_winner_reason(metrics_a, metrics_b, "a")
        else:
            winner = "b"
            reason = self._build_winner_reason(metrics_b, metrics_a, "b")

        return {
            "branch_a": metrics_a,
            "branch_b": metrics_b,
            "comparison": comparison,
            "winner": winner,
            "reason": reason,
        }

    def _build_winner_reason(self, winner_m: dict, loser_m: dict, label: str) -> str:
        """构建胜者理由"""
        parts = [f"分支{label}({winner_m['name']})综合得分更高"]
        if winner_m["quality_score"] > loser_m["quality_score"]:
            parts.append("质量更优")
        if winner_m["popularity_score"] > loser_m["popularity_score"]:
            parts.append("读者欢迎度更高")
        if winner_m["pleasure_point_count"] > loser_m["pleasure_point_count"]:
            parts.append(f"爽点更多({winner_m['pleasure_point_count']}个)")
        if winner_m["is_canon"] and not loser_m["is_canon"]:
            parts.append("属于正史主线")
        return "，".join(parts)

    def compare_multiple_branches(
        self, branch_ids: list[str], tree: BranchTree | None = None
    ) -> list[dict]:
        """多分支对比排序 (按综合得分)"""
        t = self._get_tree(tree)
        if t is None:
            return []

        results = []
        for bid in branch_ids:
            node = t.nodes.get(bid)
            if node:
                metrics = self._get_node_metrics(node, t)
                results.append(metrics)

        results.sort(key=lambda m: m["composite_score"], reverse=True)

        # 添加排名
        for i, r in enumerate(results):
            r["rank"] = i + 1

        return results

    def get_branch_difference(
        self, branch_a_id: str, branch_b_id: str, tree: BranchTree | None = None
    ) -> dict:
        """获取分支差异详情"""
        t = self._get_tree(tree)
        if t is None:
            return {"error": "no_tree_available"}

        node_a = t.nodes.get(branch_a_id)
        node_b = t.nodes.get(branch_b_id)
        if not node_a or not node_b:
            return {"error": "branch_not_found"}

        # 条件差异
        def _cond_key(c):
            ct = c.condition_type
            ct_str = ct.value if hasattr(ct, "value") else str(ct)
            return (ct_str, c.key)

        cond_a_keys = {_cond_key(c) for c in node_a.conditions}
        cond_b_keys = {_cond_key(c) for c in node_b.conditions}
        only_a_conditions = [f"{ct}:{key}" for ct, key in (cond_a_keys - cond_b_keys)]
        only_b_conditions = [f"{ct}:{key}" for ct, key in (cond_b_keys - cond_a_keys)]

        # 角色差异
        chars_a = set(node_a.character_ids)
        chars_b = set(node_b.character_ids)
        only_a_chars = list(chars_a - chars_b)
        only_b_chars = list(chars_b - chars_a)
        shared_chars = list(chars_a & chars_b)

        # 冲突差异
        conf_a = set(node_a.conflict_ids)
        conf_b = set(node_b.conflict_ids)
        only_a_conflicts = list(conf_a - conf_b)
        only_b_conflicts = list(conf_b - conf_a)
        shared_conflicts = list(conf_a & conf_b)

        # 描述关键词差异 (简单分词)
        import re

        def extract_keywords(text: str) -> set[str]:
            # 简单提取中文关键词 (2字以上)
            words = re.findall(r"[\u4e00-\u9fa5]{2,}", text)
            return set(words)

        kw_a = extract_keywords(node_a.description)
        kw_b = extract_keywords(node_b.description)
        only_a_keywords = list(kw_a - kw_b)[:10]
        only_b_keywords = list(kw_b - kw_a)[:10]

        return {
            "branch_a": node_a.id,
            "branch_b": node_b.id,
            "conditions": {
                "only_in_a": only_a_conditions,
                "only_in_b": only_b_conditions,
                "shared_count": len(cond_a_keys & cond_b_keys),
            },
            "characters": {
                "only_in_a": only_a_chars,
                "only_in_b": only_b_chars,
                "shared": shared_chars,
                "overlap_ratio": len(shared_chars) / max(len(chars_a | chars_b), 1),
            },
            "conflicts": {
                "only_in_a": only_a_conflicts,
                "only_in_b": only_b_conflicts,
                "shared": shared_conflicts,
                "has_mutually_exclusive": bool(only_a_conflicts and only_b_conflicts),
            },
            "description_keywords": {
                "only_in_a": only_a_keywords,
                "only_in_b": only_b_keywords,
            },
            "branch_type_same": node_a.branch_type == node_b.branch_type,
            "chapter_diff": abs(node_a.chapter - node_b.chapter),
        }

    # ─── 分支合并决策 ──────────────────────────────

    def evaluate_merge_feasibility(
        self, branch_ids: list[str], tree: BranchTree | None = None
    ) -> dict:
        """评估分支合并的可行性"""
        t = self._get_tree(tree)
        if t is None:
            return {
                "feasible": False,
                "feasibility_score": 0.0,
                "factors": {},
                "recommended_strategy": "reject",
            }

        nodes: list[BranchNode] = []
        for bid in branch_ids:
            n = t.nodes.get(bid)
            if n is not None:
                nodes.append(n)
        if len(nodes) < 2:
            return {
                "feasible": False,
                "feasibility_score": 0.0,
                "factors": {},
                "recommended_strategy": "reject",
            }

        factors: dict[str, Any] = {}

        # 1. 章节接近度 (章节差<=5为高可行)
        chapters = [n.chapter for n in nodes]
        max_chapter_diff = max(chapters) - min(chapters)
        chapter_score = max(0.0, 1.0 - max_chapter_diff / 20.0)
        proximity_label = "，接近" if max_chapter_diff <= 5 else "，较远"
        factors["chapter_proximity"] = {
            "score": round(chapter_score, 3),
            "max_diff": max_chapter_diff,
            "detail": f"章节差{max_chapter_diff}{proximity_label}",
        }

        # 2. 角色重叠度
        all_chars = [set(n.character_ids) for n in nodes]
        union_chars = set().union(*all_chars) if all_chars else set()
        intersection_chars = all_chars[0].copy()
        for cs in all_chars[1:]:
            intersection_chars &= cs
        char_overlap = len(intersection_chars) / max(len(union_chars), 1)
        factors["character_overlap"] = {
            "score": round(char_overlap, 3),
            "shared_characters": list(intersection_chars),
            "detail": f"角色重叠率 {char_overlap*100:.1f}%",
        }

        # 3. 冲突兼容性 (是否有互斥冲突)
        all_conflicts = [set(n.conflict_ids) for n in nodes]
        has_mutually_exclusive = False
        for i in range(len(all_conflicts)):
            for j in range(i + 1, len(all_conflicts)):
                # 如果两个分支有完全不同的冲突且无交集，视为潜在互斥
                only_i = all_conflicts[i] - all_conflicts[j]
                only_j = all_conflicts[j] - all_conflicts[i]
                if only_i and only_j and not (all_conflicts[i] & all_conflicts[j]):
                    has_mutually_exclusive = True
                    break
        conflict_score = 0.2 if has_mutually_exclusive else 0.9
        factors["conflict_compatibility"] = {
            "score": conflict_score,
            "has_mutually_exclusive": has_mutually_exclusive,
            "detail": "存在互斥冲突" if has_mutually_exclusive else "冲突兼容",
        }

        # 4. 类型兼容性
        types = [n.branch_type for n in nodes]
        type_same = len(set(types)) == 1
        type_score = 0.9 if type_same else 0.5
        factors["type_compatibility"] = {
            "score": type_score,
            "all_same_type": type_same,
            "types": [t.value if hasattr(t, "value") else str(t) for t in types],
        }

        # 5. 正史状态
        canon_count = sum(1 for n in nodes if n.is_canon)
        canon_score = 0.9 if canon_count >= 1 else 0.4
        factors["canon_status"] = {
            "score": canon_score,
            "canon_count": canon_count,
            "detail": f"{canon_count}个正史分支" if canon_count else "无正史分支",
        }

        # 综合可行性得分
        weights = {
            "chapter_proximity": 0.25,
            "character_overlap": 0.25,
            "conflict_compatibility": 0.20,
            "type_compatibility": 0.15,
            "canon_status": 0.15,
        }
        feasibility_score = sum(
            factors[k]["score"] * weights[k] for k in weights
        )

        feasible = feasibility_score >= 0.5

        # 推荐策略
        if not feasible:
            recommended = "reject"
        elif canon_count >= 1 and len(nodes) == 2:
            recommended = "canon_absorb"
        elif type_same and char_overlap > 0.3:
            recommended = "parallel_merge"
        elif max_chapter_diff > 5:
            recommended = "timeline_split"
        else:
            recommended = "parallel_merge"

        return {
            "feasible": feasible,
            "feasibility_score": round(feasibility_score, 3),
            "factors": factors,
            "recommended_strategy": recommended,
        }

    def propose_merge(
        self,
        branch_ids: list[str],
        tree: BranchTree | None = None,
        strategy: str | None = None,
    ) -> MergeDecision:
        """生成分支合并建议"""
        t = self._get_tree(tree)
        if t is None:
            return MergeDecision(
                branch_ids=branch_ids,
                merge_strategy="reject",
                confidence=0.0,
                reason="无可用分支树",
            )

        nodes: list[BranchNode] = []
        for bid in branch_ids:
            n = t.nodes.get(bid)
            if n is not None:
                nodes.append(n)
        if len(nodes) < 2:
            return MergeDecision(
                branch_ids=branch_ids,
                merge_strategy="reject",
                confidence=0.0,
                reason="有效分支不足2个",
            )

        feasibility = self.evaluate_merge_feasibility(branch_ids, t)

        if strategy is None:
            strategy = feasibility["recommended_strategy"]

        confidence = feasibility["feasibility_score"] if strategy != "reject" else 0.0

        # 生成合并大纲摘要
        merged_outline = self._generate_merged_outline(nodes, strategy)

        # 列出风险
        risks = self._identify_merge_risks(strategy, feasibility)

        # 生成理由
        reason = self._build_merge_reason(nodes, strategy, feasibility)

        return MergeDecision(
            branch_ids=branch_ids,
            merge_strategy=strategy,
            confidence=round(confidence, 3),
            reason=reason,
            merged_outline=merged_outline,
            risks=risks,
        )

    def _generate_merged_outline(self, nodes: list[BranchNode], strategy: str) -> str:
        """生成合并后的大纲摘要"""
        names = "、".join(n.name for n in nodes)

        if strategy == "canon_absorb":
            canon_node = next((n for n in nodes if n.is_canon), nodes[0])
            others = [n for n in nodes if n.id != canon_node.id]
            return (
                f"正史分支「{canon_node.name}」吸收支线内容："
                f"将{'、'.join(o.name for o in others)}的关键事件、角色和冲突融入正史线，"
                f"被吸收分支标记为死路。合并后主线在第{canon_node.chapter}章继续推进。"
            )
        if strategy == "parallel_merge":
            return (
                f"平行合并「{names}」：两条线并行发展，"
                f"在后续章节汇合。各自保留核心冲突和角色弧光，汇合点产生剧情高潮。"
            )
        if strategy == "timeline_split":
            chapters = sorted(n.chapter for n in nodes)
            return (
                f"时间线拆分「{names}」：按章节顺序拆分为不同时间线事件，"
                f"第{chapters[0]}章至第{chapters[-1]}章依次发生，"
                f"通过伏笔和回忆串联。"
            )
        return f"不建议合并「{names}」：保留独立分支发展，避免剧情冲突和逻辑混乱。"

    def _identify_merge_risks(
        self, strategy: str, feasibility: dict
    ) -> list[str]:
        """识别合并风险"""
        risks: list[str] = []

        if strategy == "reject":
            return ["合并可行性低，强行合并可能导致剧情逻辑混乱"]

        factors = feasibility.get("factors", {})

        if factors.get("conflict_compatibility", {}).get("has_mutually_exclusive"):
            risks.append("分支间存在互斥冲突，合并后需处理冲突解决逻辑")

        char_overlap = factors.get("character_overlap", {}).get("score", 1.0)
        if char_overlap < 0.3:
            risks.append("角色重叠度低，合并后角色戏份分配需重新规划")

        chapter_diff = factors.get("chapter_proximity", {}).get("max_diff", 0)
        if chapter_diff > 5:
            risks.append(f"章节差距较大({chapter_diff}章)，时间线衔接需额外铺垫")

        if strategy == "canon_absorb":
            risks.append("被吸收分支的读者可能不满，需在正文中给予合理交代")
        elif strategy == "parallel_merge":
            risks.append("双线并行增加叙事复杂度，需注意节奏控制和汇合点设计")
        elif strategy == "timeline_split":
            risks.append("时间线拆分可能导致读者困惑，需明确时间标记")

        if not risks:
            risks.append("合并风险较低，注意保持剧情连贯性")

        return risks

    def _build_merge_reason(
        self, nodes: list[BranchNode], strategy: str, feasibility: dict
    ) -> str:
        """构建合并理由"""
        names = "、".join(n.name for n in nodes)
        score = feasibility.get("feasibility_score", 0)

        strategy_names = {
            "canon_absorb": "正史吸收",
            "parallel_merge": "平行合并",
            "timeline_split": "时间线拆分",
            "reject": "不合并",
        }

        if strategy == "reject":
            return f"「{names}」合并可行性得分{score:.2f}，低于阈值，建议保留独立分支"

        return (
            f"「{names}」合并可行性得分{score:.2f}，"
            f"推荐采用「{strategy_names.get(strategy, strategy)}」策略"
        )

    def execute_merge(self, merge_decision: MergeDecision, tree: BranchTree | None = None) -> dict:
        """执行合并 (修改分支树结构)"""
        t = self._get_tree(tree)
        if t is None:
            return {"success": False, "merged_node_id": "", "changes": ["无可用分支树"]}

        # 验证分支存在
        missing = [bid for bid in merge_decision.branch_ids if bid not in t.nodes]
        if missing:
            return {
                "success": False,
                "merged_node_id": "",
                "changes": [f"分支不存在: {', '.join(missing)}"],
            }

        changes: list[str] = []
        strategy = merge_decision.merge_strategy

        if strategy == "canon_absorb":
            result = self._execute_canon_absorb(merge_decision, t, changes)
        elif strategy == "parallel_merge":
            result = self._execute_parallel_merge(merge_decision, t, changes)
        elif strategy == "timeline_split":
            result = self._execute_timeline_split(merge_decision, t, changes)
        else:  # reject
            result = {
                "success": True,
                "merged_node_id": "",
                "changes": ["reject策略：不做任何修改，保留独立分支"],
            }

        logger.info(f"[BranchComparator] 执行合并策略={strategy}, 成功={result['success']}")
        return result

    def _execute_canon_absorb(
        self, decision: MergeDecision, tree: BranchTree, changes: list[str]
    ) -> dict:
        """执行正史吸收策略"""
        nodes = [tree.nodes[bid] for bid in decision.branch_ids]
        canon_node = next((n for n in nodes if n.is_canon), None)

        if canon_node is None:
            # 没有正史分支，选综合得分最高的作为正史
            canon_node = max(nodes, key=lambda n: n.composite_score)
            canon_node.is_canon = True
            changes.append(f"将「{canon_node.name}」设为正史分支")

        absorbed = [n for n in nodes if n.id != canon_node.id]

        for node in absorbed:
            # 合并角色
            for cid in node.character_ids:
                if cid not in canon_node.character_ids:
                    canon_node.character_ids.append(cid)
            # 合并冲突
            for cfid in node.conflict_ids:
                if cfid not in canon_node.conflict_ids:
                    canon_node.conflict_ids.append(cfid)
            # 合并条件
            existing_cond_keys = {
                (c.condition_type, c.key) for c in canon_node.conditions
            }
            for cond in node.conditions:
                key = (cond.condition_type, cond.key)
                if key not in existing_cond_keys:
                    canon_node.conditions.append(cond)
            # 标记为死路
            node.is_dead_end = True
            changes.append(
                f"吸收「{node.name}」: 合并{len(node.character_ids)}个角色、"
                f"{len(node.conflict_ids)}个冲突，标记为死路"
            )

        # 更新正史前路径
        tree.current_path = tree.get_path_to_root(canon_node.id)
        changes.append(f"更新正史路径至「{canon_node.name}」")

        return {
            "success": True,
            "merged_node_id": canon_node.id,
            "changes": changes,
        }

    def _execute_parallel_merge(
        self, decision: MergeDecision, tree: BranchTree, changes: list[str]
    ) -> dict:
        """执行平行合并策略: 创建合并节点，两个分支都指向新节点"""
        from kunlun.branch_plot.types import BranchPointType

        nodes = [tree.nodes[bid] for bid in decision.branch_ids]

        # 创建合并节点
        merge_id = f"merge_{'_'.join(n.id for n in nodes)}"
        if merge_id in tree.nodes:
            merge_id = f"{merge_id}_{len(tree.nodes)}"

        avg_chapter = sum(n.chapter for n in nodes) // len(nodes)
        merge_node = BranchNode(
            id=merge_id,
            name=f"合并节点: {'+'.join(n.name for n in nodes)}",
            description=f"平行合并节点，汇合{'、'.join(n.name for n in nodes)}两条线",
            chapter=avg_chapter + 1,
            branch_type=BranchPointType.EVENT_OUTCOME,
            parent_id="",  # 多父节点，通过children关联
            character_ids=list(
                set().union(*[set(n.character_ids) for n in nodes])
            ),
            conflict_ids=list(
                set().union(*[set(n.conflict_ids) for n in nodes])
            ),
            quality_score=sum(n.quality_score for n in nodes) / len(nodes),
            popularity_score=sum(n.popularity_score for n in nodes) / len(nodes),
        )
        tree.add_node(merge_node)

        # 所有分支都指向合并节点
        for node in nodes:
            if merge_id not in node.children:
                node.children.append(merge_id)
            changes.append(f"「{node.name}」指向合并节点「{merge_node.name}」")

        changes.append(f"创建合并节点「{merge_node.name}」(ID: {merge_id})")

        return {
            "success": True,
            "merged_node_id": merge_id,
            "changes": changes,
        }

    def _execute_timeline_split(
        self, decision: MergeDecision, tree: BranchTree, changes: list[str]
    ) -> dict:
        """执行时间线拆分策略: 不修改树结构，只在metadata中标记时间线"""
        nodes = [tree.nodes[bid] for bid in decision.branch_ids]
        # 按章节排序
        nodes.sort(key=lambda n: n.chapter)

        for i, node in enumerate(nodes):
            # 使用 description 追加时间线标记 (不新增字段，保持向后兼容)
            timeline_tag = f"[时间线{i+1}]"
            if timeline_tag not in node.description:
                node.description = f"{timeline_tag} {node.description}"
            changes.append(f"「{node.name}」标记为时间线{i+1} (第{node.chapter}章)")

        return {
            "success": True,
            "merged_node_id": "",
            "changes": changes,
        }

    # ─── 分支管理增强 ──────────────────────────────

    def get_branch_network(
        self, center_branch_id: str, tree: BranchTree | None = None, depth: int = 2
    ) -> dict:
        """获取以某分支为中心的分支网络"""
        t = self._get_tree(tree)
        if t is None:
            return {"error": "no_tree_available"}

        center = t.nodes.get(center_branch_id)
        if not center:
            return {"error": "branch_not_found", "branch_id": center_branch_id}

        # 父分支链
        parent_chain: list[dict] = []
        current = center.parent_id
        while current and current in t.nodes:
            pnode = t.nodes[current]
            parent_chain.append({"id": pnode.id, "name": pnode.name, "chapter": pnode.chapter})
            current = pnode.parent_id

        # 子分支 (递归到指定深度)
        children_tree = self._collect_children(center_branch_id, t, depth)

        # 兄弟分支
        siblings = []
        if center.parent_id and center.parent_id in t.nodes:
            parent = t.nodes[center.parent_id]
            for cid in parent.children:
                if cid != center_branch_id and cid in t.nodes:
                    snode = t.nodes[cid]
                    siblings.append(
                        {
                            "id": snode.id,
                            "name": snode.name,
                            "chapter": snode.chapter,
                            "composite_score": round(snode.composite_score, 3),
                        }
                    )

        return {
            "center": {
                "id": center.id,
                "name": center.name,
                "chapter": center.chapter,
                "is_canon": center.is_canon,
            },
            "parent_chain": parent_chain,
            "children_tree": children_tree,
            "siblings": siblings,
            "depth": depth,
        }

    def _collect_children(
        self, node_id: str, tree: BranchTree, max_depth: int, current_depth: int = 1
    ) -> list[dict]:
        """递归收集子分支"""
        if current_depth > max_depth:
            return []
        node = tree.nodes.get(node_id)
        if not node:
            return []

        result = []
        for cid in node.children:
            child = tree.nodes.get(cid)
            if child:
                result.append(
                    {
                        "id": child.id,
                        "name": child.name,
                        "chapter": child.chapter,
                        "is_canon": child.is_canon,
                        "composite_score": round(child.composite_score, 3),
                        "children": self._collect_children(
                            cid, tree, max_depth, current_depth + 1
                        ),
                    }
                )
        return result

    def find_divergence_point(
        self, branch_a_id: str, branch_b_id: str, tree: BranchTree | None = None
    ) -> str | None:
        """找到两个分支的分歧点 (最近公共祖先)"""
        t = self._get_tree(tree)
        if t is None:
            return None

        path_a = t.get_path_to_root(branch_a_id)
        path_b = t.get_path_to_root(branch_b_id)

        # 找最近公共祖先
        set_a = set(path_a)
        lca = None
        for nid in reversed(path_b):
            if nid in set_a:
                lca = nid
                break

        return lca

    def get_canon_branch_path(self, tree: BranchTree | None = None) -> list[BranchNode]:
        """获取正史分支路径 (从root到current_path末尾)"""
        t = self._get_tree(tree)
        if t is None:
            return []

        path_nodes = []
        for nid in t.current_path:
            node = t.nodes.get(nid)
            if node:
                path_nodes.append(node)
        return path_nodes

    def suggest_branch_pruning(
        self,
        tree: BranchTree | None = None,
        min_quality: float = 0.3,
        max_branches: int = 20,
    ) -> list[dict]:
        """建议修剪低质量分支"""
        t = self._get_tree(tree)
        if t is None:
            return []

        suggestions: list[dict] = []

        for node in t.nodes.values():
            # 跳过根节点和正史节点
            if node.id == t.root_id or node.is_canon:
                continue

            reasons = []
            # 低质量
            if node.quality_score < min_quality:
                reasons.append(f"质量分过低({node.quality_score:.2f} < {min_quality})")

            # 死路
            if node.is_dead_end:
                reasons.append("已标记为死路")

            # 无爽点且低流行度
            if node.pleasure_point_count == 0 and node.popularity_score < 0.2:
                reasons.append("无爽点且流行度低")

            # 叶子节点且无发展
            if node.is_leaf and not node.is_completed and node.quality_score < 0.4:
                reasons.append("叶子节点且质量不足，无发展潜力")

            if reasons:
                suggestions.append(
                    {
                        "branch_id": node.id,
                        "name": node.name,
                        "chapter": node.chapter,
                        "quality_score": node.quality_score,
                        "composite_score": round(node.composite_score, 3),
                        "reasons": reasons,
                        "action": "prune" if len(reasons) >= 2 else "review",
                    }
                )

        # 如果分支总数超过上限，额外建议修剪得分最低的
        non_canon_nodes = [
            n for n in t.nodes.values() if not n.is_canon and n.id != t.root_id
        ]
        if len(non_canon_nodes) > max_branches:
            sorted_nodes = sorted(non_canon_nodes, key=lambda n: n.composite_score)
            excess = len(non_canon_nodes) - max_branches
            existing_ids = {s["branch_id"] for s in suggestions}
            excess_reason = (
                f"分支总数超限({len(non_canon_nodes)} > {max_branches})，综合得分最低"
            )
            suggestions.extend(
                {
                    "branch_id": node.id,
                    "name": node.name,
                    "chapter": node.chapter,
                    "quality_score": node.quality_score,
                    "composite_score": round(node.composite_score, 3),
                    "reasons": [excess_reason],
                    "action": "prune",
                }
                for node in sorted_nodes[:excess]
                if node.id not in existing_ids
            )

        suggestions.sort(key=lambda s: s["composite_score"])
        return suggestions
