"""
昆仑创作引擎 — 角色状态机
管理角色的动态状态：心理、持有物品、情报、能力进度、人物弧光
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from loguru import logger


class ArcPhase(StrEnum):
    """人物弧光阶段"""

    SETUP = "setup"  # 初始状态：展现缺陷/渴望
    CATALYST = "catalyst"  # 催化事件：被迫改变
    STRUGGLE = "struggle"  # 挣扎期：新旧自我对抗
    TRANSFORMATION = "transform"  # 转变期：新自我成形
    TEST = "test"  # 考验期：新自我被极限测试
    RESOLUTION = "resolution"  # 完成：新自我确立


@dataclass
class CharacterState:
    """角色动态状态"""

    character_uid: str

    # 心理状态
    current_emotion: str = "neutral"  # 当前情绪
    psychological_state: str = ""  # 心理状态描述（如"极度焦虑""信心重建中"）
    mental_health: float = 1.0  # 0-1，1=完全健康

    # 表层动机 vs 深层需求（人物弧光核心）
    surface_motivation: str = ""  # 角色认为自己想要什么
    deep_need: str = ""  # 角色真正需要什么
    arc_phase: ArcPhase = ArcPhase.SETUP  # 弧光阶段
    arc_progress: float = 0.0  # 0.0-1.0

    # 持有物品（当前）
    held_items: list[str] = field(default_factory=list)  # item_uid 列表

    # 能力状态
    current_ability_level: str = ""  # 当前能力等级
    ability_growth_log: list[dict] = field(default_factory=list)
    # [{chapter: 3, event: "突破至筑基期", trigger: "服用筑基丹"}]

    # 关系状态
    relationships: dict[str, float] = field(default_factory=dict)
    # {other_char_uid: affinity_score (-1.0 到 1.0)}

    # 位置
    current_location_uid: str = ""

    # 最新更新时间
    last_updated_chapter: int = 0


class StateMachine:
    """
    角色状态机

    核心能力:
    - 角色动态状态追踪
    - 人物弧光阶段推进
    - 心理状态演变
    - 能力成长日志
    - 关系亲密度追踪
    """

    def __init__(self, book_id: str = ""):
        self._states: dict[str, CharacterState] = {}
        self._book_id = book_id
        self._data_dir: Path | None = None
        if book_id:
            from kunlun.config import settings

            self._data_dir = settings.DATA_DIR / "state" / book_id
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    def save(self):
        """持久化到磁盘"""
        if not self._data_dir:
            return
        data = {}
        for uid, st in self._states.items():
            data[uid] = {
                "character_uid": st.character_uid,
                "current_emotion": st.current_emotion,
                "psychological_state": st.psychological_state,
                "mental_health": st.mental_health,
                "surface_motivation": st.surface_motivation,
                "deep_need": st.deep_need,
                "arc_phase": st.arc_phase.value,
                "arc_progress": st.arc_progress,
                "held_items": list(st.held_items),
                "ability_growth_log": list(st.ability_growth_log),
                "relationships": dict(st.relationships),
                "current_location_uid": st.current_location_uid,
                "last_updated_chapter": st.last_updated_chapter,
            }
        path = self._data_dir / "state_machine.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load(self):
        """从磁盘恢复"""
        if not self._data_dir:
            return
        path = self._data_dir / "state_machine.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for uid, d in data.items():
                st = CharacterState(character_uid=uid)
                st.current_emotion = d.get("current_emotion", "neutral")
                st.psychological_state = d.get("psychological_state", "")
                st.mental_health = d.get("mental_health", 1.0)
                st.surface_motivation = d.get("surface_motivation", "")
                st.deep_need = d.get("deep_need", "")
                st.arc_phase = ArcPhase(d.get("arc_phase", "setup"))
                st.arc_progress = d.get("arc_progress", 0.0)
                st.held_items = list(d.get("held_items", []))
                st.ability_growth_log = list(d.get("ability_growth_log", []))
                st.relationships = dict(d.get("relationships", {}))
                st.current_location_uid = d.get("current_location_uid", "")
                st.last_updated_chapter = d.get("last_updated_chapter", 0)
                self._states[uid] = st
        except Exception as e:
            logger.warning(f"[StateMachine] 加载失败: {e}")

    def get_or_create(self, character_uid: str) -> CharacterState:
        if character_uid not in self._states:
            self._states[character_uid] = CharacterState(character_uid=character_uid)
        return self._states[character_uid]

    def update_emotion(
        self, character_uid: str, emotion: str, reason: str, chapter: int
    ) -> CharacterState:
        state = self.get_or_create(character_uid)
        old = state.current_emotion
        state.current_emotion = emotion
        state.last_updated_chapter = chapter
        logger.info(f"[StateMachine] {character_uid}: 情绪 {old} → {emotion} (原因: {reason})")
        return state

    def update_psychological_state(
        self, character_uid: str, description: str, chapter: int
    ) -> CharacterState:
        state = self.get_or_create(character_uid)
        state.psychological_state = description
        state.last_updated_chapter = chapter
        return state

    def advance_arc(
        self, character_uid: str, new_phase: ArcPhase, trigger_event: str, chapter: int
    ) -> CharacterState:
        """推进人物弧光阶段"""
        state = self.get_or_create(character_uid)
        phase_order = list(ArcPhase)
        old_idx = phase_order.index(state.arc_phase)
        new_idx = phase_order.index(new_phase)

        if new_idx < old_idx:
            logger.warning(
                f"[StateMachine] {character_uid}: 弧光回退 {state.arc_phase} → {new_phase}"
            )

        state.arc_phase = new_phase
        state.arc_progress = (new_idx + 1) / len(phase_order)
        state.last_updated_chapter = chapter
        logger.info(
            f"[StateMachine] {character_uid}: 弧光 {old_idx + 1}/6 → {new_idx + 1}/6 "
            f"({new_phase.value}), 触发: {trigger_event}"
        )
        return state

    def add_item(self, character_uid: str, item_uid: str, chapter: int) -> CharacterState:
        state = self.get_or_create(character_uid)
        if item_uid not in state.held_items:
            state.held_items.append(item_uid)
            state.last_updated_chapter = chapter
        return state

    def remove_item(self, character_uid: str, item_uid: str, chapter: int) -> CharacterState:
        state = self.get_or_create(character_uid)
        if item_uid in state.held_items:
            state.held_items.remove(item_uid)
            state.last_updated_chapter = chapter
        return state

    def log_ability_growth(
        self, character_uid: str, new_level: str, trigger: str, chapter: int
    ) -> CharacterState:
        state = self.get_or_create(character_uid)
        state.current_ability_level = new_level
        state.ability_growth_log.append(
            {
                "chapter": chapter,
                "event": f"突破至 {new_level}",
                "trigger": trigger,
            }
        )
        state.last_updated_chapter = chapter
        return state

    def update_relationship(
        self, character_uid: str, target_uid: str, delta: float, reason: str, chapter: int
    ) -> CharacterState:
        """更新与其他角色的亲密度（delta可正可负）"""
        state = self.get_or_create(character_uid)
        old = state.relationships.get(target_uid, 0.0)
        new = max(-1.0, min(1.0, old + delta))
        state.relationships[target_uid] = new
        state.last_updated_chapter = chapter
        logger.info(
            f"[StateMachine] {character_uid}→{target_uid}: 亲密度 {old:.2f} → {new:.2f} ({reason})"
        )
        return state

    def move_to(self, character_uid: str, location_uid: str, chapter: int) -> CharacterState:
        state = self.get_or_create(character_uid)
        state.current_location_uid = location_uid
        state.last_updated_chapter = chapter
        return state

    def get_summary(self, character_uid: str) -> dict:
        state = self._states.get(character_uid)
        if not state:
            return {"error": f"角色 {character_uid} 未注册"}
        return {
            "character_uid": state.character_uid,
            "emotion": state.current_emotion,
            "psychological_state": state.psychological_state,
            "surface_motivation": state.surface_motivation,
            "deep_need": state.deep_need,
            "arc_phase": state.arc_phase.value,
            "arc_progress": f"{state.arc_progress:.0%}",
            "held_items_count": len(state.held_items),
            "ability": state.current_ability_level,
            "location": state.current_location_uid,
            "relationships": {k: round(v, 2) for k, v in state.relationships.items()},
            "last_updated_chapter": state.last_updated_chapter,
        }


# 全局单例
state_machine = StateMachine()
