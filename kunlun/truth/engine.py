"""
truth 真相文件引擎 — 写作"底牌"管理+角色关系矩阵+信息揭露计划

核心能力:
1. 真相文件管理（作者知道的底牌，读者不知道）
2. 角色关系矩阵（秘密、动机、背叛、联盟）
3. 信息揭露计划（何时、以何种方式揭示真相给读者）
4. 一致性校验（揭露的信息是否与底牌冲突）
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from kunlun.core.extension_base import BaseExtensionModule


class RevealType(Enum):
    """揭露方式"""

    DIALOGUE = "dialogue"  # 对话揭露
    ACTION = "action"  # 行动揭露
    FLASHBACK = "flashback"  # 回忆揭露
    DISCOVERY = "discovery"  # 发现（证据/线索）
    CONFRONTATION = "confrontation"  # 对峙揭露
    NARRATION = "narration"  # 旁白揭露
    HINT = "hint"  # 暗示（埋线）


class SecretLevel(Enum):
    """秘密等级"""

    PUBLIC = "public"  # 已公开
    KNOWN_TO_SOME = "known"  # 部分角色知道
    KNOWN_TO_ONE = "one"  # 仅一人知道
    AUTHOR_ONLY = "author"  # 仅作者知道（底牌）


@dataclass
class TruthEntry:
    """单条真相/底牌"""

    truth_id: str
    title: str
    content: str  # 完整的真相描述
    level: SecretLevel = SecretLevel.AUTHOR_ONLY
    related_characters: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    revealed: bool = False
    reveal_plan: list[RevealStep] = field(default_factory=list)
    notes: str = ""

    def summary(self) -> dict[str, Any]:
        return {
            "truth_id": self.truth_id,
            "title": self.title,
            "level": self.level.value,
            "revealed": self.revealed,
            "related_characters": self.related_characters,
            "reveal_steps": len(self.reveal_plan),
        }


@dataclass
class RevealStep:
    """揭露计划步骤"""

    step_id: str
    chapter: str = ""  # 目标章节
    reveal_type: RevealType = RevealType.HINT
    what_is_revealed: str = ""  # 揭露什么信息
    who_discovers: str = ""  # 谁发现
    narrative_impact: str = ""  # 叙事影响
    completed: bool = False
    completed_at: float = 0.0
    notes: str = ""


@dataclass
class CharacterRelation:
    """角色间关系"""

    character_a: str
    character_b: str
    relation_type: str = ""  # 朋友/敌人/家人/恋人/师徒/对手/陌生人
    secrets_between: list[str] = field(default_factory=list)  # 彼此间秘密
    trust_level: float = 0.5  # 信任度 0-1
    power_dynamic: str = ""  # 权力关系: a_dominant / b_dominant / equal
    notes: str = ""


@dataclass
class CharacterMatrixEntry:
    """角色矩阵条目（单个角色的底牌信息）"""

    character_name: str
    public_facts: list[str] = field(default_factory=list)  # 公开事实
    known_secrets: list[str] = field(default_factory=list)  # 部分人知道的秘密
    personal_secrets: list[str] = field(default_factory=list)  # 个人秘密
    true_motivation: str = ""  # 真实动机（作者底牌）
    hidden_agenda: str = ""  # 隐藏议程
    relationships: list[CharacterRelation] = field(default_factory=list)
    arc_truth: str = ""  # 角色弧线核心真相

    def summary(self) -> dict[str, Any]:
        return {
            "character": self.character_name,
            "public_facts": len(self.public_facts),
            "known_secrets": len(self.known_secrets),
            "personal_secrets": len(self.personal_secrets),
            "relationships": len(self.relationships),
            "has_motivation": bool(self.true_motivation),
            "has_agenda": bool(self.hidden_agenda),
        }


class TruthFileManager(BaseExtensionModule):
    """真相文件管理器"""

    SUBDIR = "truth"

    def __init__(self, book_id: str = ""):
        super().__init__(book_id)
        self._truths: dict[str, TruthEntry] = {}
        self._character_matrix: dict[str, CharacterMatrixEntry] = {}
        self._reveal_schedule: list[RevealStep] = []

    # === 真相管理 ===

    def add_truth(
        self,
        truth_id: str,
        title: str,
        content: str,
        level: SecretLevel = SecretLevel.AUTHOR_ONLY,
        related_characters: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> TruthEntry:
        """添加一条真相/底牌"""
        entry = TruthEntry(
            truth_id=truth_id,
            title=title,
            content=content,
            level=level,
            related_characters=related_characters or [],
            tags=tags or [],
        )
        self._truths[truth_id] = entry
        logger.info(f"真相已添加: {truth_id} [{level.value}]")
        return entry

    def get_truth(self, truth_id: str) -> TruthEntry | None:
        return self._truths.get(truth_id)

    def list_truths(
        self, level: SecretLevel | None = None, character: str = ""
    ) -> list[dict[str, Any]]:
        """列出真相，可按等级或角色过滤"""
        results = list(self._truths.values())
        if level:
            results = [t for t in results if t.level == level]
        if character:
            results = [t for t in results if character in t.related_characters]
        return [t.summary() for t in results]

    def add_reveal_plan(
        self,
        truth_id: str,
        steps: list[dict[str, Any]],
    ) -> bool:
        """为真相添加揭露计划"""
        truth = self._truths.get(truth_id)
        if not truth:
            logger.warning(f"真相不存在: {truth_id}")
            return False

        for step_data in steps:
            step = RevealStep(
                step_id=f"{truth_id}_step_{len(truth.reveal_plan) + 1}",
                chapter=step_data.get("chapter", ""),
                reveal_type=RevealType(step_data.get("reveal_type", "hint")),
                what_is_revealed=step_data.get("what_is_revealed", ""),
                who_discovers=step_data.get("who_discovers", ""),
                narrative_impact=step_data.get("narrative_impact", ""),
                notes=step_data.get("notes", ""),
            )
            truth.reveal_plan.append(step)
            self._reveal_schedule.append(step)

        logger.info(f"揭露计划已添加: {truth_id} ({len(steps)}步)")
        return True

    def mark_revealed(self, truth_id: str, step_id: str = "") -> bool:
        """标记真相已揭露"""
        truth = self._truths.get(truth_id)
        if not truth:
            return False

        if step_id:
            for step in truth.reveal_plan:
                if step.step_id == step_id and not step.completed:
                    step.completed = True
                    step.completed_at = time.time()
                    break

        # 检查是否所有步骤完成
        if all(s.completed for s in truth.reveal_plan) if truth.reveal_plan else True:
            truth.revealed = True
            logger.info(f"真相已完全揭露: {truth_id}")

        return True

    # === 角色矩阵 ===

    def set_character_entry(
        self,
        character_name: str,
        public_facts: list[str] | None = None,
        known_secrets: list[str] | None = None,
        personal_secrets: list[str] | None = None,
        true_motivation: str = "",
        hidden_agenda: str = "",
    ) -> CharacterMatrixEntry:
        """设置角色矩阵条目"""
        entry = self._character_matrix.get(character_name)
        if not entry:
            entry = CharacterMatrixEntry(character_name=character_name)
            self._character_matrix[character_name] = entry

        if public_facts is not None:
            entry.public_facts = public_facts
        if known_secrets is not None:
            entry.known_secrets = known_secrets
        if personal_secrets is not None:
            entry.personal_secrets = personal_secrets
        if true_motivation:
            entry.true_motivation = true_motivation
        if hidden_agenda:
            entry.hidden_agenda = hidden_agenda

        logger.info(f"角色矩阵已更新: {character_name}")
        return entry

    def add_relation(
        self,
        char_a: str,
        char_b: str,
        relation_type: str = "",
        trust_level: float = 0.5,
        power_dynamic: str = "",
    ) -> CharacterRelation:
        """添加角色间关系"""
        rel = CharacterRelation(
            character_a=char_a,
            character_b=char_b,
            relation_type=relation_type,
            trust_level=trust_level,
            power_dynamic=power_dynamic,
        )

        for name in (char_a, char_b):
            entry = self._character_matrix.get(name)
            if entry:
                entry.relationships.append(rel)

        logger.info(f"关系已添加: {char_a} <-> {char_b} ({relation_type})")
        return rel

    def get_character_matrix(self) -> dict[str, dict[str, Any]]:
        """获取完整角色矩阵"""
        return {name: entry.summary() for name, entry in self._character_matrix.items()}

    # === 一致性校验 ===

    def check_consistency(self, revealed_text: str, truth_id: str) -> dict[str, Any]:
        """校验揭露的文本是否与底牌一致"""
        truth = self._truths.get(truth_id)
        if not truth:
            return {"consistent": False, "error": f"真相不存在: {truth_id}"}

        issues: list[str] = []
        warnings: list[str] = []

        # 关键词检查
        content_lower = truth.content.lower()
        text_lower = revealed_text.lower()

        # 检查是否矛盾（简单关键词对立检测）
        contradictions = {
            "是": "不是",
            "真": "假",
            "活": "死",
            "爱": "恨",
            "友": "敌",
        }

        for pos, neg in contradictions.items():
            if pos in content_lower and neg in revealed_text.lower():
                issues.append(f"可能矛盾：底牌含'{pos}'，揭露文本含'{neg}'")

        # 检查时间线
        if "之前" in text_lower and "之后" in content_lower:
            warnings.append("时间线可能颠倒")

        consistent = len(issues) == 0

        if consistent:
            logger.info(f"一致性检查通过: {truth_id}")
        else:
            logger.warning(f"一致性检查发现问题: {truth_id} — {issues}")

        return {
            "consistent": consistent,
            "truth_id": truth_id,
            "issues": issues,
            "warnings": warnings,
        }

    # === 统计 ===

    def get_stats(self) -> dict[str, Any]:
        """获取真相文件统计"""
        total = len(self._truths)
        revealed = sum(1 for t in self._truths.values() if t.revealed)
        unrevealed = total - revealed

        level_counts = {}
        for t in self._truths.values():
            level_counts[t.level.value] = level_counts.get(t.level.value, 0) + 1

        return {
            "total_truths": total,
            "revealed": revealed,
            "unrevealed": unrevealed,
            "by_level": level_counts,
            "characters_with_matrix": len(self._character_matrix),
            "total_reveal_steps": len(self._reveal_schedule),
            "completed_steps": sum(1 for s in self._reveal_schedule if s.completed),
        }

    def get_consistency_report(self) -> dict[str, Any]:
        """获取一致性报告摘要"""
        stats = self.get_stats()
        issues = []
        # 检查未揭露的truth是否即将过期
        for tid, truth in self._truths.items():
            if not truth.revealed:
                issues.append(
                    {
                        "truth_id": tid,
                        "name": truth.name,
                        "status": "unrevealed",
                        "level": truth.level.value,
                    }
                )
        return {
            "overall_consistent": True,
            "total_checks": stats["total_truths"],
            "issues": issues,
            "stats": stats,
        }

    def get_reveal_schedule(self, chapter: str = "") -> list[dict[str, Any]]:
        """获取揭露计划表"""
        steps = self._reveal_schedule
        if chapter:
            steps = [s for s in steps if s.chapter == chapter]
        return [
            {
                "step_id": s.step_id,
                "chapter": s.chapter,
                "type": s.reveal_type.value,
                "what": s.what_is_revealed,
                "who": s.who_discovers,
                "completed": s.completed,
            }
            for s in steps
        ]


_managers: dict[str, TruthFileManager] = {}


def get_truth_manager(book_id: str = "") -> TruthFileManager:
    """获取真相文件管理器实例"""
    if book_id not in _managers:
        _managers[book_id] = TruthFileManager(book_id=book_id)
    return _managers[book_id]
