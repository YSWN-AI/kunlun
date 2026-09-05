"""
昆仑创作引擎 — SQLite FTS5 全文搜索仓储实现

封装 SQLite FTS5，提供中文全文检索能力。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from loguru import logger

from kunlun.config import settings
from kunlun.kg.repositories.base import FullTextRepository, SearchResult


class SQLiteFTSRepository(FullTextRepository):
    """SQLite FTS5 全文搜索仓储"""

    _SUPPORTED_TABLES = ("chapters", "notes", "outlines")

    def __init__(self):
        db_path = getattr(
            settings,
            "sqlite_path",
            str(settings.DATA_DIR / "kunlun_search.db"),
        )
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._ensure_tables()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_tables(self) -> None:
        """确保 FTS5 表存在"""
        conn = self._get_conn()
        for table in self._SUPPORTED_TABLES:
            conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS fts_{table}
                USING fts5(content, metadata, tokenize='unicode61 remove_diacritics 1')
            """)
        conn.commit()

    async def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        table: str = "chapters",
    ) -> list[SearchResult]:
        if table not in self._SUPPORTED_TABLES:
            logger.warning(f"FTS: 不支持的表 '{table}'，回退到 chapters")
            table = "chapters"

        conn = self._get_conn()
        try:
            # 使用 FTS5 的 highlight 获取片段
            rows = conn.execute(
                f"""
                SELECT rowid, content, snippet(fts_{table}, 1, '<b>', '</b>', '...', 40) as snippet,
                       metadata, rank
                FROM fts_{table}
                WHERE fts_{table} MATCH ?
                ORDER BY rank
                LIMIT ? OFFSET ?
                """,
                (query, limit, offset),
            ).fetchall()

            import json

            return [
                SearchResult(
                    doc_id=str(r["rowid"]),
                    score=float(r["rank"]) if r["rank"] is not None else 0.0,
                    content=r["content"] or "",
                    snippet=r["snippet"] or "",
                    metadata=json.loads(r["metadata"]) if r["metadata"] else {},
                )
                for r in rows
            ]
        except sqlite3.OperationalError as e:
            # 语法错误 → 回退到简单 LIKE
            logger.debug(f"FTS 查询降级为 LIKE: {e}")
            rows = conn.execute(
                f"""
                SELECT rowid, content, '' as snippet, metadata, 0 as rank
                FROM fts_{table}
                WHERE content LIKE ?
                LIMIT ? OFFSET ?
                """,
                (f"%{query}%", limit, offset),
            ).fetchall()

            import json

            return [
                SearchResult(
                    doc_id=str(r["rowid"]),
                    score=0.0,
                    content=r["content"] or "",
                    snippet="",
                    metadata=json.loads(r["metadata"]) if r["metadata"] else {},
                )
                for r in rows
            ]

    async def index(
        self,
        doc_id: str,
        content: str,
        metadata: dict | None = None,
        table: str = "chapters",
    ) -> None:
        if table not in self._SUPPORTED_TABLES:
            table = "chapters"

        conn = self._get_conn()
        import json

        # 先删除旧记录
        conn.execute(
            f"DELETE FROM fts_{table} WHERE rowid = ?",
            (int(doc_id),),
        )
        # 插入新记录
        conn.execute(
            f"INSERT INTO fts_{table}(rowid, content, metadata) VALUES (?, ?, ?)",
            (int(doc_id), content, json.dumps(metadata or {}, ensure_ascii=False)),
        )
        conn.commit()

    async def delete(self, doc_id: str, table: str = "chapters") -> None:
        if table not in self._SUPPORTED_TABLES:
            table = "chapters"

        conn = self._get_conn()
        conn.execute(
            f"DELETE FROM fts_{table} WHERE rowid = ?",
            (int(doc_id),),
        )
        conn.commit()

    async def health_check(self) -> bool:
        try:
            conn = self._get_conn()
            conn.execute("SELECT 1 FROM fts_chapters LIMIT 0")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def close_sync(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
