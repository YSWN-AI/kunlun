"""
版本差异引擎 — 文本差异对比与版本管理

支持:
- 行级差异对比 (unified diff)
- 词级差异对比 (word-level)
- 差异统计 (新增/删除/修改行数)
- 版本快照 (snapshot)
- 版本回滚建议

基于 Python 标准库 difflib，零外部依赖。

用法:
    engine = DiffEngine()
    diff = engine.compare("旧版本内容", "新版本内容")
    print(f"新增 {diff.lines_added} 行, 删除 {diff.lines_removed} 行")
"""

from __future__ import annotations

import difflib
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiffResult:
    """差异对比结果"""

    lines_added: int = 0
    lines_removed: int = 0
    lines_modified: int = 0
    total_changes: int = 0
    unified_diff: str = ""
    change_ratio: float = 0.0  # 变化比例 (0.0 ~ 1.0)

    @property
    def is_empty(self) -> bool:
        return self.total_changes == 0


@dataclass
class VersionSnapshot:
    """版本快照"""

    version_id: str
    doc_id: str
    content: str
    timestamp: float = field(default_factory=time.time)
    author_id: str = ""
    description: str = ""
    parent_version_id: str = ""


class DiffEngine:
    """差异引擎

    提供文本差异对比、版本快照管理、变更统计功能。

    用法:
        engine = DiffEngine()
        result = engine.compare(original, revised)
        engine.save_snapshot("doc_001", revised, author_id="user_001")
    """

    def __init__(self):
        self._snapshots: dict[str, list[VersionSnapshot]] = {}
        self._max_snapshots: int = 100

    def compare(
        self,
        original: str,
        revised: str,
        context_lines: int = 3,
    ) -> DiffResult:
        """对比两个文本的差异

        Args:
            original: 原始文本
            revised: 修订文本
            context_lines: 差异上下文中保留的行数

        Returns:
            DiffResult: 包含差异统计和 unified diff 文本
        """
        original_lines = original.splitlines(keepends=True)
        revised_lines = revised.splitlines(keepends=True)

        differ = difflib.unified_diff(
            original_lines,
            revised_lines,
            fromfile="original",
            tofile="revised",
            n=context_lines,
        )
        diff_lines = list(differ)

        added = 0
        removed = 0

        for line in diff_lines[2:]:  # skip header lines
            if line.startswith("+") and not line.startswith("+++"):
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                removed += 1

        total = added + removed
        total_original = len(original_lines)
        ratio = min(total / max(total_original, 1), 1.0)

        return DiffResult(
            lines_added=added,
            lines_removed=removed,
            lines_modified=max(added, removed),
            total_changes=total,
            unified_diff="".join(diff_lines),
            change_ratio=ratio,
        )

    def word_diff(self, original: str, revised: str) -> list[dict[str, Any]]:
        """词级差异对比 — 返回结构化的变更列表

        Returns:
            list of dicts with keys: type(add/remove/equal), text, pos
        """
        orig_words = original.split()
        rev_words = revised.split()

        matcher = difflib.SequenceMatcher(None, orig_words, rev_words)
        changes: list[dict[str, Any]] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                pass  # 不输出相同部分以减少数据量
            elif tag == "replace":
                changes.append(
                    {
                        "type": "replace",
                        "old_text": " ".join(orig_words[i1:i2]),
                        "new_text": " ".join(rev_words[j1:j2]),
                        "old_pos": i1,
                        "new_pos": j1,
                    }
                )
            elif tag == "delete":
                changes.append(
                    {
                        "type": "delete",
                        "old_text": " ".join(orig_words[i1:i2]),
                        "old_pos": i1,
                    }
                )
            elif tag == "insert":
                changes.append(
                    {
                        "type": "insert",
                        "new_text": " ".join(rev_words[j1:j2]),
                        "new_pos": j1,
                    }
                )

        return changes

    def save_snapshot(
        self,
        doc_id: str,
        content: str,
        author_id: str = "",
        description: str = "",
        parent_version_id: str = "",
    ) -> VersionSnapshot:
        """保存版本快照"""
        import uuid

        snapshots = self._snapshots.setdefault(doc_id, [])

        version_id = str(uuid.uuid4())[:12]
        snapshot = VersionSnapshot(
            version_id=version_id,
            doc_id=doc_id,
            content=content,
            author_id=author_id,
            description=description,
            parent_version_id=parent_version_id or (snapshots[-1].version_id if snapshots else ""),
        )

        snapshots.append(snapshot)

        # 限制快照数量
        if len(snapshots) > self._max_snapshots:
            snapshots[:] = snapshots[-self._max_snapshots :]

        return snapshot

    def get_snapshot(self, doc_id: str, version_id: str) -> VersionSnapshot | None:
        """获取指定版本快照"""
        for s in self._snapshots.get(doc_id, []):
            if s.version_id == version_id:
                return s
        return None

    def get_latest_snapshot(self, doc_id: str) -> VersionSnapshot | None:
        """获取最新版本"""
        snapshots = self._snapshots.get(doc_id, [])
        return snapshots[-1] if snapshots else None

    def get_version_history(self, doc_id: str) -> list[dict[str, Any]]:
        """获取版本历史（不含内容，仅元数据）"""
        return [
            {
                "version_id": s.version_id,
                "timestamp": s.timestamp,
                "author_id": s.author_id,
                "description": s.description,
                "parent_version_id": s.parent_version_id,
            }
            for s in self._snapshots.get(doc_id, [])
        ]

    def compare_versions(
        self,
        doc_id: str,
        version_id_old: str,
        version_id_new: str,
    ) -> DiffResult | None:
        """对比两个版本"""
        old_snap = self.get_snapshot(doc_id, version_id_old)
        new_snap = self.get_snapshot(doc_id, version_id_new)
        if not old_snap or not new_snap:
            return None
        return self.compare(old_snap.content, new_snap.content)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_docs": len(self._snapshots),
            "total_snapshots": sum(len(v) for v in self._snapshots.values()),
        }
