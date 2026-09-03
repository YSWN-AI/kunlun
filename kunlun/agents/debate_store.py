"""
昆仑创作引擎 — 辩论结果结构化存储 (DebateStore)

将多Agent辩论的结果以JSON文件形式持久化存储，支持按书籍/章节/类型查询，
提供统计、归档和历史追溯能力。纯文件存储，不依赖数据库。

存储结构:
  data/debate_records/
    book_<id>/
      chapter_<num>_<type>.json
      archive/
        chapter_<num>_<type>.json
"""

from __future__ import annotations

import json
import shutil
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

# ══════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════


@dataclass
class DebateRecord:
    """辩论记录

    Attributes:
        record_id: 记录唯一ID
        book_id: 书籍ID
        chapter: 章节号
        debate_type: 辩论类型 (blueprint_review / chapter_final / general)
        created_at: 创建时间戳
        debate_result: DebateResult.to_dict() 的字典形式
        final_decision: 最终决议文本
        revision_suggestions: 修订建议列表
        consensus_score: 共识度 0.0-1.0
        status: 状态 (pending / resolved / archived)
        metadata: 附加元数据
    """

    record_id: str
    book_id: str
    chapter: int
    debate_type: str
    created_at: float = field(default_factory=time.time)
    debate_result: dict[str, Any] = field(default_factory=dict)
    final_decision: str = ""
    revision_suggestions: list[dict[str, Any]] = field(default_factory=list)
    consensus_score: float = 0.0
    status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DebateRecord:
        """从字典反序列化"""
        return cls(
            record_id=data.get("record_id", ""),
            book_id=data.get("book_id", "default"),
            chapter=data.get("chapter", 0),
            debate_type=data.get("debate_type", "general"),
            created_at=data.get("created_at", time.time()),
            debate_result=data.get("debate_result", {}),
            final_decision=data.get("final_decision", ""),
            revision_suggestions=data.get("revision_suggestions", []),
            consensus_score=data.get("consensus_score", 0.0),
            status=data.get("status", "pending"),
            metadata=data.get("metadata", {}),
        )


# ══════════════════════════════════════════════════════
# DebateStore
# ══════════════════════════════════════════════════════


