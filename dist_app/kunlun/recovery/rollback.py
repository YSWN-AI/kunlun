"""
章节回滚系统 — 每章自动版本快照，支持任意回滚

对应 inkos write rewrite 命令
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

from loguru import logger

from kunlun.config import settings


@dataclass
class ChapterVersion:
    version_id: str
    book_id: str
    chapter: int
    created_at: float
    word_count: int
    draft_path: str
    snapshot_path: str
    audit_score: float = 0
    note: str = ""


class ChapterVersionManager:
    """章节版本管理器"""

    def __init__(self, book_id: str):
        self.book_id = book_id
        self.versions_dir = settings.DATA_DIR / "versions" / book_id
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.versions_dir / "index.json"
        self._index = self._load_index()

    def _load_index(self) -> dict:
        if self.index_path.exists():
            try:
                return json.loads(self.index_path.read_text())
            except Exception:
                logger.debug("恢复索引文件读取失败")
        return {"versions": {}}

    def _save_index(self):
        self.index_path.write_text(json.dumps(self._index, ensure_ascii=False, indent=2))

    def save_version(
        self, chapter: int, draft: str, audit_score: float = 0, note: str = ""
    ) -> ChapterVersion:
        """保存章节版本"""
        version_id = f"ch{chapter}_v{int(time.time())}"
        version_dir = self.versions_dir / f"ch{chapter:04d}"
        version_dir.mkdir(parents=True, exist_ok=True)

        # 保存正文
        draft_path = version_dir / f"{version_id}.txt"
        draft_path.write_text(draft, encoding="utf-8")

        # 保存元数据
        meta_path = version_dir / f"{version_id}.meta.json"
        meta = {
            "chapter": chapter,
            "word_count": len(draft),
            "audit_score": audit_score,
            "note": note,
            "created_at": time.time(),
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))

        v = ChapterVersion(
            version_id,
            self.book_id,
            chapter,
            time.time(),
            len(draft),
            str(draft_path),
            str(meta_path),
            audit_score,
            note,
        )

        # 更新索引
        ch_key = str(chapter)
        if ch_key not in self._index["versions"]:
            self._index["versions"][ch_key] = []
        self._index["versions"][ch_key].append(
            {
                "version_id": version_id,
                "created_at": v.created_at,
                "word_count": v.word_count,
                "audit_score": audit_score,
                "note": note,
            }
        )
        self._save_index()

        # 保留最近10个版本
        versions = self._index["versions"][ch_key]
        if len(versions) > 10:
            for old in versions[:-10]:
                old_path = version_dir / f"{old['version_id']}.txt"
                if old_path.exists():
                    old_path.unlink()
            self._index["versions"][ch_key] = versions[-10:]
            self._save_index()

        logger.info(f"[Rollback] 版本已保存: {version_id} ({len(draft)}字)")
        return v

    def get_versions(self, chapter: int) -> list[dict]:
        """获取某章的所有版本"""
        return self._index["versions"].get(str(chapter), [])

    def get_version(self, version_id: str) -> str | None:
        """获取指定版本的内容"""
        for ch_versions in self._index["versions"].values():
            for v in ch_versions:
                if v["version_id"] == version_id:
                    path = (
                        self.versions_dir
                        / f"ch{int(v.get('chapter', 0)):04d}"
                        / f"{version_id}.txt"
                    )
                    if path.exists():
                        return path.read_text(encoding="utf-8")
        return None

    def get_latest(self, chapter: int) -> str | None:
        """获取最新版本"""
        versions = self.get_versions(chapter)
        if versions:
            latest = versions[-1]
            return self.get_version(latest["version_id"])
        return None

    def rollback(self, chapter: int, version_id: str) -> str | None:
        """回滚到指定版本"""
        draft = self.get_version(version_id)
        if draft:
            # 先保存当前版本
            current = self.get_latest(chapter)
            if current:
                self.save_version(chapter, current, note="rollback前自动保存")
            logger.info(f"[Rollback] 第{chapter}章已回滚到 {version_id}")
        return draft

    def diff_versions(self, version_id_a: str, version_id_b: str) -> str:
        """比较两个版本的差异"""
        import difflib

        text_a = self.get_version(version_id_a) or ""
        text_b = self.get_version(version_id_b) or ""
        diff = difflib.unified_diff(text_a.splitlines(), text_b.splitlines(), lineterm="", n=1)
        return "\n".join(list(diff)[:100])


# 全局实例管理
_managers: dict[str, ChapterVersionManager] = {}


def get_version_manager(book_id: str) -> ChapterVersionManager:
    if book_id not in _managers:
        _managers[book_id] = ChapterVersionManager(book_id)
    return _managers[book_id]
