"""
昆仑创作引擎 — 时序记忆管理器

灵感来源: InkOS SQLite时序记忆 + WenShape上下文引擎

核心机制:
  1. 对话历史按时间戳存储在SQLite中
  2. 基于相关性检索，而非全量注入
  3. 动态窗口调整，长对话场景下自动优化

使用方式:
    memory = TemporalMemory(book_id="test_book")
    memory.add_entry("user", "写一章玄幻小说")
    memory.add_entry("assistant", "好的，我来帮你写一章...")
    context = memory.retrieve_relevant(limit_tokens=4000)
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import time
from typing import Any

from loguru import logger

from kunlun.config import settings


class MemoryEntry:
    """单条记忆条目"""

    def __init__(
        self, entry_id: int, role: str, content: str, timestamp: float, metadata: dict | None = None
    ):
        self.entry_id = entry_id
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.metadata = metadata or {}

    def to_dict(self):
        return {
            "id": self.entry_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class TemporalMemory:
    """
    时序记忆管理器

    基于SQLite的对话历史存储与检索系统，支持：
    - 按时间戳顺序存储
    - 相关性加权检索
    - 动态Token预算管理
    - 长对话场景优化
    """

    def __init__(self, book_id: str):
        self.book_id = book_id
        self._db_path = settings.DATA_DIR / "memory" / f"{book_id}.db"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        self._ensure_connection()
        assert self._conn is not None
        cursor = self._conn.cursor()

        # 记忆条目表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL,
                metadata TEXT DEFAULT '{}',
                relevance_score REAL DEFAULT 1.0,
                accessed_count INTEGER DEFAULT 0,
                last_accessed REAL DEFAULT 0
            )
        """)

        # 索引优化
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON memory_entries(timestamp)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_relevance ON memory_entries(relevance_score)"
        )

        self._conn.commit()

    def _ensure_connection(self) -> sqlite3.Connection:
        """确保数据库连接"""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def add_entry(self, role: str, content: str, metadata: dict | None = None):
        """添加记忆条目"""
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO memory_entries (role, content, timestamp, metadata)
            VALUES (?, ?, ?, ?)
        """,
            (role, content, time.time(), json.dumps(metadata or {})),
        )

        conn.commit()
        return cursor.lastrowid

    def add_chapter_entry(
        self, chapter_number: int, content: str, arc_stage: str = "", pleasure_points: int = 0
    ):
        """添加章节记忆条目"""
        metadata = {
            "chapter": chapter_number,
            "arc_stage": arc_stage,
            "pleasure_points": pleasure_points,
            "type": "chapter",
        }
        return self.add_entry("chapter", content, metadata)

    def update_relevance(self, entry_id: int, relevance_score: float):
        """更新条目相关性分数"""
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE memory_entries
            SET relevance_score = ?, accessed_count = accessed_count + 1, last_accessed = ?
            WHERE id = ?
        """,
            (relevance_score, time.time(), entry_id),
        )

        conn.commit()

    def _estimate_tokens(self, text: str) -> int:
        """估算文本Token数"""
        chinese_chars = len(re.findall(r"[一-鿿]", text))
        english_words = len(re.findall(r"[a-zA-Z]+", text))
        other_chars = max(0, len(text) - chinese_chars - len(re.findall(r"[a-zA-Z]", text)))
        return int(chinese_chars / 1.5 + english_words * 0.75 + other_chars / 3.0)

    def _time_decay(self, hours_ago: float) -> float:
        """时间衰减函数 - 越近权重越高"""
        if hours_ago < 0.1:  # 10分钟内
            return 1.0
        return 1.0 / (1 + math.log(1 + hours_ago / 24))

    def _chapter_proximity_weight(self, entry_chapter: int, current_chapter: int) -> float:
        """章节距离权重"""
        dist = abs(current_chapter - entry_chapter)
        if dist == 0:
            return 1.0
        return 1.0 / (1 + math.log(1 + dist))

    def retrieve_relevant(
        self, limit_tokens: int = 4000, current_chapter: int = 0, _query_context: str | None = None
    ) -> list[MemoryEntry]:
        """
        检索相关记忆

        Args:
            limit_tokens: 返回内容的Token上限
            current_chapter: 当前章节号（用于章节距离加权）
            query_context: 查询上下文（用于相关性计算）

        Returns:
            按相关性排序的记忆条目列表
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        # 获取所有条目
        cursor.execute("SELECT * FROM memory_entries ORDER BY timestamp DESC")
        rows = cursor.fetchall()

        # 计算综合分数并排序
        scored_entries = []
        now = time.time()

        for row in rows:
            entry = MemoryEntry(
                entry_id=row["id"],
                role=row["role"],
                content=row["content"],
                timestamp=row["timestamp"],
                metadata=json.loads(row["metadata"]),
            )

            # 基础分数
            score = row["relevance_score"]

            # 时间衰减
            hours_ago = (now - entry.timestamp) / 3600
            time_weight = self._time_decay(hours_ago)
            score *= time_weight

            # 章节距离权重（如果是章节类型）
            if entry.metadata.get("type") == "chapter":
                chapter_num = entry.metadata.get("chapter", 0)
                chapter_weight = self._chapter_proximity_weight(chapter_num, current_chapter)
                score *= chapter_weight

            # 访问频率加成
            if row["accessed_count"] > 0:
                score *= 1 + min(row["accessed_count"] * 0.1, 0.5)

            scored_entries.append((score, entry))

        # 按分数降序排序
        scored_entries.sort(key=lambda x: -x[0])

        # 按Token预算选取
        result = []
        total_tokens = 0

        for score, entry in scored_entries:
            entry_tokens = self._estimate_tokens(entry.content)

            if total_tokens + entry_tokens <= limit_tokens:
                result.append(entry)
                total_tokens += entry_tokens
                # 更新访问计数
                self.update_relevance(entry.entry_id, score)
            # 尝试截断过长条目
            elif entry_tokens > limit_tokens * 0.5 and total_tokens < limit_tokens * 0.8:
                truncate_len = int(
                    len(entry.content) * (limit_tokens - total_tokens) / entry_tokens
                )
                truncated = entry.content[:truncate_len]
                # 在句子边界断开
                for punct in ["。", "！", "？", "\n", ".", "!", "?"]:
                    pos = truncated.rfind(punct)
                    if pos > truncate_len * 0.5:
                        truncated = truncated[: pos + 1]
                        break
                entry.content = truncated + "\n[内容截断...]"
                result.append(entry)
                total_tokens += self._estimate_tokens(entry.content)

            if total_tokens >= limit_tokens:
                break

        return result

    def get_recent_entries(self, limit: int = 20) -> list[MemoryEntry]:
        """获取最近的记忆条目"""
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM memory_entries
            ORDER BY timestamp DESC LIMIT ?
        """,
            (limit,),
        )

        rows = cursor.fetchall()
        return [
            MemoryEntry(
                entry_id=row["id"],
                role=row["role"],
                content=row["content"],
                timestamp=row["timestamp"],
                metadata=json.loads(row["metadata"]),
            )
            for row in rows
        ]

    def get_chapter_entries(self, chapter_number: int | None = None) -> list[MemoryEntry]:
        """获取章节相关条目"""
        conn = self._ensure_connection()
        cursor = conn.cursor()

        if chapter_number is not None:
            cursor.execute(
                """
                SELECT * FROM memory_entries
                WHERE metadata LIKE ?
                ORDER BY timestamp DESC
            """,
                (f"%chapter%{chapter_number}%",),
            )
        else:
            cursor.execute("""
                SELECT * FROM memory_entries
                WHERE metadata LIKE '%type": "chapter"%'
                ORDER BY timestamp DESC
            """)

        rows = cursor.fetchall()
        return [
            MemoryEntry(
                entry_id=row["id"],
                role=row["role"],
                content=row["content"],
                timestamp=row["timestamp"],
                metadata=json.loads(row["metadata"]),
            )
            for row in rows
        ]

    def clear_memory(self):
        """清空所有记忆"""
        conn = self._ensure_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memory_entries")
        conn.commit()
        logger.info(f"[TemporalMemory] 已清空书籍 {self.book_id} 的记忆")

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM memory_entries")
        count = cursor.fetchone()["count"]

        cursor.execute("SELECT SUM(LENGTH(content)) as total_chars FROM memory_entries")
        total_chars = cursor.fetchone()["total_chars"] or 0

        cursor.execute(
            "SELECT MIN(timestamp) as oldest, MAX(timestamp) as newest FROM memory_entries"
        )
        times = cursor.fetchone()

        return {
            "entry_count": count,
            "total_characters": total_chars,
            "estimated_tokens": int(total_chars / 1.5),
            "oldest_entry": times["oldest"],
            "newest_entry": times["newest"],
            "memory_file": str(self._db_path),
        }

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None


# 全局便捷函数
_temporal_memory_cache: dict[str, TemporalMemory] = {}


def get_temporal_memory(book_id: str) -> TemporalMemory:
    """获取或创建时序记忆实例（单例缓存）"""
    if book_id not in _temporal_memory_cache:
        _temporal_memory_cache[book_id] = TemporalMemory(book_id)
    return _temporal_memory_cache[book_id]
