"""
交互式小说引擎 — InteractiveFictionEngine

核心能力:
  1. 读者选择系统 — 关键节点提供分支选择
  2. 状态追踪 — 角色属性/关系/物品/标志位全生命周期
  3. 多结局支持 — 条件驱动的多结局系统
  4. KG世界状态集成 — 与知识图谱联动同步世界状态
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from loguru import logger

from kunlun.config import settings


class ChoiceType(StrEnum):
    """选择类型"""

    ACTION = "action"  # 行动选择
    DIALOGUE = "dialogue"  # 对话选择
    MORAL = "moral"  # 道德选择
    ROMANCE = "romance"  # 感情选择
    STRATEGY = "strategy"  # 策略选择
    EXPLORATION = "exploration"  # 探索选择
    CUSTOM = "custom"  # 自定义


@dataclass
class ChoiceOutcome:
    """选择结果"""

    description: str  # 结果描述
    attribute_changes: dict[str, float] = field(default_factory=dict)  # 属性变化 {name: delta}
    relationship_changes: dict[str, float] = field(
        default_factory=dict
    )  # 关系变化 {char_id: delta}
    items_gained: list[str] = field(default_factory=list)  # 获得物品
    items_lost: list[str] = field(default_factory=list)  # 失去物品
    flags_set: dict[str, str] = field(default_factory=dict)  # 设置标志位 {flag: value}
    flags_cleared: list[str] = field(default_factory=list)  # 清除标志位
    next_chapter_id: str = ""  # 跳转章节ID
    is_ending: bool = False  # 是否为结局
    ending_id: str = ""  # 结局ID


@dataclass
class Choice:
    """选择项"""

    id: str
    text: str  # 显示文本
    choice_type: ChoiceType = ChoiceType.ACTION
    conditions: dict[str, str] = field(default_factory=dict)  # 前置条件 {key: value}
    outcomes: list[ChoiceOutcome] = field(default_factory=list)
    is_hidden: bool = False  # 是否隐藏(条件不满足时)
    hint: str = ""  # 提示文字
    popularity: float = 0.5  # 读者偏好度 0-1


@dataclass
class StoryEnding:
    """故事结局"""

    id: str
    name: str  # 结局名称
    description: str  # 结局描述
    ending_type: str = "normal"  # 结局类型: good/bad/true/hidden/normal
    conditions: dict[str, str] = field(default_factory=dict)  # 触发条件
    epilogue_text: str = ""  # 后记
    is_unlocked: bool = False
    unlock_count: int = 0  # 解锁次数


@dataclass
class GameState:
    """游戏状态 — 追踪所有交互式变量"""

    book_id: str
    current_chapter: int = 0
    current_node_id: str = ""

    # 角色状态
    character_attributes: dict[str, dict[str, float]] = field(default_factory=dict)
    # character_attributes[char_id] = { "好感度": 50, "信任": 30, ... }

    # 关系
    relationships: dict[str, dict[str, float]] = field(default_factory=dict)
    # relationships[char_a][char_b] = 好感值

    # 物品
    inventory: dict[str, int] = field(default_factory=dict)
    # inventory[item_id] = 数量

    # 标志位
    flags: dict[str, str] = field(default_factory=dict)

    # 历史
    choices_made: list[str] = field(default_factory=list)  # 已做选择ID
    visited_nodes: list[str] = field(default_factory=list)  # 已访问节点

    # 统计
    total_chapters_read: int = 0
    playthrough_count: int = 0

    # 结局追踪
    unlocked_endings: list[str] = field(default_factory=list)

    def apply_outcome(self, outcome: ChoiceOutcome) -> None:
        """应用选择结果到游戏状态"""
        # 属性变更
        for attr, delta in outcome.attribute_changes.items():
            parts = attr.split(".", 1)
            if len(parts) == 2:
                char_id, attr_name = parts
                if char_id not in self.character_attributes:
                    self.character_attributes[char_id] = {}
                current = self.character_attributes[char_id].get(attr_name, 0)
                self.character_attributes[char_id][attr_name] = max(0, min(100, current + delta))

        # 关系变更
        for char_id, delta in outcome.relationship_changes.items():
            self.relationships.setdefault("主角", {})
            current = self.relationships["主角"].get(char_id, 50)
            self.relationships["主角"][char_id] = max(0, min(100, current + delta))

        # 物品变更
        for item in outcome.items_gained:
            self.inventory[item] = self.inventory.get(item, 0) + 1
        for item in outcome.items_lost:
            if self.inventory.get(item, 0) > 0:
                self.inventory[item] -= 1
                if self.inventory[item] <= 0:
                    self.inventory.pop(item, None)

        # 标志位变更
        self.flags.update(outcome.flags_set)
        for flag in outcome.flags_cleared:
            self.flags.pop(flag, None)

    def check_conditions(self, conditions: dict[str, str]) -> bool:
        """检查条件是否满足"""
        for key, expected in conditions.items():
            # 检查标志位
            if key in self.flags:
                if self.flags[key] != expected:
                    return False
                continue

            # 检查物品
            if key.startswith("item:"):
                item_name = key[5:]
                if item_name not in self.inventory:
                    return False
                continue

            # 检查属性 (格式: char_id.attr_name)
            if "." in key:
                parts = key.split(".", 1)
                char_id, attr = parts
                actual = self.character_attributes.get(char_id, {}).get(attr, 0)
                try:
                    threshold = float(expected)
                    if actual < threshold:
                        return False
                except ValueError:
                    if str(actual) != expected:
                        return False
                continue

            # 检查关系 (格式: rel.char_id)
            if key.startswith("rel."):
                char_id = key[4:]
                actual = self.relationships.get("主角", {}).get(char_id, 0)
                try:
                    threshold = float(expected)
                    if actual < threshold:
                        return False
                except ValueError:
                    if str(actual) != expected:
                        return False
                continue

        return True

    def get_available_choices(self, choices: list[Choice]) -> list[Choice]:
        """筛选满足条件的可用选择"""
        available = []
        for choice in choices:
            if choice.is_hidden and not self.check_conditions(choice.conditions):
                continue
            if not choice.conditions or self.check_conditions(choice.conditions):
                available.append(choice)
        return available


class InteractiveFictionEngine:
    """交互式小说引擎"""

    def __init__(self, book_id: str = ""):
        self.book_id = book_id
        self.state: GameState | None = None
        self.choices: dict[str, list[Choice]] = {}  # node_id → [Choice]
        self.endings: dict[str, StoryEnding] = {}
        self._data_dir: Path | None = None

        if book_id:
            self._data_dir = settings.DATA_DIR / "interactive" / book_id
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    # ─── 状态管理 ────────────────────────────────

    def init_state(self) -> GameState:
        """初始化游戏状态"""
        self.state = GameState(book_id=self.book_id)
        self._save()
        return self.state

    def get_or_create_state(self) -> GameState:
        if self.state is None:
            return self.init_state()
        return self.state

    def reset_state(self) -> GameState:
        """重置状态（新周目）"""
        state = self.get_or_create_state()
        state.playthrough_count += 1
        state.current_chapter = 0
        state.current_node_id = ""
        state.character_attributes.clear()
        state.relationships.clear()
        state.inventory.clear()
        state.flags.clear()
        state.choices_made.clear()
        state.visited_nodes.clear()
        self._save()
        return state

    # ─── 选择系统 ────────────────────────────────

    def add_choice(
        self,
        node_id: str,
        text: str,
        choice_type: ChoiceType = ChoiceType.ACTION,
        conditions: dict[str, str] | None = None,
        outcomes: list[ChoiceOutcome] | None = None,
        hint: str = "",
    ) -> Choice:
        """添加选择项到指定节点"""
        self.get_or_create_state()
        choice_id = f"choice_{node_id}_{len(self.choices.get(node_id, [])):03d}"
        choice = Choice(
            id=choice_id,
            text=text,
            choice_type=choice_type,
            conditions=conditions or {},
            outcomes=outcomes or [],
            hint=hint,
        )
        self.choices.setdefault(node_id, []).append(choice)
        self._save()
        return choice

    def get_choices(self, node_id: str) -> list[Choice]:
        """获取指定节点的所有可用选择"""
        state = self.get_or_create_state()
        node_choices = self.choices.get(node_id, [])
        return state.get_available_choices(node_choices)

    def make_choice(
        self, choice_id: str, node_id: str, next_node_id: str = ""
    ) -> list[ChoiceOutcome]:
        """执行选择并返回结果"""
        state = self.get_or_create_state()
        node_choices = self.choices.get(node_id, [])

        choice = next((c for c in node_choices if c.id == choice_id), None)
        if not choice:
            raise ValueError(f"选择 {choice_id} 在节点 {node_id} 中不存在")

        if choice.conditions and not state.check_conditions(choice.conditions):
            raise ValueError(f"选择 {choice_id} 的条件不满足")

        state.choices_made.append(choice_id)
        state.visited_nodes.append(node_id)

        results = []
        for outcome in choice.outcomes:
            state.apply_outcome(outcome)
            results.append(outcome)

            # 检查是否为结局
            if outcome.is_ending and outcome.ending_id:
                ending = self.endings.get(outcome.ending_id)
                if ending:
                    ending.is_unlocked = True
                    ending.unlock_count += 1
                    if outcome.ending_id not in state.unlocked_endings:
                        state.unlocked_endings.append(outcome.ending_id)

        if next_node_id:
            state.current_node_id = next_node_id
        state.current_chapter += 1
        state.total_chapters_read += 1

        self._save()
        return results

    # ─── 结局系统 ────────────────────────────────

    def add_ending(
        self,
        name: str,
        description: str,
        conditions: dict[str, str] | None = None,
        ending_type: str = "normal",
        epilogue: str = "",
    ) -> StoryEnding:
        """添加结局"""
        self.get_or_create_state()
        ending_id = f"ending_{len(self.endings):03d}"
        ending = StoryEnding(
            id=ending_id,
            name=name,
            description=description,
            ending_type=ending_type,
            conditions=conditions or {},
            epilogue_text=epilogue,
        )
        self.endings[ending_id] = ending
        self._save()
        return ending

    def check_endings(self) -> list[StoryEnding]:
        """检查当前状态触发了哪些结局条件"""
        state = self.get_or_create_state()
        return [
            ending for ending in self.endings.values() if state.check_conditions(ending.conditions)
        ]

    def get_all_endings(self) -> list[StoryEnding]:
        """获取所有结局"""
        return list(self.endings.values())

    def get_unlocked_endings(self) -> list[StoryEnding]:
        """获取已解锁的结局"""
        return [e for e in self.endings.values() if e.is_unlocked]

    # ─── KG 世界状态集成 ─────────────────────────

    def sync_to_kg(self) -> dict:
        """将交互式状态同步到知识图谱"""
        state = self.get_or_create_state()
        sync_data = {
            "character_attributes": state.character_attributes,
            "relationships": state.relationships,
            "inventory": dict(state.inventory),
            "flags": dict(state.flags),
            "current_chapter": state.current_chapter,
        }

        if self._data_dir:
            (self._data_dir / "kg_sync.json").write_text(
                json.dumps(sync_data, ensure_ascii=False, indent=2)
            )

        try:
            from kunlun.kg.client import kg_client

            # 更新角色属性到KG
            for char_id, attrs in state.character_attributes.items():
                for attr_name, attr_val in attrs.items():
                    kg_client.set_entity_property(
                        "Character", char_id, f"attr_{attr_name}", str(attr_val)
                    )

            # 更新关系到KG
            for char_a, rels in state.relationships.items():
                for char_b, val in rels.items():
                    kg_client.set_entity_property("Character", char_a, f"rel_{char_b}", str(val))
        except Exception as e:
            logger.debug(f"[Interactive] KG同步失败: {e}")

        return sync_data

    def load_from_kg(self) -> GameState:
        """从知识图谱加载世界状态"""
        state = self.get_or_create_state()

        try:
            from kunlun.kg.client import kg_client

            characters = kg_client.get_all("Character")
            for char in characters:
                char_id = char.get("id", "")
                attrs = {k: float(v) for k, v in char.items() if k.startswith("attr_")}
                if attrs:
                    state.character_attributes[char_id] = attrs

                rels = {k: float(v) for k, v in char.items() if k.startswith("rel_")}
                if rels:
                    for rel_target, val in rels.items():
                        state.relationships.setdefault(char_id, {})[rel_target] = val
        except Exception as e:
            logger.debug(f"[Interactive] KG加载失败: {e}")

        self._save()
        return state

    # ─── 统计与导出 ──────────────────────────────

    def get_state_summary(self) -> dict:
        """获取当前游戏状态摘要"""
        state = self.get_or_create_state()
        return {
            "book_id": state.book_id,
            "current_chapter": state.current_chapter,
            "choices_made": len(state.choices_made),
            "endings_unlocked": len(state.unlocked_endings),
            "total_endings": len(self.endings),
            "inventory_size": len(state.inventory),
            "flags_count": len(state.flags),
            "playthroughs": state.playthrough_count,
            "relationships": state.relationships.get("主角", {}),
            "key_flags": dict(state.flags),
        }

    def export_choice_tree(self) -> dict:
        """导出选择树供前端可视化"""
        nodes = []
        edges = []

        for node_id, choices in self.choices.items():
            nodes.append(
                {
                    "id": node_id,
                    "type": "choice_node",
                    "choice_count": len(choices),
                    "choices": [
                        {
                            "id": c.id,
                            "text": c.text,
                            "type": c.choice_type.value,
                            "popularity": c.popularity,
                        }
                        for c in choices
                    ],
                }
            )
            for choice in choices:
                edges.extend(
                    {
                        "source": node_id,
                        "target": outcome.next_chapter_id,
                        "label": choice.text[:20],
                        "choice_id": choice.id,
                    }
                    for outcome in choice.outcomes
                    if outcome.next_chapter_id
                )

        return {
            "book_id": self.book_id,
            "nodes": nodes,
            "edges": edges,
            "endings": [
                {"id": e.id, "name": e.name, "type": e.ending_type, "unlocked": e.is_unlocked}
                for e in self.endings.values()
            ],
            "current_state": self.get_state_summary() if self.state else {},
        }

    # ─── 持久化 ──────────────────────────────────

    def _save(self):
        if not self._data_dir:
            return

        state_data = None
        if self.state:
            state_data = {
                "book_id": self.state.book_id,
                "current_chapter": self.state.current_chapter,
                "current_node_id": self.state.current_node_id,
                "character_attributes": self.state.character_attributes,
                "relationships": self.state.relationships,
                "inventory": self.state.inventory,
                "flags": self.state.flags,
                "choices_made": self.state.choices_made,
                "visited_nodes": self.state.visited_nodes,
                "total_chapters_read": self.state.total_chapters_read,
                "playthrough_count": self.state.playthrough_count,
                "unlocked_endings": self.state.unlocked_endings,
            }

        choices_data = {}
        for node_id, node_choices in self.choices.items():
            choices_data[node_id] = [
                {
                    "id": c.id,
                    "text": c.text,
                    "choice_type": c.choice_type.value,
                    "conditions": c.conditions,
                    "outcomes": [
                        {
                            "description": o.description,
                            "attribute_changes": o.attribute_changes,
                            "relationship_changes": o.relationship_changes,
                            "items_gained": o.items_gained,
                            "items_lost": o.items_lost,
                            "flags_set": o.flags_set,
                            "flags_cleared": o.flags_cleared,
                            "next_chapter_id": o.next_chapter_id,
                            "is_ending": o.is_ending,
                            "ending_id": o.ending_id,
                        }
                        for o in c.outcomes
                    ],
                    "is_hidden": c.is_hidden,
                    "hint": c.hint,
                    "popularity": c.popularity,
                }
                for c in node_choices
            ]

        endings_data = {}
        for eid, ending in self.endings.items():
            endings_data[eid] = {
                "id": ending.id,
                "name": ending.name,
                "description": ending.description,
                "ending_type": ending.ending_type,
                "conditions": ending.conditions,
                "epilogue_text": ending.epilogue_text,
                "is_unlocked": ending.is_unlocked,
                "unlock_count": ending.unlock_count,
            }

        data = {
            "state": state_data,
            "choices": choices_data,
            "endings": endings_data,
        }
        (self._data_dir / "interactive_state.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2)
        )

    def _load(self):
        if not self._data_dir:
            return
        state_file = self._data_dir / "interactive_state.json"
        if not state_file.exists():
            return
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))

            if data.get("state"):
                s = data["state"]
                self.state = GameState(
                    book_id=s.get("book_id", self.book_id),
                    current_chapter=s.get("current_chapter", 0),
                    current_node_id=s.get("current_node_id", ""),
                    character_attributes=s.get("character_attributes", {}),
                    relationships=s.get("relationships", {}),
                    inventory=s.get("inventory", {}),
                    flags=s.get("flags", {}),
                    choices_made=s.get("choices_made", []),
                    visited_nodes=s.get("visited_nodes", []),
                    total_chapters_read=s.get("total_chapters_read", 0),
                    playthrough_count=s.get("playthrough_count", 0),
                    unlocked_endings=s.get("unlocked_endings", []),
                )

            for node_id, node_choices in data.get("choices", {}).items():
                self.choices[node_id] = [
                    Choice(
                        id=c["id"],
                        text=c["text"],
                        choice_type=ChoiceType(c["choice_type"]),
                        conditions=c.get("conditions", {}),
                        outcomes=[
                            ChoiceOutcome(
                                description=o["description"],
                                attribute_changes=o.get("attribute_changes", {}),
                                relationship_changes=o.get("relationship_changes", {}),
                                items_gained=o.get("items_gained", []),
                                items_lost=o.get("items_lost", []),
                                flags_set=o.get("flags_set", {}),
                                flags_cleared=o.get("flags_cleared", []),
                                next_chapter_id=o.get("next_chapter_id", ""),
                                is_ending=o.get("is_ending", False),
                                ending_id=o.get("ending_id", ""),
                            )
                            for o in c.get("outcomes", [])
                        ],
                        is_hidden=c.get("is_hidden", False),
                        hint=c.get("hint", ""),
                        popularity=c.get("popularity", 0.5),
                    )
                    for c in node_choices
                ]

            for eid, ed in data.get("endings", {}).items():
                self.endings[eid] = StoryEnding(
                    id=ed["id"],
                    name=ed["name"],
                    description=ed["description"],
                    ending_type=ed.get("ending_type", "normal"),
                    conditions=ed.get("conditions", {}),
                    epilogue_text=ed.get("epilogue_text", ""),
                    is_unlocked=ed.get("is_unlocked", False),
                    unlock_count=ed.get("unlock_count", 0),
                )
        except Exception:
            logger.warning("交互式小说数据加载失败，使用空状态")


# ─── 工厂函数 ──────────────────────────────────

_interactive_engines: dict[str, InteractiveFictionEngine] = {}


def get_interactive_engine(book_id: str) -> InteractiveFictionEngine:
    if book_id not in _interactive_engines:
        _interactive_engines[book_id] = InteractiveFictionEngine(book_id)
    return _interactive_engines[book_id]
