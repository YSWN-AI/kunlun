"""
draft 草稿版本管理 — 版本保存、差异对比、回滚恢复

核心能力:
1. 自动保存草稿版本（时间戳+字数快照）
2. 版本间差异对比（diff算法）
3. 版本回滚
4. 零LLM纯文本操作
"""

from __future__ import annotations

import difflib
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from loguru import logger

from kunlun.core.extension_base import BaseExtensionModule


@dataclass
class DraftVersion:
    """单个草稿版本"""

    version_id: str
    text: str
    word_count: int = 0
    created_at: str = ""
    label: str = ""  # 用户标签（如"v1-初稿"）
    chapter_id: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.word_count:
            self.word_count = len(self.text)


@dataclass
class VersionDiff:
    """版本差异"""

    from_version: str
    to_version: str
    added_lines: int = 0
    removed_lines: int = 0
    modified_lines: int = 0
    added_words: int = 0
    removed_words: int = 0
    similarity: float = 0.0  # 0-1
    diff_html: str = ""  # 带标记的HTML差异
    unified_diff: str = ""  # 标准unified diff

    def summary(self) -> str:
        return (
            f"{self.from_version} → {self.to_version}: "
            f"+{self.added_words}/-{self.removed_words}字, "
            f"相似度{self.similarity:.0%}"
        )


@dataclass
class DraftStats:
    """草稿统计"""

    total_versions: int = 0
    total_words_written: int = 0  # 累计写作字数（含删除）
    current_word_count: int = 0
    first_version_at: str = ""
    last_modified_at: str = ""
    average_words_per_version: float = 0.0


class DraftManager(BaseExtensionModule):
    """草稿版本管理器"""

    def __init__(self, book_id: str = ""):
        super().__init__(book_id)
        self._versions: dict[str, list[DraftVersion]] = defaultdict(list)
        self._current: dict[str, DraftVersion] = {}

    def save_version(
        self,
        chapter_id: str,
        text: str,
        label: str = "",
    ) -> DraftVersion:
        """保存一个新版本"""
        version = DraftVersion(
            version_id=f"v{len(self._versions.get(chapter_id, [])) + 1}",
            text=text,
            word_count=len(text),
            chapter_id=chapter_id,
            label=label or f"自动保存-{datetime.now().strftime('%H:%M')}",
        )

        if chapter_id not in self._versions:
            self._versions[chapter_id] = []
        self._versions[chapter_id].append(version)
        self._current[chapter_id] = version

        logger.info(f"草稿已保存: {chapter_id} {version.version_id} ({version.word_count}字)")
        return version

    def get_current(self, chapter_id: str) -> DraftVersion | None:
        """获取当前版本"""
        return self._current.get(chapter_id)

    def get_version(self, chapter_id: str, version_id: str) -> DraftVersion | None:
        """获取指定版本"""
        versions = self._versions.get(chapter_id, [])
        for v in versions:
            if v.version_id == version_id:
                return v
        return None

    def list_versions(self, chapter_id: str) -> list[dict[str, Any]]:
        """列出所有版本摘要"""
        versions = self._versions.get(chapter_id, [])
        return [
            {
                "version_id": v.version_id,
                "word_count": v.word_count,
                "created_at": v.created_at,
                "label": v.label,
                "is_current": v == self._current.get(chapter_id),
            }
            for v in versions
        ]

    def diff_versions(
        self,
        chapter_id: str,
        from_version_id: str,
        to_version_id: str,
    ) -> VersionDiff | None:
        """对比两个版本"""
        v_from = self.get_version(chapter_id, from_version_id)
        v_to = self.get_version(chapter_id, to_version_id)

        if not v_from or not v_to:
            logger.warning(f"版本不存在: {from_version_id} → {to_version_id}")
            return None

        diff = VersionDiff(
            from_version=from_version_id,
            to_version=to_version_id,
        )

        # 行级对比
        lines_from = v_from.text.split("\n")
        lines_to = v_to.text.split("\n")

        differ = difflib.unified_diff(
            lines_from,
            lines_to,
            fromfile=from_version_id,
            tofile=to_version_id,
            lineterm="",
        )
        diff.unified_diff = "\n".join(differ)

        # 统计
        matcher = difflib.SequenceMatcher(None, v_from.text, v_to.text)
        diff.similarity = matcher.ratio()

        opcodes = matcher.get_opcodes()
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "insert":
                diff.added_words += len(v_to.text[j1:j2])
            elif tag == "delete":
                diff.removed_words += len(v_from.text[i1:i2])
            elif tag == "replace":
                diff.modified_lines += 1
                diff.added_words += len(v_to.text[j1:j2])
                diff.removed_words += len(v_from.text[i1:i2])

        # HTML差异
        diff.diff_html = self._generate_diff_html(v_from.text, v_to.text)

        logger.info(diff.summary())
        return diff

    def rollback(self, chapter_id: str, version_id: str) -> DraftVersion | None:
        """回滚到指定版本"""
        version = self.get_version(chapter_id, version_id)
        if not version:
            logger.warning(f"无法回滚：版本{version_id}不存在")
            return None

        # 回滚 = 基于旧版本创建新版本
        rollback_version = self.save_version(
            chapter_id=chapter_id,
            text=version.text,
            label=f"回滚至{version_id}",
        )
        logger.info(f"已回滚: {chapter_id} → {version_id}")
        return rollback_version

    def get_stats(self, chapter_id: str) -> DraftStats:
        """获取草稿统计"""
        versions = self._versions.get(chapter_id, [])
        stats = DraftStats()

        if not versions:
            return stats

        stats.total_versions = len(versions)
        stats.current_word_count = versions[-1].word_count
        stats.first_version_at = versions[0].created_at
        stats.last_modified_at = versions[-1].created_at

        # 累计字数
        for i, version in enumerate(versions):
            if i == 0:
                stats.total_words_written = version.word_count
            else:
                # 只计入新增字数
                added = version.word_count - versions[i - 1].word_count
                if added > 0:
                    stats.total_words_written += added
                else:
                    stats.total_words_written += int(version.word_count * 0.1)  # 重写算10%

        stats.average_words_per_version = (
            stats.total_words_written / len(versions) if versions else 0
        )

        return stats

    @staticmethod
    def _generate_diff_html(original: str, modified: str) -> str:
        """生成带高亮的HTML差异"""
        differ = difflib.HtmlDiff(wrapcolumn=80)
        return differ.make_file(
            original.split("\n"),
            modified.split("\n"),
            fromdesc="原始版本",
            todesc="新版本",
        )

    def cleanup_old_versions(self, chapter_id: str, keep: int = 10) -> int:
        """清理旧版本，只保留最近N个"""
        versions = self._versions.get(chapter_id, [])
        if len(versions) <= keep:
            return 0

        removed = len(versions) - keep
        self._versions[chapter_id] = versions[-keep:]
        logger.info(f"已清理{removed}个旧版本: {chapter_id}")
        return removed


_managers: dict[str, DraftManager] = {}


def get_draft_manager(book_id: str = "") -> DraftManager:
    """获取草稿管理器实例"""
    if book_id not in _managers:
        _managers[book_id] = DraftManager(book_id=book_id)
    return _managers[book_id]
