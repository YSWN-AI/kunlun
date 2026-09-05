"""
分支剧情系统 — 数据类型定义
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class BranchPointType(StrEnum):
    """分支点触发类型"""

    CONFLICT_FORK = "conflict_fork"  # 冲突分叉 — 战斗/对抗的不同走向
    CHARACTER_DECISION = "character_decision"  # 角色抉择 — 关键选择点
    ROMANCE_FORK = "romance_fork"  # 感情线分支
    FACTION_CHOICE = "faction_choice"  # 阵营选择
    POWER_UP_PATH = "power_up_path"  # 升级路线分支
    REVELATION_BRANCH = "revelation_branch"  # 真相揭露的不同方向
    MORAL_DILEMMA = "moral_dilemma"  # 道德困境
    EVENT_OUTCOME = "event_outcome"  # 事件结果分支
    SUBPLOT_INSERT = "subplot_insert"  # 支线插入点

    @property
    def label(self) -> str:
        labels = {
            "conflict_fork": "冲突分叉",
            "character_decision": "角色抉择",
            "romance_fork": "感情线分支",
            "faction_choice": "阵营选择",
            "power_up_path": "升级路线",
            "revelation_branch": "真相揭露",
            "moral_dilemma": "道德困境",
            "event_outcome": "事件结果",
            "subplot_insert": "支线插入",
        }
        return labels.get(self.value, self.value)


class BranchConditionType(StrEnum):
    """分支条件类型"""

    CHARACTER_ATTRIBUTE = "character_attribute"  # 角色属性条件 (好感度/修为/等)
    PREVIOUS_CHOICE = "previous_choice"  # 前置选择
    ITEM_POSSESSION = "item_possession"  # 物品持有
    FLAG_STATE = "flag_state"  # 全局标志
    CHAPTER_RANGE = "chapter_range"  # 章节范围
    RELATIONSHIP = "relationship"  # 关系条件


@dataclass
class BranchCondition:
    """分支条件"""

    condition_type: BranchConditionType
    key: str  # 条件键 (如 "好感度_女主A")
    operator: str = ">="  # 比较运算符
    value: str | int | float = ""  # 阈值
    description: str = ""  # 人类可读描述

    def evaluate(self, state: dict) -> bool:
        """在给定状态下评估条件是否满足"""
        actual = state.get(self.key)
        if actual is None:
            return False
        try:
            actual_val = float(actual)
            threshold = float(self.value)
            if self.operator == ">=":
                return actual_val >= threshold
            if self.operator == ">":
                return actual_val > threshold
            if self.operator == "<=":
                return actual_val <= threshold
            if self.operator == "<":
                return actual_val < threshold
            if self.operator == "==":
                return actual_val == threshold
            if self.operator == "!=":
                return actual_val != threshold
            return False
        except (ValueError, TypeError):
            return str(actual) == str(self.value)


@dataclass
class BranchNode:
    """分支节点"""

    id: str  # 唯一标识
    name: str  # 分支名
    description: str  # 分支描述
    chapter: int  # 发生章节
    branch_type: BranchPointType  # 分支类型
    parent_id: str = ""  # 父节点ID
    children: list[str] = field(default_factory=list)  # 子节点ID列表
    conditions: list[BranchCondition] = field(default_factory=list)  # 进入条件
    conflict_ids: list[str] = field(default_factory=list)  # 关联冲突ID
    character_ids: list[str] = field(default_factory=list)  # 关联角色ID

    # 质量/流行度评分 (0-1)
    quality_score: float = 0.0
    popularity_score: float = 0.0
    reader_votes: int = 0

    # 叙事属性
    word_count_estimate: int = 0  # 预计字数
    pleasure_point_count: int = 0  # 爽点数
    tension_curve: list[float] = field(default_factory=list)  # 预期张力曲线

    is_canon: bool = False  # 是否为正史线
    is_completed: bool = False  # 是否已完成
    is_dead_end: bool = False  # 是否死路

    @property
    def composite_score(self) -> float:
        """综合评分 (质量*0.5 + 流行度*0.3 + 投票归一化*0.2)"""
        vote_score = min(1.0, self.reader_votes / 100.0) if self.reader_votes else 0.0
        return self.quality_score * 0.5 + self.popularity_score * 0.3 + vote_score * 0.2

    @property
    def is_leaf(self) -> bool:
        """是否为叶子节点"""
        return len(self.children) == 0


@dataclass
class BranchTree:
    """分支树"""

    book_id: str
    root_id: str  # 根节点ID
    nodes: dict[str, BranchNode] = field(default_factory=dict)
    current_path: list[str] = field(default_factory=list)  # 当前主线路径
    all_paths: list[list[str]] = field(default_factory=list)  # 所有完整路径
    endings: list[str] = field(default_factory=list)  # 结局节点ID列表

    def add_node(self, node: BranchNode) -> None:
        self.nodes[node.id] = node

    def get_path_to_root(self, node_id: str) -> list[str]:
        """获取从根到指定节点的路径"""
        path = []
        current = node_id
        while current:
            path.append(current)
            node = self.nodes.get(current)
            if not node or not node.parent_id:
                break
            current = node.parent_id
        return list(reversed(path))

    def get_children(self, node_id: str) -> list[BranchNode]:
        """获取节点的所有子节点"""
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[cid] for cid in node.children if cid in self.nodes]

    def get_siblings(self, node_id: str) -> list[BranchNode]:
        """获取节点的所有兄弟节点"""
        node = self.nodes.get(node_id)
        if not node or not node.parent_id:
            return []
        parent = self.nodes.get(node.parent_id)
        if not parent:
            return []
        return [self.nodes[cid] for cid in parent.children if cid in self.nodes and cid != node_id]

    def get_current_node(self) -> BranchNode | None:
        """获取当前路径的最后一个节点"""
        if not self.current_path:
            return None
        return self.nodes.get(self.current_path[-1])

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def path_count(self) -> int:
        return len(self.all_paths)

    @property
    def ending_count(self) -> int:
        return len(self.endings)
