"""
昆仑创作引擎 — 事件冷却矩阵

设计来源: novel-creator-skill 的事件矩阵与冷却机制

核心功能:
  1. 每种剧情事件类型有冷却章数（同一类型不能连续出现）
  2. 检测"爽点套路重复"——同类型爽点/冲突/情感模式过度密集
  3. 对将要生成的章节给出"冷却警告"——建议换什么类型

冷却规则:
  conflict_thrill (打脸/冲突爽点) — 冷却2章
  bond_deepening (感情推进)     — 冷却1章
  faction_building (势力/组织)   — 冷却2章
  world_painting (世界观展示)    — 冷却3章
  tension_escalation (危机升级)  — 冷却2章
  reveal_twist (真相揭露)        — 冷却3章
  battle_showdown (战斗高潮)     — 冷却2章
  character_growth (角色成长)    — 冷却1章
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass

from loguru import logger

from kunlun.common.json_store import save_json
from kunlun.config import settings

# ─── 事件类型定义 ─────────────────────────────────────

EVENT_TYPES = [
    "conflict_thrill",  # 打脸/冲突爽点
    "bond_deepening",  # 感情推进/暧昧/甜蜜
    "faction_building",  # 势力/组织/宗门建设
    "world_painting",  # 世界观展示/设定说明
    "tension_escalation",  # 危机升级/压力增加
    "reveal_twist",  # 真相揭露/反转
    "battle_showdown",  # 战斗高潮/对决
    "character_growth",  # 角色成长/突破/领悟
]

# 每种事件的冷却章数
EVENT_COOLDOWNS = {
    "conflict_thrill": 2,  # 不能连续两章都是打脸爽点
    "bond_deepening": 1,  # 感情推进冷却1章
    "faction_building": 2,  # 势力建设冷却2章
    "world_painting": 3,  # 世界观展示冷却3章（最长的冷却）
    "tension_escalation": 2,  # 危机升级冷却2章
    "reveal_twist": 3,  # 真相揭露冷却3章（防止频繁反转）
    "battle_showdown": 2,  # 战斗高潮冷却2章
    "character_growth": 1,  # 角色成长冷却1章
}

# 互为"健康替换"的事件类型对（如果A在冷却中，推荐B）
HEALTHY_ALTERNATIVES = {
    "conflict_thrill": ["tension_escalation", "character_growth", "reveal_twist"],
    "bond_deepening": ["conflict_thrill", "battle_showdown"],
    "faction_building": ["character_growth", "world_painting"],
    "world_painting": ["conflict_thrill", "bond_deepening"],
    "tension_escalation": ["character_growth", "reveal_twist"],
    "reveal_twist": ["tension_escalation", "conflict_thrill"],
    "battle_showdown": ["character_growth", "bond_deepening"],
    "character_growth": ["conflict_thrill", "tension_escalation"],
}


@dataclass
class EventRecord:
    """单次事件记录"""

    event_type: str
    chapter: int
    description: str = ""
    intensity: float = 1.0  # 0.0-2.0, 强度越高冷却越严格


@dataclass
class CooldownStatus:
    """当前冷却状态"""

    event_type: str
    remaining: int  # 还需冷却几章
    total_cooldown: int  # 总冷却章数
    last_chapter: int  # 上次出现章节
    is_cooling: bool  # 是否在冷却中
    alternatives: list[str]  # 推荐的替代事件类型


class EventCooldownMatrix:
    """
    事件冷却矩阵

    使用方式:
        matrix = EventCooldownMatrix(book_id)
        matrix.record_event("conflict_thrill", chapter=5)
        status = matrix.get_cooldown("conflict_thrill", current_chapter=6)
        if status.is_cooling:
            print(f"冷却中，推荐: {status.alternatives}")
        suggestions = matrix.suggest_next(current_chapter=6)
    """

    STORAGE_VERSION = 1

    def __init__(self, book_id: str):
        self.book_id = book_id
        self._history: list[EventRecord] = []
        self._data_dir = settings.DATA_DIR / "cooldown" / book_id
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    # ─── 记录事件 ────────────────────────────────────

    def record_event(
        self, event_type: str, chapter: int, description: str = "", intensity: float = 1.0
    ) -> None:
        """记录一次剧情事件"""
        if event_type not in EVENT_COOLDOWNS:
            logger.warning(f"[Cooldown] 未知事件类型: {event_type}")
            return

        self._history.append(
            EventRecord(
                event_type=event_type,
                chapter=chapter,
                description=description,
                intensity=min(2.0, max(0.0, intensity)),
            )
        )
        self._save()
        logger.debug(f"[Cooldown] 记录: ch{chapter} {event_type} (强度={intensity})")

    # ─── 冷却查询 ────────────────────────────────────

    def get_cooldown(self, event_type: str, current_chapter: int) -> CooldownStatus:
        """查询某事件类型的当前冷却状态"""
        base_cooldown = EVENT_COOLDOWNS.get(event_type, 1)

        # 找该类型上次出现章节
        last_chapter = 0
        last_intensity = 1.0
        for r in reversed(self._history):
            if r.event_type == event_type:
                last_chapter = r.chapter
                last_intensity = r.intensity
                break

        if last_chapter == 0:
            return CooldownStatus(
                event_type=event_type,
                remaining=0,
                total_cooldown=base_cooldown,
                last_chapter=0,
                is_cooling=False,
                alternatives=HEALTHY_ALTERNATIVES.get(event_type, []),
            )

        # 高强度事件冷却更严格（强度系数×总冷却）
        intensity_multiplier = 1.0 + max(0, last_intensity - 1.0) * 0.5
        effective_cooldown = int(base_cooldown * intensity_multiplier)
        gap = current_chapter - last_chapter
        remaining = max(0, effective_cooldown - gap)

        return CooldownStatus(
            event_type=event_type,
            remaining=remaining,
            total_cooldown=effective_cooldown,
            last_chapter=last_chapter,
            is_cooling=remaining > 0,
            alternatives=HEALTHY_ALTERNATIVES.get(event_type, []),
        )

    def get_all_cooldowns(self, current_chapter: int) -> list[CooldownStatus]:
        """查询所有事件类型的冷却状态"""
        return [self.get_cooldown(et, current_chapter) for et in EVENT_TYPES]

    # ─── 推荐引擎 ────────────────────────────────────

    def suggest_next(self, current_chapter: int) -> dict:
        """
        为下一章推荐事件类型。

        Returns:
            {
                "recommended": ["event_type", ...],  # 推荐的事件（按优先级）
                "cooling": [...],                      # 冷却中的事件
                "warnings": [...],                     # 冷却违规警告
            }
        """
        statuses = self.get_all_cooldowns(current_chapter)
        cooling = [s for s in statuses if s.is_cooling]
        available = [s for s in statuses if not s.is_cooling]

        # 按优先级推荐：使用最少 → 推荐
        usage_counts = self._get_usage_counts()
        available.sort(key=lambda s: usage_counts.get(s.event_type, 0))

        # 检查冷却违规（连续出现同类型）
        warnings = [
            f"⚠️ '{s.event_type}' 连续出现（上次ch{s.last_chapter}），"
            f"建议冷却{s.remaining}章，可选: {s.alternatives}"
            for s in cooling
            if s.last_chapter == current_chapter - 1
        ]

        return {
            "recommended": [s.event_type for s in available[:3]],
            "cooling": [
                {"type": s.event_type, "remaining": s.remaining, "alternatives": s.alternatives}
                for s in cooling
            ],
            "warnings": warnings,
        }

    def validate_blueprint(self, blueprint: dict, chapter: int) -> list[str]:
        """
        验证蓝图是否存在冷却违规。

        在Architect生成蓝图后调用，如果检测到冷却违规，
        返回警告列表供修订阶段使用。
        """
        warnings = []
        scenes = blueprint.get("scenes", []) or []

        # 检测场景中的事件类型
        scene_types = set()
        for scene in scenes:
            scene_type = scene.get("event_type", "") or self._infer_event_type(scene)
            if scene_type:
                scene_types.add(scene_type)

        for et in scene_types:
            status = self.get_cooldown(et, chapter)
            if status.is_cooling and status.last_chapter == chapter - 1:
                warnings.append(
                    f"[冷却违规] '{et}' 还在冷却中({status.remaining}章)，"
                    f"建议替换为: {status.alternatives}"
                )

        return warnings

    @staticmethod
    def _infer_event_type(scene: dict) -> str | None:
        """从场景描述推断事件类型"""
        desc = (
            scene.get("description", "")
            + " "
            + scene.get("title", "")
            + " "
            + scene.get("conflict", "")
        ).lower()

        # 关键词匹配
        patterns = {
            "conflict_thrill": ["打脸", "冲突", "碾压", "震惊", "秒杀"],
            "bond_deepening": ["暧昧", "心动", "表白", "牵手", "甜蜜", "感情"],
            "faction_building": ["势力", "组织", "宗门", "建设", "招募", "发展"],
            "world_painting": ["世界观", "设定", "说明", "背景", "历史", "地理"],
            "tension_escalation": ["危机", "压力", "紧张", "危险", "威胁", "紧迫"],
            "reveal_twist": ["真相", "揭露", "反转", "秘密", "原来", "竟然"],
            "battle_showdown": ["战斗", "对决", "决战", "厮杀", "对战", "比武"],
            "character_growth": ["突破", "成长", "领悟", "晋级", "觉醒", "蜕变"],
        }

        for event_type, keywords in patterns.items():
            for kw in keywords:
                if kw in desc:
                    return event_type

        return None

    def _get_usage_counts(self) -> dict[str, int]:
        """获取各事件类型的使用次数"""
        counts = defaultdict(int)
        for r in self._history:
            counts[r.event_type] += 1
        return dict(counts)

    # ─── 持久化 ──────────────────────────────────────

    def _save(self) -> None:
        data = {
            "version": self.STORAGE_VERSION,
            "book_id": self.book_id,
            "history": [
                {
                    "event_type": r.event_type,
                    "chapter": r.chapter,
                    "description": r.description,
                    "intensity": r.intensity,
                }
                for r in self._history[-200:]  # 最近200条
            ],
        }
        save_json(self._data_dir / "cooldown_state.json", data, pretty=True)

    def _load(self) -> None:
        path = self._data_dir / "cooldown_state.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for ed in data.get("history", []):
                self._history.append(
                    EventRecord(
                        event_type=ed["event_type"],
                        chapter=ed["chapter"],
                        description=ed.get("description", ""),
                        intensity=ed.get("intensity", 1.0),
                    )
                )
        except (OSError, json.JSONDecodeError, KeyError) as e:
            logger.warning(f"[Cooldown] 状态加载失败: {e}")


# ─── 工厂函数 ──────────────────────────────────────

_matrices: dict[str, EventCooldownMatrix] = {}


def get_cooldown_matrix(book_id: str) -> EventCooldownMatrix:
    if book_id not in _matrices:
        _matrices[book_id] = EventCooldownMatrix(book_id)
    return _matrices[book_id]