class DebateStore:
    """辩论结果结构化存储

    纯文件存储，每条辩论记录保存为独立JSON文件。
    支持按书籍/章节/类型/状态查询，统计和归档。
    """

    VALID_TYPES = ("blueprint_review", "chapter_final", "general")
    VALID_STATUSES = ("pending", "resolved", "archived")

    def __init__(self, storage_dir: str = "data/debate_records") -> None:
        self.storage_dir = storage_dir
        Path(storage_dir).mkdir(parents=True, exist_ok=True)

    # ── 内部工具 ────────────────────────────────────────

    def _book_dir(self, book_id: str) -> Path:
        return Path(self.storage_dir) / f"book_{book_id}"

    def _record_path(self, book_id: str, chapter: int, debate_type: str) -> Path:
        return self._book_dir(book_id) / f"chapter_{chapter}_{debate_type}.json"

    def _archive_dir(self, book_id: str) -> Path:
        return self._book_dir(book_id) / "archive"

    def _generate_record_id(self, book_id: str, chapter: int, debate_type: str) -> str:
        timestamp = int(time.time() * 1000)
        return f"{book_id}_ch{chapter}_{debate_type}_{timestamp}"

    def _iter_all_records(self) -> list[DebateRecord]:
        """遍历所有非归档记录"""
        records: list[DebateRecord] = []
        root = Path(self.storage_dir)
        if not root.is_dir():
            return records
        for book_path in root.iterdir():
            if not book_path.is_dir() or not book_path.name.startswith("book_"):
                continue
            for filepath in book_path.iterdir():
                if not filepath.name.endswith(".json"):
                    continue
                record = self._load_from_file(filepath)
                if record is not None:
                    records.append(record)
        return records

    @staticmethod
    def _load_from_file(filepath: Path) -> DebateRecord | None:
        try:
            with filepath.open(encoding="utf-8") as f:
                data = json.load(f)
            return DebateRecord.from_dict(data)
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.warning(f"[DebateStore] 加载记录失败 {filepath}: {e}")
            return None

    # ── 保存与加载 ──────────────────────────────────────

    def save_record(self, record: DebateRecord) -> str:
        """保存辩论记录到JSON文件

        Args:
            record: 辩论记录

        Returns:
            record_id 记录ID
        """
        if not record.record_id:
            record.record_id = self._generate_record_id(
                record.book_id, record.chapter, record.debate_type
            )

        book_dir = self._book_dir(record.book_id)
        book_dir.mkdir(parents=True, exist_ok=True)

        filepath = self._record_path(record.book_id, record.chapter, record.debate_type)
        try:
            with filepath.open("w", encoding="utf-8") as f:
                json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)
            logger.debug(
                f"[DebateStore] 保存记录 {record.record_id} -> {filepath}"
            )
        except OSError as e:
            logger.error(f"[DebateStore] 保存记录失败: {e}")
            raise

        return record.record_id

    def load_record(self, record_id: str) -> DebateRecord | None:
        """按record_id加载记录

        Args:
            record_id: 记录ID

        Returns:
            DebateRecord 或 None
        """
        for record in self._iter_all_records():
            if record.record_id == record_id:
                return record
        return None

    # ── 查询 ────────────────────────────────────────────

    def get_records(
        self,
        book_id: str | None = None,
        chapter: int | None = None,
        debate_type: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[DebateRecord]:
        """按条件查询记录

        Args:
            book_id: 书籍ID过滤
            chapter: 章节号过滤
            debate_type: 辩论类型过滤
            status: 状态过滤
            limit: 返回数量上限

        Returns:
            符合条件的记录列表（按创建时间倒序）
        """
        records = self._iter_all_records()

        if book_id is not None:
            records = [r for r in records if r.book_id == book_id]
        if chapter is not None:
            records = [r for r in records if r.chapter == chapter]
        if debate_type is not None:
            records = [r for r in records if r.debate_type == debate_type]
        if status is not None:
            records = [r for r in records if r.status == status]

        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[:limit]

    def get_latest_record(
        self, book_id: str, chapter: int, debate_type: str
    ) -> DebateRecord | None:
        """获取某书籍某章节某类型的最新记录

        Args:
            book_id: 书籍ID
            chapter: 章节号
            debate_type: 辩论类型

        Returns:
            最新记录或 None
        """
        filepath = self._record_path(book_id, chapter, debate_type)
        if filepath.is_file():
            return self._load_from_file(filepath)
        return None

    def get_debate_history(self, book_id: str, chapter: int) -> list[DebateRecord]:
        """获取某章节的辩论历史（所有类型）

        Args:
            book_id: 书籍ID
            chapter: 章节号

        Returns:
            该章节所有辩论记录（按创建时间倒序）
        """
        return self.get_records(book_id=book_id, chapter=chapter, limit=100)

    # ── 更新 ────────────────────────────────────────────

    def update_decision(
        self,
        record_id: str,
        final_decision: str,
        revision_suggestions: list[dict[str, Any]] | None = None,
    ) -> bool:
        """更新最终决议

        Args:
            record_id: 记录ID
            final_decision: 最终决议文本
            revision_suggestions: 修订建议（可选，None则不更新）

        Returns:
            是否更新成功
        """
        record = self.load_record(record_id)
        if record is None:
            logger.warning(f"[DebateStore] 更新决议失败，记录不存在: {record_id}")
            return False

        record.final_decision = final_decision
        if revision_suggestions is not None:
            record.revision_suggestions = revision_suggestions
        record.status = "resolved"

        try:
            self.save_record(record)
            return True
        except OSError:
            return False

    def update_status(self, record_id: str, status: str) -> bool:
        """更新记录状态

        Args:
            record_id: 记录ID
            status: 新状态 (pending / resolved / archived)

        Returns:
            是否更新成功
        """
        if status not in self.VALID_STATUSES:
            logger.warning(f"[DebateStore] 无效状态: {status}")
            return False

        record = self.load_record(record_id)
        if record is None:
            logger.warning(f"[DebateStore] 更新状态失败，记录不存在: {record_id}")
            return False

        record.status = status
        try:
            self.save_record(record)
            return True
        except OSError:
            return False

    # ── 统计 ────────────────────────────────────────────

    def get_statistics(self, book_id: str | None = None) -> dict[str, Any]:
        """统计辩论记录

        Args:
            book_id: 书籍ID过滤，None则统计全部

        Returns:
            统计字典: total_debates, avg_consensus, decision_distribution,
                     common_issue_types, type_distribution
        """
        records = self.get_records(book_id=book_id, limit=10000)

        if not records:
            return {
                "total_debates": 0,
                "avg_consensus": 0.0,
                "decision_distribution": {},
                "common_issue_types": [],
                "type_distribution": {},
            }

        total = len(records)
        avg_consensus = sum(r.consensus_score for r in records) / total

        decision_counter: Counter[str] = Counter()
        for r in records:
            if "通过" in r.final_decision and "不通过" not in r.final_decision:
                decision_counter["通过"] += 1
            elif "不通过" in r.final_decision:
                decision_counter["不通过"] += 1
            elif "有条件" in r.final_decision:
                decision_counter["有条件通过"] += 1
            else:
                decision_counter["未决议"] += 1

        type_counter = Counter(r.debate_type for r in records)

        issue_counter: Counter[str] = Counter()
        keywords = ("爽点", "节奏", "逻辑", "人物", "章末", "情感", "对话", "描写")
        for r in records:
            for sug in r.revision_suggestions:
                issue = sug.get("issue", "")
                if issue:
                    for keyword in keywords:
                        if keyword in issue:
                            issue_counter[keyword] += 1
                            break

        common_issues = issue_counter.most_common(10)

        return {
            "total_debates": total,
            "avg_consensus": round(avg_consensus, 3),
            "decision_distribution": dict(decision_counter),
            "common_issue_types": [{"type": k, "count": v} for k, v in common_issues],
            "type_distribution": dict(type_counter),
        }

    # ── 归档 ────────────────────────────────────────────

    def archive_old_records(self, book_id: str, before_chapter: int) -> int:
        """归档旧章节记录（移动到archive子目录）

        Args:
            book_id: 书籍ID
            before_chapter: 归档章节号小于此值的记录

        Returns:
            归档的记录数量
        """
        book_dir = self._book_dir(book_id)
        if not book_dir.is_dir():
            return 0

        archive_dir = self._archive_dir(book_id)
        archive_dir.mkdir(parents=True, exist_ok=True)

        archived_count = 0
        for filepath in book_dir.iterdir():
            if not filepath.name.endswith(".json"):
                continue
            if not filepath.name.startswith("chapter_"):
                continue
            try:
                parts = filepath.name[len("chapter_") :].split("_", 1)
                chapter_num = int(parts[0])
            except (ValueError, IndexError):
                continue

            if chapter_num < before_chapter:
                dst = archive_dir / filepath.name
                try:
                    shutil.move(str(filepath), str(dst))
                    archived_count += 1
                    logger.debug(f"[DebateStore] 归档记录: {filepath.name}")
                except OSError as e:
                    logger.warning(f"[DebateStore] 归档失败 {filepath.name}: {e}")

        logger.info(
            f"[DebateStore] 归档完成: {archived_count}条记录 (章节<{before_chapter})"
        )
        return archived_count
