"""
分支剧情引擎 — BranchPlotEngine

核心能力:
  1. 分支点检测 — 基于冲突引擎/关键词/句式自动发现分支点
  2. 分支树管理 — 树形数据结构，支持增删改查
  3. 分支推荐 — 基于质量/流行度的分支推荐
  4. 冲突引擎集成 — 复用冲突检测结果生成分支点
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from kunlun.branch_plot.types import (
    BranchCondition,
    BranchConditionType,
    BranchNode,
    BranchPointType,
    BranchTree,
)
from kunlun.config import settings


@dataclass
class BranchRecommendation:
    """分支推荐结果"""

    node: BranchNode
    score: float
    reason: str
    suggested_chapter_range: tuple[int, int] = (0, 0)


class BranchPlotEngine:
    """分支剧情引擎 — 分支点检测 + 树管理 + 推荐"""

    # 分支触发关键词
    BRANCH_KEYWORDS: dict[BranchPointType, list[str]] = {
        BranchPointType.CHARACTER_DECISION: [
            "选择",
            "抉择",
            "决定",
            "要么",
            "还是",
            "该不该",
            "犹豫",
            "纠结",
            "到底",
            "权衡",
            "取舍",
        ],
        BranchPointType.CONFLICT_FORK: [
            "决战",
            "对峙",
            "谈判",
            "要么战",
            "要么和",
            "妥协",
            "鱼死网破",
            "两败俱伤",
            "撤退",
        ],
        BranchPointType.ROMANCE_FORK: [
            "表白",
            "拒绝",
            "接受",
            "选择谁",
            "三角",
            "吃醋",
            "误会",
            "分离",
            "和好",
            "坦白",
        ],
        BranchPointType.FACTION_CHOICE: [
            "加入",
            "投靠",
            "站队",
            "阵营",
            "投名状",
            "背叛",
            "脱离",
            "自立门户",
        ],
        BranchPointType.POWER_UP_PATH: [
            "修炼方向",
            "功法",
            "侧重",
            "剑道",
            "法术",
            "体修",
            "魂修",
            "丹道",
            "阵法",
        ],
        BranchPointType.MORAL_DILEMMA: [
            "杀不杀",
            "救不救",
            "说不说",
            "瞒不瞒",
            "牺牲",
            "保全",
            "原则",
            "底线",
        ],
        BranchPointType.REVELATION_BRANCH: [
            "真相",
            "秘密",
            "揭露",
            "摊牌",
            "承认",
            "隐瞒",
            "发现",
            "察觉",
        ],
    }

    def __init__(self, book_id: str = ""):
        self.book_id = book_id
        self.tree: BranchTree | None = None
        self._data_dir: Path | None = None
        self._branch_counter = 0

        if book_id:
            self._data_dir = settings.DATA_DIR / "branch_plot" / book_id
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    def _next_id(self) -> str:
        self._branch_counter += 1
        return f"branch_{self._branch_counter:04d}"

    # ─── 分支树管理 ──────────────────────────────

    def init_tree(self) -> BranchTree:
        """初始化分支树"""
        root = BranchNode(
            id="root",
            name="主线起点",
            description="故事起点",
            chapter=0,
            branch_type=BranchPointType.EVENT_OUTCOME,
            is_canon=True,
        )
        self.tree = BranchTree(book_id=self.book_id, root_id="root")
        self.tree.add_node(root)
        self.tree.current_path = ["root"]
        self._branch_counter = 1
        self._save()
        return self.tree

    def get_or_create_tree(self) -> BranchTree:
        if self.tree is None:
            return self.init_tree()
        return self.tree

    def add_branch(
        self,
        parent_id: str,
        name: str,
        description: str,
        chapter: int,
        branch_type: BranchPointType,
        conditions: list[BranchCondition] | None = None,
        conflict_ids: list[str] | None = None,
        character_ids: list[str] | None = None,
        is_canon: bool = False,
    ) -> BranchNode:
        """添加分支节点"""
        tree = self.get_or_create_tree()

        if parent_id not in tree.nodes:
            raise ValueError(f"父节点 {parent_id} 不存在")

        node = BranchNode(
            id=self._next_id(),
            name=name,
            description=description,
            chapter=chapter,
            branch_type=branch_type,
            parent_id=parent_id,
            conditions=conditions or [],
            conflict_ids=conflict_ids or [],
            character_ids=character_ids or [],
            is_canon=is_canon,
        )

        tree.add_node(node)
        parent = tree.nodes[parent_id]
        parent.children.append(node.id)

        if is_canon:
            tree.current_path = tree.get_path_to_root(node.id)

        self._save()
        logger.info(f"[BranchPlot] 添加分支: {node.id} ({name}) @ 第{chapter}章")
        return node

    def add_ending(self, node_id: str, ending_name: str) -> None:
        """标记节点为结局"""
        tree = self.get_or_create_tree()
        if node_id not in tree.nodes:
            raise ValueError(f"节点 {node_id} 不存在")
        node = tree.nodes[node_id]
        node.name = ending_name
        if node_id not in tree.endings:
            tree.endings.append(node_id)
        node.is_completed = True
        self._save()

    def get_available_branches(self, node_id: str) -> list[BranchNode]:
        """获取某节点的所有可用子分支"""
        tree = self.get_or_create_tree()
        return tree.get_children(node_id)

    def get_full_paths(self) -> list[list[BranchNode]]:
        """获取所有完整分支路径"""
        tree = self.get_or_create_tree()

        def dfs(node_id: str, path: list[str], all_paths: list[list[str]]):
            path.append(node_id)
            node = tree.nodes.get(node_id)
            if not node or not node.children or node.is_dead_end:
                all_paths.append(list(path))
            else:
                for child_id in node.children:
                    dfs(child_id, list(path), all_paths)

        all_path_ids: list[list[str]] = []
        dfs(tree.root_id, [], all_path_ids)

        tree.all_paths = all_path_ids
        return [
            [tree.nodes[pid] for pid in path_ids if pid in tree.nodes] for path_ids in all_path_ids
        ]

    # ─── 分支点检测 ──────────────────────────────

    def detect_branch_points(self, text: str, chapter: int, conflict_manager=None) -> list[dict]:
        """检测文本中的潜在分支点

        1. 关键词匹配
        2. 冲突引擎整合 (如果提供 conflict_manager)
        3. 对话句式分析
        """
        branch_points: list[dict] = []

        # 1. 关键词检测
        for branch_type, keywords in self.BRANCH_KEYWORDS.items():
            matched_kw = []
            total_weight = 0.0
            for kw in keywords:
                count = len(re.findall(kw, text))
                if count > 0:
                    matched_kw.append(kw)
                    total_weight += count
            if matched_kw and total_weight >= 1:
                branch_points.append(
                    {
                        "type": branch_type,
                        "confidence": min(1.0, total_weight / 8.0),
                        "keywords": matched_kw,
                        "chapter": chapter,
                        "source": "keyword",
                    }
                )

        # 2. 冲突引擎整合 — 利用现有冲突数据
        if conflict_manager:
            active_conflicts = conflict_manager.get_active_conflicts()
            for conflict in active_conflicts:
                branch_points.extend(
                    [
                        {
                            "type": BranchPointType.CONFLICT_FORK,
                            "confidence": 0.7,
                            "keywords": [conflict.name],
                            "chapter": chapter,
                            "source": "conflict_engine",
                            "conflict_id": conflict.id,
                            "conflict_name": conflict.name,
                        }
                    ]
                    if conflict.status in ("escalating", "climax")
                    else []
                )

        # 3. 对话句式 — 检测选择问句
        choice_patterns = [
            r"(.+还是.+\?)",
            r"(.+要么.+(要么.+))",
            r"(.+或者.+)",
            r"(.+到底该不该.+)",
        ]
        for pattern in choice_patterns:
            matches = re.findall(pattern, text)
            branch_points.extend(
                {
                    "type": BranchPointType.CHARACTER_DECISION,
                    "confidence": 0.4,
                    "keywords": [m[:30]],
                    "chapter": chapter,
                    "source": "dialogue",
                }
                for m in matches[:3]
            )

        return sorted(branch_points, key=lambda x: x["confidence"], reverse=True)

    def suggest_branch_options(self, branch_point: dict, _text: str) -> list[str]:
        """为检测到的分支点提供分支选项建议"""
        btype = branch_point["type"]

        suggestions: dict[BranchPointType, list[str]] = {
            BranchPointType.CONFLICT_FORK: [
                "正面迎战 — 以实力碾压",
                "策略周旋 — 以智取胜",
                "暂时撤退 — 以退为进",
                "寻求援军 — 借力打力",
            ],
            BranchPointType.CHARACTER_DECISION: [
                "选择冒险 — 高风险高回报",
                "选择稳妥 — 稳扎稳打",
                "选择第三条路 — 出其不意",
            ],
            BranchPointType.ROMANCE_FORK: [
                "主动表白 — 情感升温",
                "默默守候 — 暧昧延续",
                "产生误会 — 情感波折",
                "选择另一人 — 感情线转折",
            ],
            BranchPointType.FACTION_CHOICE: [
                "加入A派 — 获得势力庇护",
                "加入B派 — 获得独立资源",
                "保持中立 — 左右逢源",
                "自立门户 — 开辟新势力",
            ],
            BranchPointType.POWER_UP_PATH: [
                "专精一道 — 极致突破",
                "全面发展 — 稳中有升",
                "剑走偏锋 — 旁门左道",
                "意外奇遇 — 机缘巧合",
            ],
            BranchPointType.MORAL_DILEMMA: [
                "坚守原则 — 付出代价",
                "妥协退让 — 保全大局",
                "欺骗伪装 — 权宜之计",
            ],
            BranchPointType.REVELATION_BRANCH: [
                "全部坦白 — 信任建立",
                "部分隐藏 — 留有余地",
                "继续隐瞒 — 矛盾加深",
            ],
            BranchPointType.EVENT_OUTCOME: [
                "事件成功 — 正向推进",
                "事件失败 — 逆势翻盘",
                "事件意外 — 新线索出现",
            ],
            BranchPointType.SUBPLOT_INSERT: [
                "插入支线 — 丰富世界观",
                "暂时搁置 — 日后展开",
                "快速收束 — 不留悬念",
            ],
        }

        return suggestions.get(btype, ["正向发展", "逆向发展", "意外发展"])

    # ─── 分支推荐 ────────────────────────────────

    def recommend_branches(self, node_id: str, top_k: int = 3) -> list[BranchRecommendation]:
        """基于质量/流行度推荐最优分支"""
        tree = self.get_or_create_tree()

        if node_id not in tree.nodes:
            return []

        children = tree.get_children(node_id)
        if not children:
            return []

        recommendations = []
        for child in children:
            score = child.composite_score
            reasons = []
            if child.quality_score >= 0.7:
                reasons.append("高质量分支")
            if child.popularity_score >= 0.6:
                reasons.append("读者欢迎")
            if child.pleasure_point_count >= 3:
                reasons.append(f"爽点丰富({child.pleasure_point_count}个)")
            if child.is_canon:
                reasons.append("正史主线")
            if not reasons:
                reasons.append("可行分支")

            recommendations.append(
                BranchRecommendation(
                    node=child,
                    score=score,
                    reason="，".join(reasons),
                    suggested_chapter_range=(
                        child.chapter,
                        child.chapter + child.word_count_estimate // 2500,
                    ),
                )
            )

        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:top_k]

    def recommend_next_chapter_branch(
        self, current_chapter: int, context_text: str = ""
    ) -> list[BranchRecommendation]:
        """基于当前章节推荐下一步分支走向"""
        tree = self.get_or_create_tree()
        current_node_id = tree.current_path[-1] if tree.current_path else tree.root_id

        # 检测当前章节的分支点
        branch_points = self.detect_branch_points(context_text, current_chapter)
        if not branch_points:
            children = tree.get_children(current_node_id)
            if children:
                return self.recommend_branches(current_node_id)
            return []

        results = []
        for bp in branch_points[:3]:
            options = self.suggest_branch_options(bp, context_text)
            for i, option in enumerate(options):
                node = BranchNode(
                    id=f"suggest_{bp['type'].value}_{current_chapter}_{i}",
                    name=option,
                    description=f"第{current_chapter}章检测到{bp['type'].label}",
                    chapter=current_chapter,
                    branch_type=bp["type"],
                    parent_id=current_node_id,
                    quality_score=bp["confidence"],
                )
                results.append(
                    BranchRecommendation(
                        node=node,
                        score=bp["confidence"],
                        reason=f"检测到{bp['type'].label}",
                        suggested_chapter_range=(current_chapter, current_chapter + 3),
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:5]

    # ─── 统计与导出 ──────────────────────────────

    def get_statistics(self) -> dict:
        """获取分支树统计"""
        tree = self.get_or_create_tree()
        nodes = list(tree.nodes.values())
        return {
            "total_nodes": len(nodes),
            "total_paths": tree.path_count,
            "total_endings": tree.ending_count,
            "max_depth": self._max_depth(),
            "branch_types": {
                bpt.value: len([n for n in nodes if n.branch_type == bpt])
                for bpt in BranchPointType
                if any(n.branch_type == bpt for n in nodes)
            },
            "canon_path_length": len(tree.current_path),
            "avg_quality": (sum(n.quality_score for n in nodes) / max(len(nodes), 1)),
        }

    def _max_depth(self) -> int:
        tree = self.get_or_create_tree()

        def depth(node_id: str, visited: set) -> int:
            if node_id in visited:
                return 0
            visited.add(node_id)
            node = tree.nodes.get(node_id)
            if not node or not node.children:
                return 1
            return 1 + max(
                (depth(cid, visited.copy()) for cid in node.children),
                default=0,
            )

        return depth(tree.root_id, set())

    def export_for_browser(self) -> dict:
        """导出分支树供前端可视化使用"""
        tree = self.get_or_create_tree()
        nodes = []
        edges = []
        for node in tree.nodes.values():
            nodes.append(
                {
                    "id": node.id,
                    "label": node.name,
                    "chapter": node.chapter,
                    "type": node.branch_type.value,
                    "is_canon": node.is_canon,
                    "is_completed": node.is_completed,
                    "quality_score": node.quality_score,
                    "popularity_score": node.popularity_score,
                }
            )
            edges.extend(
                {
                    "source": node.id,
                    "target": child_id,
                    "is_canon": tree.nodes.get(
                        child_id,
                        BranchNode(
                            id="",
                            name="",
                            description="",
                            chapter=0,
                            branch_type=BranchPointType.EVENT_OUTCOME,
                        ),
                    ).is_canon,
                }
                for child_id in node.children
            )
        return {
            "book_id": self.book_id,
            "nodes": nodes,
            "edges": edges,
            "current_path": tree.current_path,
            "endings": tree.endings,
            "statistics": self.get_statistics(),
        }

    # ─── 持久化 ──────────────────────────────────

    def _save(self):
        if not self._data_dir or not self.tree:
            return
        data = {
            "book_id": self.book_id,
            "root_id": self.tree.root_id,
            "current_path": self.tree.current_path,
            "all_paths": self.tree.all_paths,
            "endings": self.tree.endings,
            "branch_counter": self._branch_counter,
            "nodes": {},
        }
        for nid, node in self.tree.nodes.items():
            data["nodes"][nid] = {
                "id": node.id,
                "name": node.name,
                "description": node.description,
                "chapter": node.chapter,
                "branch_type": node.branch_type.value,
                "parent_id": node.parent_id,
                "children": node.children,
                "conditions": [
                    {
                        "condition_type": c.condition_type.value,
                        "key": c.key,
                        "operator": c.operator,
                        "value": c.value,
                        "description": c.description,
                    }
                    for c in node.conditions
                ],
                "conflict_ids": node.conflict_ids,
                "character_ids": node.character_ids,
                "quality_score": node.quality_score,
                "popularity_score": node.popularity_score,
                "reader_votes": node.reader_votes,
                "word_count_estimate": node.word_count_estimate,
                "pleasure_point_count": node.pleasure_point_count,
                "tension_curve": node.tension_curve,
                "is_canon": node.is_canon,
                "is_completed": node.is_completed,
                "is_dead_end": node.is_dead_end,
            }
        (self._data_dir / "branch_tree.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2)
        )

    def _load(self):
        if not self._data_dir:
            return
        state_file = self._data_dir / "branch_tree.json"
        if not state_file.exists():
            return
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            self.tree = BranchTree(
                book_id=data["book_id"],
                root_id=data["root_id"],
            )
            self.tree.current_path = data.get("current_path", ["root"])
            self.tree.all_paths = data.get("all_paths", [])
            self.tree.endings = data.get("endings", [])
            self._branch_counter = data.get("branch_counter", 0)

            for nid, nd in data.get("nodes", {}).items():
                node = BranchNode(
                    id=nd["id"],
                    name=nd["name"],
                    description=nd["description"],
                    chapter=nd["chapter"],
                    branch_type=BranchPointType(nd["branch_type"]),
                    parent_id=nd.get("parent_id", ""),
                    children=nd.get("children", []),
                    conditions=[
                        BranchCondition(
                            condition_type=BranchConditionType(c["condition_type"]),
                            key=c["key"],
                            operator=c.get("operator", ">="),
                            value=c["value"],
                            description=c.get("description", ""),
                        )
                        for c in nd.get("conditions", [])
                    ],
                    conflict_ids=nd.get("conflict_ids", []),
                    character_ids=nd.get("character_ids", []),
                    quality_score=nd.get("quality_score", 0.0),
                    popularity_score=nd.get("popularity_score", 0.0),
                    reader_votes=nd.get("reader_votes", 0),
                    word_count_estimate=nd.get("word_count_estimate", 0),
                    pleasure_point_count=nd.get("pleasure_point_count", 0),
                    tension_curve=nd.get("tension_curve", []),
                    is_canon=nd.get("is_canon", False),
                    is_completed=nd.get("is_completed", False),
                    is_dead_end=nd.get("is_dead_end", False),
                )
                self.tree.nodes[nid] = node
        except Exception:
            logger.warning("分支树数据加载失败，使用空状态")


# ─── 工厂函数 ──────────────────────────────────

_branch_engines: dict[str, BranchPlotEngine] = {}


def get_branch_engine(book_id: str) -> BranchPlotEngine:
    if book_id not in _branch_engines:
        _branch_engines[book_id] = BranchPlotEngine(book_id)
    return _branch_engines[book_id]
