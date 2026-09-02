"""
outline 引擎核心实现
大纲智能调整 + 影响范围传播

对标长篇创作工具的大纲管理能力，
支持节点增删改 + 影响范围自动传播 + 变更历史追溯。

Author: 昆仑创作引擎
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from loguru import logger

from kunlun.config import settings

# ══════════════════════════════════════════════════════
# 枚举与数据类
# ══════════════════════════════════════════════════════


class OperationType(StrEnum):
    """操作类型"""

    ADD = "add"
    DELETE = "delete"
    MODIFY = "modify"
    MOVE = "move"
    SPLIT = "split"
    MERGE = "merge"

    @property
    def label(self) -> str:
        labels = {
            "add": "新增",
            "delete": "删除",
            "modify": "修改",
            "move": "移动",
            "split": "拆分",
            "merge": "合并",
        }
        return labels.get(self.value, self.value)


class ImpactSeverity(StrEnum):
    """影响严重度"""

    NONE = "none"  # 无影响
    LOW = "low"  # 低 — 仅影响当前章
    MEDIUM = "medium"  # 中 — 影响后续3-5章
    HIGH = "high"  # 高 — 影响后续5-15章
    CRITICAL = "critical"  # 严重 — 影响全局

    @property
    def affected_chapters(self) -> tuple[int, int]:
        return {
            "none": (0, 0),
            "low": (0, 1),
            "medium": (1, 5),
            "high": (5, 15),
            "critical": (15, 999),
        }.get(self.value, (0, 0))


@dataclass
class OutlineNode:
    """大纲节点"""

    id: str
    chapter: int
    title: str
    summary: str = ""
    key_events: list[str] = field(default_factory=list)
    characters_involved: list[str] = field(default_factory=list)
    foreshadowing_planted: list[str] = field(default_factory=list)
    foreshadowing_resolved: list[str] = field(default_factory=list)
    parent_id: str = ""
    children_ids: list[str] = field(default_factory=list)
    order: int = 0
    status: str = "planned"  # planned / writing / completed / skipped

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"


@dataclass
class ChangeHistory:
    """变更历史条目"""

    operation: OperationType
    node_id: str
    chapter: int
    timestamp: str = ""
    description: str = ""
    old_value: dict | None = None
    new_value: dict | None = None
    impact: ImpactSeverity = ImpactSeverity.NONE
    affected_chapters: list[int] = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()


@dataclass
class AdjustmentPlan:
    """调整计划 — 一次大纲变更的完整影响分析"""

    operation: OperationType
    target_node: OutlineNode
    impact: ImpactSeverity
    affected_nodes: list[OutlineNode] = field(default_factory=list)
    ripple_effects: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    auto_propagate: bool = True

    @property
    def affected_count(self) -> int:
        return len(self.affected_nodes)


# ══════════════════════════════════════════════════════
# 大纲调整器
# ══════════════════════════════════════════════════════


class OutlineAdjuster:
    """大纲智能调整器"""

    def __init__(self, book_id: str = ""):
        self.book_id = book_id
        self.nodes: dict[str, OutlineNode] = {}
        self.history: list[ChangeHistory] = []
        self._data_dir: Path | None = None
        if book_id:
            self._data_dir = settings.DATA_DIR / "outline" / book_id
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    # ── 节点操作 ────────────────────────────────────────

    def add_node(self, node: OutlineNode, auto_reorder: bool = True) -> AdjustmentPlan:
        """添加大纲节点"""
        self.nodes[node.id] = node

        if auto_reorder:
            self._reorder_chapters()

        impact = ImpactSeverity.LOW
        affected = self._find_affected_nodes(node.id, "add")

        plan = AdjustmentPlan(
            operation=OperationType.ADD,
            target_node=node,
            impact=impact,
            affected_nodes=affected,
            ripple_effects=[f"新增第{node.chapter}章 {node.title}"],
            suggestions=[f"确认第{node.chapter}章与前后章节衔接"],
        )

        self._record_history(
            ChangeHistory(
                operation=OperationType.ADD,
                node_id=node.id,
                chapter=node.chapter,
                description=f"新增章节: {node.title}",
                new_value=self._node_to_dict(node),
                impact=impact,
                affected_chapters=[n.chapter for n in affected],
            )
        )

        self._save()
        return plan

    def delete_node(self, node_id: str) -> AdjustmentPlan:
        """删除大纲节点"""
        node = self.nodes.pop(node_id, None)
        if not node:
            raise ValueError(f"节点不存在: {node_id}")

        # 删除子节点
        for child_id in node.children_ids:
            self.nodes.pop(child_id, None)

        impact = ImpactSeverity.MEDIUM if node.children_ids else ImpactSeverity.LOW
        affected = self._find_affected_nodes(node_id, "delete")

        plan = AdjustmentPlan(
            operation=OperationType.DELETE,
            target_node=node,
            impact=impact,
            affected_nodes=affected,
            ripple_effects=[f"删除第{node.chapter}章 {node.title}"]
            + ([f"同时删除 {len(node.children_ids)} 个子节点"] if node.children_ids else []),
            suggestions=[
                f"第{node.chapter}章删除后，前后章节衔接需检查",
                "如有伏笔在删除章节中，需在后续章节补充",
            ],
        )

        self._record_history(
            ChangeHistory(
                operation=OperationType.DELETE,
                node_id=node_id,
                chapter=node.chapter,
                description=f"删除章节: {node.title}",
                old_value=self._node_to_dict(node),
                impact=impact,
                affected_chapters=[n.chapter for n in affected],
            )
        )

        self._save()
        return plan

    def modify_node(self, node_id: str, updates: dict) -> AdjustmentPlan:
        """修改大纲节点"""
        node = self.nodes.get(node_id)
        if not node:
            raise ValueError(f"节点不存在: {node_id}")

        old_value = self._node_to_dict(node)

        # 应用更新
        for key, value in updates.items():
            if hasattr(node, key):
                setattr(node, key, value)

        impact = self._assess_modify_impact(old_value, updates)
        affected = self._find_affected_nodes(node_id, "modify")

        plan = AdjustmentPlan(
            operation=OperationType.MODIFY,
            target_node=node,
            impact=impact,
            affected_nodes=affected,
            suggestions=self._generate_modify_suggestions(updates, impact),
        )

        self._record_history(
            ChangeHistory(
                operation=OperationType.MODIFY,
                node_id=node_id,
                chapter=node.chapter,
                description=f"修改章节: {node.title}",
                old_value=old_value,
                new_value=self._node_to_dict(node),
                impact=impact,
                affected_chapters=[n.chapter for n in affected],
            )
        )

        self._save()
        return plan

    def move_node(self, node_id: str, new_chapter: int) -> AdjustmentPlan:
        """移动大纲节点"""
        node = self.nodes.get(node_id)
        if not node:
            raise ValueError(f"节点不存在: {node_id}")

        old_chapter = node.chapter
        old_value = self._node_to_dict(node)
        node.chapter = new_chapter

        distance = abs(new_chapter - old_chapter)
        impact = (
            ImpactSeverity.HIGH
            if distance > 10
            else ImpactSeverity.MEDIUM
            if distance > 3
            else ImpactSeverity.LOW
        )

        affected = self._find_affected_nodes(node_id, "move")

        plan = AdjustmentPlan(
            operation=OperationType.MOVE,
            target_node=node,
            impact=impact,
            affected_nodes=affected,
            ripple_effects=[f"第{old_chapter}章移至第{new_chapter}章"],
            suggestions=[
                f"章节移动跨度{distance}章，需检查伏笔和剧情线的连贯性",
                "建议重新审视受影响章节的衔接过渡",
            ],
        )

        self._record_history(
            ChangeHistory(
                operation=OperationType.MOVE,
                node_id=node_id,
                chapter=node.chapter,
                description=f"移动章节: {old_chapter}→{new_chapter}",
                old_value=old_value,
                new_value=self._node_to_dict(node),
                impact=impact,
                affected_chapters=[n.chapter for n in affected],
            )
        )

        self._save()
        return plan

    def split_node(self, node_id: str, split_at: str, new_title: str = "") -> AdjustmentPlan:
        """拆分大纲节点"""
        node = self.nodes.get(node_id)
        if not node:
            raise ValueError(f"节点不存在: {node_id}")

        old_value = self._node_to_dict(node)

        # 创建两个新节点
        new_id_1 = f"{node_id}_a"
        new_id_2 = f"{node_id}_b"

        node_a = OutlineNode(
            id=new_id_1,
            chapter=node.chapter,
            title=node.title + "(上)",
            summary=f"{node.summary}\n[拆分点: {split_at}]",
            characters_involved=node.characters_involved.copy(),
            order=node.order,
        )
        node_b = OutlineNode(
            id=new_id_2,
            chapter=int(node.chapter + 0.5),  # 临时章号
            title=new_title or node.title + "(下)",
            summary=f"[拆分自第{node.chapter}章] {node.summary}",
            characters_involved=node.characters_involved.copy(),
            order=node.order + 1,
        )

        # 替换原节点
        del self.nodes[node_id]
        self.nodes[new_id_1] = node_a
        self.nodes[new_id_2] = node_b
        self._reorder_chapters()

        plan = AdjustmentPlan(
            operation=OperationType.SPLIT,
            target_node=node,
            impact=ImpactSeverity.MEDIUM,
            affected_nodes=[node_a, node_b],
            ripple_effects=[f"第{node.chapter}章拆分为两章"],
            suggestions=["拆分后的两章各需独立的高潮/结尾", "确保拆分点不会打断关键剧情"],
        )

        self._record_history(
            ChangeHistory(
                operation=OperationType.SPLIT,
                node_id=node_id,
                chapter=node.chapter,
                description=f"拆分章节: {node.title}",
                old_value=old_value,
                impact=ImpactSeverity.MEDIUM,
            )
        )

        self._save()
        return plan

    # ── 影响分析 ────────────────────────────────────────

    def _find_affected_nodes(self, node_id: str, _operation: str) -> list[OutlineNode]:
        """查找受影响节点"""
        node = self.nodes.get(node_id)
        if not node:
            return []

        affected: list[OutlineNode] = []
        for n in self.nodes.values():
            if n.id == node_id:
                continue

            # 同一章的后续部分
            if n.chapter == node.chapter and n.order > node.order:
                affected.append(n)

            # 后续章节
            if n.chapter > node.chapter:
                affected.append(n)

            # 引用当前节点作为父节点
            if n.parent_id == node_id:
                affected.append(n)

            # 关联的角色
            if set(n.characters_involved) & set(node.characters_involved):
                affected.append(n)

        # 去重
        seen = set()
        unique: list[OutlineNode] = []
        for n in affected:
            if n.id not in seen:
                seen.add(n.id)
                unique.append(n)

        return sorted(unique, key=lambda x: (x.chapter, x.order))

    def _assess_modify_impact(self, _old_value: dict, updates: dict) -> ImpactSeverity:
        """评估修改的影响程度"""
        # 修改标题 → 低影响
        if set(updates.keys()) <= {"title"}:
            return ImpactSeverity.LOW

        # 修改摘要 → 中影响
        if set(updates.keys()) <= {"title", "summary"}:
            return ImpactSeverity.LOW

        # 修改关键事件/角色 → 高影响
        if "key_events" in updates or "characters_involved" in updates:
            return ImpactSeverity.HIGH

        # 修改伏笔 → 严重影响
        if "foreshadowing_planted" in updates or "foreshadowing_resolved" in updates:
            return ImpactSeverity.CRITICAL

        return ImpactSeverity.MEDIUM

    def _generate_modify_suggestions(self, updates: dict, impact: ImpactSeverity) -> list[str]:
        """生成修改建议"""
        suggestions: list[str] = []
        if "key_events" in updates:
            suggestions.append("关键事件变更需同步更新后续章节的引用")
        if "characters_involved" in updates:
            suggestions.append("角色变更需确认角色弧光的连贯性")
        if "foreshadowing_planted" in updates:
            suggestions.append("新增伏笔需确保后续章节有对应回收")
        if impact >= ImpactSeverity.HIGH:
            suggestions.append("高影响变更，建议重新审查受影响的章节")
        return suggestions

    # ── 辅助方法 ────────────────────────────────────────

    def _reorder_chapters(self):
        """重排章节顺序"""
        sorted_nodes = sorted(self.nodes.values(), key=lambda n: (n.chapter, n.order))
        for i, node in enumerate(sorted_nodes):
            node.order = i

    def _node_to_dict(self, node: OutlineNode) -> dict:
        return {
            "id": node.id,
            "chapter": node.chapter,
            "title": node.title,
            "summary": node.summary,
            "key_events": node.key_events,
            "characters_involved": node.characters_involved,
            "foreshadowing_planted": node.foreshadowing_planted,
            "foreshadowing_resolved": node.foreshadowing_resolved,
            "parent_id": node.parent_id,
            "children_ids": node.children_ids,
            "order": node.order,
            "status": node.status,
        }

    def _record_history(self, entry: ChangeHistory):
        self.history.append(entry)
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def get_history(self, limit: int = 50) -> list[dict]:
        """获取变更历史"""
        return [
            {
                "operation": h.operation.value,
                "node_id": h.node_id,
                "chapter": h.chapter,
                "timestamp": h.timestamp,
                "description": h.description,
                "impact": h.impact.value,
                "affected_chapters": h.affected_chapters,
            }
            for h in self.history[-limit:]
        ]

    def get_node(self, node_id: str) -> OutlineNode | None:
        return self.nodes.get(node_id)

    def list_nodes(self, status: str = "") -> list[OutlineNode]:
        """列出节点"""
        nodes = sorted(self.nodes.values(), key=lambda n: (n.chapter, n.order))
        if status:
            nodes = [n for n in nodes if n.status == status]
        return nodes

    def get_chapter_outline(self, chapter: int) -> list[OutlineNode]:
        """获取某章的大纲"""
        return [n for n in self.nodes.values() if n.chapter == chapter]

    def _save(self):
        if not self._data_dir:
            return
        data = {
            "nodes": {k: self._node_to_dict(v) for k, v in self.nodes.items()},
            "history": [
                {
                    "operation": h.operation.value,
                    "node_id": h.node_id,
                    "chapter": h.chapter,
                    "timestamp": h.timestamp,
                    "description": h.description,
                    "impact": h.impact.value,
                    "affected_chapters": h.affected_chapters,
                }
                for h in self.history[-100:]
            ],
        }
        (self._data_dir / "outline.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load(self):
        if not self._data_dir:
            return
        state_file = self._data_dir / "outline.json"
        if not state_file.exists():
            return
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            for node_id, node_data in data.get("nodes", {}).items():
                self.nodes[node_id] = OutlineNode(
                    id=node_data["id"],
                    chapter=node_data["chapter"],
                    title=node_data["title"],
                    summary=node_data.get("summary", ""),
                    key_events=node_data.get("key_events", []),
                    characters_involved=node_data.get("characters_involved", []),
                    foreshadowing_planted=node_data.get("foreshadowing_planted", []),
                    foreshadowing_resolved=node_data.get("foreshadowing_resolved", []),
                    parent_id=node_data.get("parent_id", ""),
                    children_ids=node_data.get("children_ids", []),
                    order=node_data.get("order", 0),
                    status=node_data.get("status", "planned"),
                )
            for h in data.get("history", []):
                self.history.append(
                    ChangeHistory(
                        operation=OperationType(h["operation"]),
                        node_id=h["node_id"],
                        chapter=h["chapter"],
                        timestamp=h["timestamp"],
                        description=h.get("description", ""),
                        impact=ImpactSeverity(h.get("impact", "none")),
                        affected_chapters=h.get("affected_chapters", []),
                    )
                )
        except Exception:
            logger.warning("大纲数据加载失败，使用空状态")


# ══════════════════════════════════════════════════════
# 工厂函数
# ══════════════════════════════════════════════════════

_outline_adjusters: dict[str, OutlineAdjuster] = {}


def get_outline_adjuster(book_id: str) -> OutlineAdjuster:
    """获取大纲调整器（单例）"""
    if book_id not in _outline_adjusters:
        _outline_adjusters[book_id] = OutlineAdjuster(book_id)
    return _outline_adjusters[book_id]
