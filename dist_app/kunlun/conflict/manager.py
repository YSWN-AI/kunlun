"""
冲突管理 — 冲突实例、状态管理、生命周期追踪
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from loguru import logger

from kunlun.config import settings

from .tension import ChapterTension, ConflictType, TensionAnalyzer, TensionLevel


class ConflictStatus(StrEnum):
    """冲突状态"""

    INTRODUCED = "introduced"  # 已引入
    ESCALATING = "escalating"  # 升级中
    CLIMAX = "climax"  # 高潮
    RESOLVING = "resolving"  # 解决中
    RESOLVED = "resolved"  # 已解决
    DORMANT = "dormant"  # 潜伏


@dataclass
class Conflict:
    """冲突实例"""

    id: str
    name: str
    conflict_type: ConflictType
    status: ConflictStatus = ConflictStatus.INTRODUCED
    participants: list[str] = field(default_factory=list)
    chapter_introduced: int = 0
    chapter_peaked: int = 0
    chapter_resolved: int = 0
    tension_timeline: list[dict] = field(default_factory=list)  # [{chapter, level}]

    @property
    def duration_chapters(self) -> int:
        """冲突持续章节数"""
        end = self.chapter_resolved or self.chapter_introduced
        return end - self.chapter_introduced

    @property
    def is_active(self) -> bool:
        return self.status not in (ConflictStatus.RESOLVED, ConflictStatus.DORMANT)


class ConflictManager:
    """冲突管理器 — 冲突生命周期 + 张力追踪"""

    def __init__(self, book_id: str = ""):
        self.book_id = book_id
        self.conflicts: dict[str, Conflict] = {}
        self.chapter_tensions: dict[int, ChapterTension] = {}
        self._data_dir: Path | None = None
        if book_id:
            self._data_dir = settings.DATA_DIR / "conflict" / book_id
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    def register_conflict(
        self,
        name: str,
        conflict_type: ConflictType,
        participants: list[str] | None = None,
        chapter: int = 0,
    ) -> Conflict:
        """注册新冲突"""
        conflict_id = f"conflict_{chapter}_{name[:4]}"
        conflict = Conflict(
            id=conflict_id,
            name=name,
            conflict_type=conflict_type,
            participants=participants or [],
            chapter_introduced=chapter,
            status=ConflictStatus.INTRODUCED,
        )
        self.conflicts[conflict_id] = conflict
        self._save()
        return conflict

    def update_status(self, conflict_id: str, new_status: ConflictStatus, chapter: int = 0):
        """更新冲突状态"""
        conflict = self.conflicts.get(conflict_id)
        if not conflict:
            return

        conflict.status = new_status
        if new_status == ConflictStatus.CLIMAX:
            conflict.chapter_peaked = chapter
        elif new_status == ConflictStatus.RESOLVED:
            conflict.chapter_resolved = chapter
        self._save()

    def analyze_chapter(self, text: str, chapter: int) -> tuple[ChapterTension, list[Conflict]]:
        """分析章节并更新冲突状态"""
        # 张力分析
        chapter_tension = TensionAnalyzer.analyze_chapter(text, chapter)

        # 更新活跃冲突
        active_conflicts = [c for c in self.conflicts.values() if c.is_active]
        chapter_tension.active_conflicts = [c.id for c in active_conflicts]

        # 记录冲突张力时间线
        for conflict in active_conflicts:
            conflict.tension_timeline.append(
                {
                    "chapter": chapter,
                    "level": chapter_tension.tension_level.value,
                    "score": chapter_tension.tension_score,
                }
            )

        # 自动检测冲突升级/解决
        for conflict in active_conflicts:
            self._auto_detect_status_change(conflict, chapter_tension, text, chapter)

        self.chapter_tensions[chapter] = chapter_tension
        self._save()
        return chapter_tension, active_conflicts

    def _auto_detect_status_change(
        self,
        conflict: Conflict,
        tension: ChapterTension,
        text: str,
        chapter: int,
    ):
        """自动检测冲突状态变化"""
        # 升级检测
        escalation_phrases = ["激化", "升级", "恶化", "爆发", "全面", "决一死战"]
        if conflict.status == ConflictStatus.INTRODUCED and any(
            p in text for p in escalation_phrases
        ):
            conflict.status = ConflictStatus.ESCALATING

        # 高潮检测
        climax_phrases = ["巅峰对决", "最终决战", "一决胜负", "拼命", "同归于尽"]
        if (
            conflict.status == ConflictStatus.ESCALATING
            and tension.tension_level >= TensionLevel.HIGH
            and any(p in text for p in climax_phrases)
        ):
            conflict.status = ConflictStatus.CLIMAX
            conflict.chapter_peaked = chapter

        # 解决检测
        resolution_phrases = ["终于", "结束", "落幕", "和解", "击败", "击杀", "斩杀", "消除"]
        if conflict.status == ConflictStatus.CLIMAX and any(p in text for p in resolution_phrases):
            conflict.status = ConflictStatus.RESOLVING

        if (
            conflict.status == ConflictStatus.RESOLVING
            and tension.tension_level <= TensionLevel.LOW
        ):
            conflict.status = ConflictStatus.RESOLVED
            conflict.chapter_resolved = chapter

    def get_tension_curve(self, last_n: int = 20) -> list[dict]:
        """获取全书张力曲线"""
        sorted_chapters = sorted(self.chapter_tensions.keys())[-last_n:]
        return [
            {
                "chapter": ch,
                "level": self.chapter_tensions[ch].tension_level.value,
                "score": self.chapter_tensions[ch].tension_score,
                "conflict_count": len(self.chapter_tensions[ch].active_conflicts),
            }
            for ch in sorted_chapters
        ]

    def get_active_conflicts(self) -> list[Conflict]:
        """获取活跃冲突"""
        return [c for c in self.conflicts.values() if c.is_active]

    def get_conflict_summary(self) -> dict:
        """获取冲突摘要"""
        active = self.get_active_conflicts()
        all_conflicts = list(self.conflicts.values())
        return {
            "total": len(all_conflicts),
            "active": len(active),
            "resolved": len([c for c in all_conflicts if c.status == ConflictStatus.RESOLVED]),
            "by_type": {
                ct.value: len([c for c in all_conflicts if c.conflict_type == ct])
                for ct in ConflictType
            },
            "avg_duration": (
                sum(c.duration_chapters for c in all_conflicts) / max(len(all_conflicts), 1)
            ),
        }

    def _save(self):
        if not self._data_dir:
            return
        data = {
            "conflicts": {
                cid: {
                    "id": c.id,
                    "name": c.name,
                    "conflict_type": c.conflict_type.value,
                    "status": c.status.value,
                    "participants": c.participants,
                    "chapter_introduced": c.chapter_introduced,
                    "chapter_peaked": c.chapter_peaked,
                    "chapter_resolved": c.chapter_resolved,
                    "tension_timeline": c.tension_timeline[-50:],
                }
                for cid, c in self.conflicts.items()
            },
            "chapter_tensions": {
                str(ch): {
                    "chapter": ct.chapter,
                    "tension_level": ct.tension_level.value,
                    "tension_score": ct.tension_score,
                    "active_conflicts": ct.active_conflicts,
                    "conflict_types": [ctp.value for ctp in ct.conflict_types_present],
                }
                for ch, ct in self.chapter_tensions.items()
            },
        }
        (self._data_dir / "conflicts.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2)
        )

    def _load(self):
        if not self._data_dir:
            return
        state_file = self._data_dir / "conflicts.json"
        if not state_file.exists():
            return
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            for cid, cd in data.get("conflicts", {}).items():
                self.conflicts[cid] = Conflict(
                    id=cd["id"],
                    name=cd["name"],
                    conflict_type=ConflictType(cd["conflict_type"]),
                    status=ConflictStatus(cd.get("status", "introduced")),
                    participants=cd.get("participants", []),
                    chapter_introduced=cd.get("chapter_introduced", 0),
                    chapter_peaked=cd.get("chapter_peaked", 0),
                    chapter_resolved=cd.get("chapter_resolved", 0),
                    tension_timeline=cd.get("tension_timeline", []),
                )
            for ch_str, ct_data in data.get("chapter_tensions", {}).items():
                ch = int(ch_str)
                self.chapter_tensions[ch] = ChapterTension(
                    chapter=ct_data["chapter"],
                    tension_level=TensionLevel(ct_data["tension_level"]),
                    tension_score=ct_data["tension_score"],
                    active_conflicts=ct_data.get("active_conflicts", []),
                    conflict_types_present=[
                        ConflictType(ct) for ct in ct_data.get("conflict_types", [])
                    ],
                )
        except Exception:
            logger.warning("冲突数据加载失败，使用空状态")


# ══════════════════════════════════════════════════════
# 工厂函数
# ══════════════════════════════════════════════════════

_conflict_managers: dict[str, ConflictManager] = {}


def get_conflict_manager(book_id: str) -> ConflictManager:
    """获取冲突管理器（单例）"""
    if book_id not in _conflict_managers:
        _conflict_managers[book_id] = ConflictManager(book_id)
    return _conflict_managers[book_id]
