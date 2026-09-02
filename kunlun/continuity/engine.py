"""
昆仑创作引擎 — 确定性连续性引擎 (Deterministic Continuity Engine)

灵感来源: Novel-OS 确定性连续性引擎 + InkOS 状态不可变快照
对标: 网文连载中角色/事件/设定/时间线的连续性保障
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from loguru import logger

from kunlun.config import settings

# ─── 数据类型 ────────────────────────────────────────


class ContinuitySeverity(Enum):
    """连续性违规严重度"""

    BLOCKER = "blocker"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ContinuityViolation:
    """连续性违规记录"""

    check_name: str
    severity: ContinuitySeverity
    entity_type: str
    entity_id: str
    description: str
    previous_value: Any = None
    current_value: Any = None
    suggestion: str = ""


@dataclass
class ContinuitySnapshot:
    """章节连续性快照"""

    chapter_number: int
    characters: dict[str, dict] = field(default_factory=dict)
    timeline: dict[str, Any] = field(default_factory=dict)
    items: dict[str, dict] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    plot_threads: dict[str, dict] = field(default_factory=dict)
    entity_names: dict[str, str] = field(default_factory=dict)
    values: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContinuityReport:
    """连续性检查报告"""

    chapter_number: int
    passed: bool
    overall_score: float
    violations: list[ContinuityViolation] = field(default_factory=list)
    check_results: dict[str, dict] = field(default_factory=dict)
    stats: dict[str, int] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)


# ─── 确定性检查器 ────────────────────────────────────


class ContinuityChecker:
    @staticmethod
    def check_character_continuity(
        previous: dict[str, dict],
        current: dict[str, dict],
    ) -> list[ContinuityViolation]:
        violations: list[ContinuityViolation] = []

        for char_id, prev_state in previous.items():
            if char_id not in current:
                continue

            curr_state = current[char_id]

            prev_emotion = prev_state.get("emotion", "")
            curr_emotion = curr_state.get("emotion", "")
            if prev_emotion and curr_emotion:
                emotion_distance = _emotion_distance(prev_emotion, curr_emotion)
                if emotion_distance > 2:
                    violations.append(
                        ContinuityViolation(
                            check_name="角色状态连续性",
                            severity=ContinuitySeverity.WARNING,
                            entity_type="character",
                            entity_id=char_id,
                            description=(
                            f"角色情绪剧烈变化: {prev_emotion} → {curr_emotion} "
                            f"(跨{emotion_distance}级)"
                        ),
                            previous_value=prev_emotion,
                            current_value=curr_emotion,
                            suggestion="建议添加情绪过渡描写",
                        )
                    )

            prev_loc = prev_state.get("location", "")
            curr_loc = curr_state.get("location", "")
            if (
                prev_loc
                and curr_loc
                and prev_loc != curr_loc
                and not curr_state.get("travel_described", False)
            ):
                violations.append(
                    ContinuityViolation(
                        check_name="角色状态连续性",
                        severity=ContinuitySeverity.BLOCKER,
                        entity_type="character",
                        entity_id=char_id,
                        description=f"角色位置跳跃: {prev_loc} → {curr_loc} (无移动描写)",
                        previous_value=prev_loc,
                        current_value=curr_loc,
                        suggestion="建议添加移动/转场描写，或标记 travel_described=True",
                    )
                )

            prev_health = prev_state.get("health", "")
            curr_health = curr_state.get("health", "")
            if (
                prev_health in ("重伤", "濒死")
                and curr_health in ("健康", "轻伤")
                and not curr_state.get("recovery_described", False)
            ):
                violations.append(
                    ContinuityViolation(
                        check_name="角色状态连续性",
                        severity=ContinuitySeverity.WARNING,
                        entity_type="character",
                        entity_id=char_id,
                        description=f"角色伤势不合理恢复: {prev_health} → {curr_health}",
                        previous_value=prev_health,
                        current_value=curr_health,
                        suggestion="建议添加治疗/恢复描写，或标记 recovery_described=True",
                    )
                )

            prev_rel = prev_state.get("relationship_to_protagonist", "")
            curr_rel = curr_state.get("relationship_to_protagonist", "")
            if (
                prev_rel == "敌对"
                and curr_rel == "盟友"
                and not curr_state.get("reconciliation_described", False)
            ):
                violations.append(
                    ContinuityViolation(
                        check_name="角色状态连续性",
                        severity=ContinuitySeverity.BLOCKER,
                        entity_type="character",
                        entity_id=char_id,
                        description=f"角色关系矛盾: {prev_rel} → {curr_rel} (无和解过程)",
                        previous_value=prev_rel,
                        current_value=curr_rel,
                        suggestion="建议添加和解/结盟描写，或标记 reconciliation_described=True",
                    )
                )

        return violations

    @staticmethod
    def check_timeline_continuity(
        previous: dict[str, Any],
        current: dict[str, Any],
    ) -> list[ContinuityViolation]:
        violations: list[ContinuityViolation] = []

        prev_day = previous.get("story_day", 0)
        curr_day = current.get("story_day", 0)

        if curr_day < prev_day:
            violations.append(
                ContinuityViolation(
                    check_name="时间线连续性",
                    severity=ContinuitySeverity.BLOCKER,
                    entity_type="timeline",
                    entity_id="main",
                    description=f"时间倒流: 第{prev_day}天 → 第{curr_day}天",
                    previous_value=prev_day,
                    current_value=curr_day,
                    suggestion="检查时间线标记是否正确",
                )
            )

        if curr_day - prev_day > 7:
            violations.append(
                ContinuityViolation(
                    check_name="时间线连续性",
                    severity=ContinuitySeverity.WARNING,
                    entity_type="timeline",
                    entity_id="main",
                    description=(
                            f"时间跳跃过大: {prev_day}天 → {curr_day}天 "
                            f"(跨{curr_day - prev_day}天)"
                        ),
                    previous_value=prev_day,
                    current_value=curr_day,
                    suggestion="建议添加时间跳跃说明 (如'三个月后')",
                )
            )

        if curr_day == prev_day:
            prev_hour = _time_to_hours(previous.get("time_of_day", "12:00"))
            curr_hour = _time_to_hours(current.get("time_of_day", "12:00"))
            if curr_hour < prev_hour:
                violations.append(
                    ContinuityViolation(
                        check_name="时间线连续性",
                        severity=ContinuitySeverity.WARNING,
                        entity_type="timeline",
                        entity_id="main",
                        description=(
                            f"同一天时间倒流: {previous.get('time_of_day')} "
                            f"→ {current.get('time_of_day')}"
                        ),
                        previous_value=previous.get("time_of_day"),
                        current_value=current.get("time_of_day"),
                        suggestion="检查时间标记",
                    )
                )

        return violations

    @staticmethod
    def check_item_continuity(
        previous: dict[str, dict],
        current: dict[str, dict],
    ) -> list[ContinuityViolation]:
        violations: list[ContinuityViolation] = []

        for item_id, prev_item in previous.items():
            if item_id not in current:
                if prev_item.get("status") != "consumed":
                    violations.append(
                        ContinuityViolation(
                            check_name="物品连续性",
                            severity=ContinuitySeverity.INFO,
                            entity_type="item",
                            entity_id=item_id,
                            description=f"物品 {item_id} 从状态中消失",
                            previous_value=prev_item,
                            suggestion="确认物品是否已消耗/丢失/转移",
                        )
                    )
                continue

            curr_item = current[item_id]

            if prev_item.get("status") == "consumed" and curr_item.get("status") != "consumed":
                violations.append(
                    ContinuityViolation(
                        check_name="物品连续性",
                        severity=ContinuitySeverity.BLOCKER,
                        entity_type="item",
                        entity_id=item_id,
                        description=f"已消耗物品 {item_id} 再次出现",
                        previous_value=prev_item.get("status"),
                        current_value=curr_item.get("status"),
                        suggestion="确认物品来源 (重新获得/恢复/错误)",
                    )
                )

            prev_holder = prev_item.get("holder", "")
            curr_holder = curr_item.get("holder", "")
            if (
                prev_holder
                and curr_holder
                and prev_holder != curr_holder
                and not curr_item.get("transfer_described", False)
            ):
                violations.append(
                    ContinuityViolation(
                        check_name="物品连续性",
                        severity=ContinuitySeverity.WARNING,
                        entity_type="item",
                        entity_id=item_id,
                        description=f"物品 {item_id} 持有者变更: {prev_holder} → {curr_holder}",
                        previous_value=prev_holder,
                        current_value=curr_holder,
                        suggestion="添加物品转移描写，或标记 transfer_described=True",
                    )
                )

            prev_qty = prev_item.get("quantity", 1)
            curr_qty = curr_item.get("quantity", 1)
            if curr_qty > prev_qty and not curr_item.get("acquisition_described", False):
                violations.append(
                    ContinuityViolation(
                        check_name="物品连续性",
                        severity=ContinuitySeverity.WARNING,
                        entity_type="item",
                        entity_id=item_id,
                        description=f"物品 {item_id} 数量异常增加: {prev_qty} → {curr_qty}",
                        previous_value=prev_qty,
                        current_value=curr_qty,
                        suggestion="添加获得描写，或标记 acquisition_described=True",
                    )
                )

        return violations

    @staticmethod
    def check_setting_continuity(
        previous: dict[str, Any],
        current: dict[str, Any],
    ) -> list[ContinuityViolation]:
        violations: list[ContinuityViolation] = []

        prev_max_level = previous.get("max_known_level", "")
        curr_max_level = current.get("max_known_level", "")
        if prev_max_level and curr_max_level:
            prev_rank = _level_to_rank(prev_max_level)
            curr_rank = _level_to_rank(curr_max_level)
            if curr_rank < prev_rank:
                violations.append(
                    ContinuityViolation(
                        check_name="设定连续性",
                        severity=ContinuitySeverity.WARNING,
                        entity_type="setting",
                        entity_id="power_level",
                        description=f"已知最高境界下降: {prev_max_level} → {curr_max_level}",
                        previous_value=prev_max_level,
                        current_value=curr_max_level,
                        suggestion="检查是否为不同体系，或修正境界描述",
                    )
                )

        hard_rules = previous.get("hard_rules", [])
        for rule in hard_rules:
            rule_id = rule.get("id", "")
            if rule_id in current.get("violated_rules", []):
                violations.append(
                    ContinuityViolation(
                        check_name="设定连续性",
                        severity=ContinuitySeverity.BLOCKER,
                        entity_type="setting",
                        entity_id=rule_id,
                        description=f"违反了世界观硬规则: {rule.get('description', rule_id)}",
                        suggestion=rule.get("fix_hint", "修正内容以符合设定规则"),
                    )
                )

        return violations

    @staticmethod
    def check_plot_continuity(
        previous: dict[str, dict],
        current: dict[str, dict],
    ) -> list[ContinuityViolation]:
        violations: list[ContinuityViolation] = []

        for thread_id, prev_thread in previous.items():
            if thread_id not in current:
                if prev_thread.get("status") == "in_progress":
                    violations.append(
                        ContinuityViolation(
                            check_name="情节连续性",
                            severity=ContinuitySeverity.WARNING,
                            entity_type="plot",
                            entity_id=thread_id,
                            description=f"进行中的情节线 {thread_id} 在本章无推进",
                            previous_value=prev_thread.get("status"),
                            suggestion="确认该情节线是否在本章自然暂停",
                        )
                    )
                continue

            curr_thread = current[thread_id]

            prev_status = prev_thread.get("status", "")
            curr_status = curr_thread.get("status", "")
            if prev_status == "resolved" and curr_status == "in_progress":
                violations.append(
                    ContinuityViolation(
                        check_name="情节连续性",
                        severity=ContinuitySeverity.BLOCKER,
                        entity_type="plot",
                        entity_id=thread_id,
                        description=f"已解决的情节线 {thread_id} 重新激活",
                        previous_value=prev_status,
                        current_value=curr_status,
                        suggestion="确认是否为新事件，或修改状态标记",
                    )
                )

        return violations

    @staticmethod
    def check_naming_continuity(
        previous: dict[str, str],
        current: dict[str, str],
        text: str = "",
    ) -> list[ContinuityViolation]:
        violations: list[ContinuityViolation] = []

        for entity_id, prev_name in previous.items():
            if entity_id not in current:
                continue
            curr_name = current[entity_id]
            if prev_name != curr_name:
                rename_patterns = [
                    rf"({curr_name})",
                    rf"{re.escape(prev_name)}.{0, 10}"
                    rf"(?:改名|更名|改称).{0, 10}{re.escape(curr_name)}",
                ]
                has_rename_explanation = (
                    any(re.search(p, text) for p in rename_patterns) if text else False
                )

                if not has_rename_explanation:
                    violations.append(
                        ContinuityViolation(
                            check_name="称呼连续性",
                            severity=ContinuitySeverity.WARNING,
                            entity_type="naming",
                            entity_id=entity_id,
                            description=f"实体称呼变更: {prev_name} → {curr_name}",
                            previous_value=prev_name,
                            current_value=curr_name,
                            suggestion="添加改名说明，或修正称呼",
                        )
                    )

        return violations

    @staticmethod
    def check_value_continuity(
        previous: dict[str, Any],
        current: dict[str, Any],
    ) -> list[ContinuityViolation]:
        violations: list[ContinuityViolation] = []

        for value_key, prev_val in previous.items():
            if value_key not in current:
                continue
            curr_val = current[value_key]

            if isinstance(prev_val, (int, float)) and isinstance(curr_val, (int, float)):
                no_regression_keys = ("level", "rank", "age", "realm", "stage", "tier")
                if any(k in value_key.lower() for k in no_regression_keys) and curr_val < prev_val:
                    violations.append(
                        ContinuityViolation(
                            check_name="数值连续性",
                            severity=ContinuitySeverity.BLOCKER,
                            entity_type="value",
                            entity_id=value_key,
                            description=f"数值倒退: {value_key}: {prev_val} → {curr_val}",
                            previous_value=prev_val,
                            current_value=curr_val,
                            suggestion=f"确认 {value_key} 是否合理下降",
                        )
                    )

                if prev_val > 0 and curr_val > prev_val * 3:
                    violations.append(
                        ContinuityViolation(
                            check_name="数值连续性",
                            severity=ContinuitySeverity.WARNING,
                            entity_type="value",
                            entity_id=value_key,
                            description=(
                            f"数值暴增: {value_key}: {prev_val} → {curr_val} "
                            f"(x{curr_val / max(prev_val, 1):.1f})"
                        ),
                            previous_value=prev_val,
                            current_value=curr_val,
                            suggestion="建议添加合理的升级描写",
                        )
                    )

        return violations


# ─── 快照管理器 ──────────────────────────────────────


class SnapshotManager:
    """状态快照管理器 — 不可变快照存储"""

    def __init__(self, book_id: str = ""):
        self.book_id = book_id
        self._snapshots: dict[int, ContinuitySnapshot] = {}
        self._snapshot_dir: Path | None = None

        if book_id:
            self._snapshot_dir = settings.DATA_DIR / "continuity" / book_id / "snapshots"
            self._snapshot_dir.mkdir(parents=True, exist_ok=True)
            self._load_all()

    def _load_all(self) -> None:
        if not self._snapshot_dir:
            return
        for f in sorted(self._snapshot_dir.glob("ch_*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                ch = data.get("chapter_number", 0)
                self._snapshots[ch] = ContinuitySnapshot(
                    chapter_number=ch,
                    characters=data.get("characters", {}),
                    timeline=data.get("timeline", {}),
                    items=data.get("items", {}),
                    settings=data.get("settings", {}),
                    plot_threads=data.get("plot_threads", {}),
                    entity_names=data.get("entity_names", {}),
                    values=data.get("values", {}),
                )
            except Exception as e:
                logger.warning(f"加载快照失败 ch_{f.stem}: {e}")

    def save_snapshot(self, snapshot: ContinuitySnapshot) -> None:
        if not self._snapshot_dir:
            return
        self._snapshots[snapshot.chapter_number] = snapshot

        path = self._snapshot_dir / f"ch_{snapshot.chapter_number:04d}.json"
        data = {
            "chapter_number": snapshot.chapter_number,
            "characters": snapshot.characters,
            "timeline": snapshot.timeline,
            "items": snapshot.items,
            "settings": snapshot.settings,
            "plot_threads": snapshot.plot_threads,
            "entity_names": snapshot.entity_names,
            "values": snapshot.values,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_snapshot(self, chapter: int) -> ContinuitySnapshot | None:
        return self._snapshots.get(chapter)

    def get_latest_snapshot(self) -> ContinuitySnapshot | None:
        if not self._snapshots:
            return None
        return self._snapshots[max(self._snapshots.keys())]

    def diff_snapshots(self, prev_chapter: int, curr_chapter: int) -> dict[str, Any]:
        prev = self.get_snapshot(prev_chapter)
        curr = self.get_snapshot(curr_chapter)
        if not prev or not curr:
            return {"error": "快照不存在"}

        diff: dict[str, Any] = {
            "from_chapter": prev_chapter,
            "to_chapter": curr_chapter,
            "changes": {},
        }

        char_changes: list[dict] = []
        all_char_ids = set(prev.characters.keys()) | set(curr.characters.keys())
        for cid in all_char_ids:
            if cid not in prev.characters:
                char_changes.append({"id": cid, "change": "added", "state": curr.characters[cid]})
            elif cid not in curr.characters:
                char_changes.append({"id": cid, "change": "removed"})
            else:
                field_changes = {}
                for field in prev.characters[cid]:
                    if (
                        field in curr.characters[cid]
                        and prev.characters[cid][field] != curr.characters[cid][field]
                    ):
                        field_changes[field] = {
                            "from": prev.characters[cid][field],
                            "to": curr.characters[cid][field],
                        }
                if field_changes:
                    char_changes.append({"id": cid, "change": "modified", "fields": field_changes})
        if char_changes:
            diff["changes"]["characters"] = char_changes

        item_changes: list[dict] = []
        all_item_ids = set(prev.items.keys()) | set(curr.items.keys())
        for iid in all_item_ids:
            if iid not in prev.items:
                item_changes.append({"id": iid, "change": "added"})
            elif iid not in curr.items:
                item_changes.append({"id": iid, "change": "removed"})
            else:
                field_changes = {}
                for field in prev.items[iid]:
                    if (
                        field in curr.items[iid]
                        and prev.items[iid][field] != curr.items[iid][field]
                    ):
                        field_changes[field] = {
                            "from": prev.items[iid][field],
                            "to": curr.items[iid][field],
                        }
                if field_changes:
                    item_changes.append({"id": iid, "change": "modified", "fields": field_changes})
        if item_changes:
            diff["changes"]["items"] = item_changes

        return diff


# ─── 主引擎 ──────────────────────────────────────────


class ContinuityEngine:
    """确定性连续性引擎主类"""

    def __init__(self, book_id: str = ""):
        self.book_id = book_id
        self.snapshots = SnapshotManager(book_id)
        self.checker = ContinuityChecker()
        self._previous_report: ContinuityReport | None = None

    def check(
        self,
        previous_snapshot: ContinuitySnapshot,
        current_snapshot: ContinuitySnapshot,
        text: str = "",
    ) -> ContinuityReport:
        violations: list[ContinuityViolation] = []
        check_results: dict[str, dict] = {}

        char_violations = self.checker.check_character_continuity(
            previous_snapshot.characters, current_snapshot.characters
        )
        violations.extend(char_violations)
        check_results["角色状态连续性"] = {
            "passed": not any(v.severity == ContinuitySeverity.BLOCKER for v in char_violations),
            "violations": len(char_violations),
        }

        time_violations = self.checker.check_timeline_continuity(
            previous_snapshot.timeline, current_snapshot.timeline
        )
        violations.extend(time_violations)
        check_results["时间线连续性"] = {
            "passed": not any(v.severity == ContinuitySeverity.BLOCKER for v in time_violations),
            "violations": len(time_violations),
        }

        item_violations = self.checker.check_item_continuity(
            previous_snapshot.items, current_snapshot.items
        )
        violations.extend(item_violations)
        check_results["物品连续性"] = {
            "passed": not any(v.severity == ContinuitySeverity.BLOCKER for v in item_violations),
            "violations": len(item_violations),
        }

        setting_violations = self.checker.check_setting_continuity(
            previous_snapshot.settings, current_snapshot.settings
        )
        violations.extend(setting_violations)
        check_results["设定连续性"] = {
            "passed": not any(v.severity == ContinuitySeverity.BLOCKER for v in setting_violations),
            "violations": len(setting_violations),
        }

        plot_violations = self.checker.check_plot_continuity(
            previous_snapshot.plot_threads, current_snapshot.plot_threads
        )
        violations.extend(plot_violations)
        check_results["情节连续性"] = {
            "passed": not any(v.severity == ContinuitySeverity.BLOCKER for v in plot_violations),
            "violations": len(plot_violations),
        }

        naming_violations = self.checker.check_naming_continuity(
            previous_snapshot.entity_names, current_snapshot.entity_names, text
        )
        violations.extend(naming_violations)
        check_results["称呼连续性"] = {
            "passed": not any(v.severity == ContinuitySeverity.BLOCKER for v in naming_violations),
            "violations": len(naming_violations),
        }

        value_violations = self.checker.check_value_continuity(
            previous_snapshot.values, current_snapshot.values
        )
        violations.extend(value_violations)
        check_results["数值连续性"] = {
            "passed": not any(v.severity == ContinuitySeverity.BLOCKER for v in value_violations),
            "violations": len(value_violations),
        }

        blockers = [v for v in violations if v.severity == ContinuitySeverity.BLOCKER]
        warnings = [v for v in violations if v.severity == ContinuitySeverity.WARNING]
        infos = [v for v in violations if v.severity == ContinuitySeverity.INFO]

        passed = len(blockers) == 0
        score = max(0.0, 1.0 - len(blockers) * 0.15 - len(warnings) * 0.05)

        suggestions: list[str] = []
        if blockers:
            suggestions.append(f"🔴 {len(blockers)} 个阻断项必须修复")
            suggestions.extend(f"  - {b.description}" for b in blockers)
        if warnings:
            suggestions.append(f"🟡 {len(warnings)} 个警告项建议修复")

        report = ContinuityReport(
            chapter_number=current_snapshot.chapter_number,
            passed=passed,
            overall_score=round(score, 2),
            violations=violations,
            check_results=check_results,
            stats={
                "total_violations": len(violations),
                "blockers": len(blockers),
                "warnings": len(warnings),
                "infos": len(infos),
            },
            suggestions=suggestions,
        )

        self._previous_report = report
        return report


# ─── 辅助函数 ────────────────────────────────────────


def _emotion_distance(e1: str, e2: str) -> int:
    emotion_scale = [
        "绝望",
        "恐惧",
        "愤怒",
        "悲伤",
        "焦虑",
        "平静",
        "好奇",
        "期待",
        "高兴",
        "兴奋",
        "狂喜",
    ]
    try:
        i1 = emotion_scale.index(e1)
        i2 = emotion_scale.index(e2)
        return abs(i2 - i1)
    except ValueError:
        return 0 if e1 == e2 else 3


def _time_to_hours(time_str: str) -> float:
    try:
        parts = time_str.split(":")
        return float(parts[0]) + float(parts[1]) / 60
    except (ValueError, IndexError):
        return 12.0


def _level_to_rank(level_str: str) -> int:
    level_map = {
        "凡人": 0,
        "练气": 1,
        "筑基": 2,
        "金丹": 3,
        "元婴": 4,
        "化神": 5,
        "炼虚": 6,
        "合体": 7,
        "大乘": 8,
        "渡劫": 9,
        "仙人": 10,
    }
    for key, val in level_map.items():
        if key in level_str:
            return val
    nums = re.findall(r"\d+", level_str)
    return int(nums[0]) if nums else 0


# ─── 工厂函数 ────────────────────────────────────────

_continuity_engines: dict[str, ContinuityEngine] = {}


def get_continuity_engine(book_id: str = "") -> ContinuityEngine:
    if book_id not in _continuity_engines:
        _continuity_engines[book_id] = ContinuityEngine(book_id)
    return _continuity_engines[book_id]
