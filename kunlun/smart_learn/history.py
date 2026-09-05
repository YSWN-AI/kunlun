"""
昆仑创作引擎 — 智能学习历史管理

管理每本书的学习历史记录，支持添加、查询、统计和清空。
存储: data/books/book_<id>/learning_history.json
"""

from __future__ import annotations

import json
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from loguru import logger


def _book_dir(book_id: str) -> Path:
    """获取书籍数据目录"""
    from kunlun.config import settings

    return Path(settings.PROJECT_ROOT) / "data" / "books" / f"book_{book_id}"


def _history_path(book_id: str) -> Path:
    return _book_dir(book_id) / "learning_history.json"


def _read_json(path: Path, default: Any) -> Any:
    """安全读取 JSON 文件"""
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"[LearningHistory] 读取 {path} 失败: {e}")
        return default


def _write_json(path: Path, data: Any) -> bool:
    """安全写入 JSON 文件"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except OSError as e:
        logger.error(f"[LearningHistory] 写入 {path} 失败: {e}")
        return False


class LearningHistory:
    """学习历史管理器

    用法:
        history = LearningHistory()
        history.add_record("book_001", {"type": "rule", "category": "dialogue", ...})
        stats = history.get_stats("book_001")
    """

    def __init__(self) -> None:
        self._cache: dict[str, list[dict]] = {}

    def add_record(self, book_id: str, record: dict) -> bool:
        """添加学习记录

        Args:
            book_id: 书籍 ID
            record: 学习记录字典（通常来自 PreferenceExtractor）

        Returns:
            是否成功
        """
        if not record:
            return False

        # 补全元数据
        record.setdefault("id", str(uuid.uuid4())[:12])
        record.setdefault("timestamp", time.time())
        record.setdefault("book_id", book_id)

        records = self._load(book_id)
        records.append(record)

        # 限制历史记录数量（最多 2000 条）
        if len(records) > 2000:
            records = records[-2000:]

        self._cache[book_id] = records
        return _write_json(_history_path(book_id), records)

    def list_records(
        self,
        book_id: str,
        limit: int = 50,
        category: str | None = None,
    ) -> list[dict]:
        """列出学习记录

        Args:
            book_id: 书籍 ID
            limit: 返回数量上限
            category: 分类筛选 (dialogue/style/pace/character/plot/structure)

        Returns:
            学习记录列表（按时间倒序）
        """
        records = self._load(book_id)

        if category:
            records = [r for r in records if r.get("category") == category]

        # 按时间倒序
        records.sort(key=lambda r: r.get("timestamp", 0), reverse=True)
        return records[:limit]

    def get_stats(self, book_id: str) -> dict[str, Any]:
        """获取学习统计

        Returns:
            统计字典，包含总记录数、各分类数量、类型分布、趋势
        """
        records = self._load(book_id)
        total = len(records)

        if total == 0:
            return {
                "book_id": book_id,
                "total_records": 0,
                "categories": {},
                "types": {},
                "actions": {},
                "avg_confidence": 0.0,
                "recent_7_days": 0,
                "trend": "no_data",
            }

        # 分类统计
        category_counter = Counter(r.get("category", "unknown") for r in records)
        type_counter = Counter(r.get("type", "unknown") for r in records)
        action_counter = Counter(r.get("action", "unknown") for r in records)

        # 平均置信度
        confidences = [r.get("confidence", 0.0) for r in records if r.get("confidence")]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # 近 7 天记录数
        now = time.time()
        seven_days_ago = now - 7 * 86400
        recent_7 = sum(1 for r in records if r.get("timestamp", 0) > seven_days_ago)

        # 趋势判断（近 7 天 vs 前 7 天）
        fourteen_days_ago = now - 14 * 86400
        prev_7 = sum(
            1 for r in records if fourteen_days_ago < r.get("timestamp", 0) <= seven_days_ago
        )
        if prev_7 == 0:
            trend = "new" if recent_7 > 0 else "stable"
        elif recent_7 > prev_7 * 1.2:
            trend = "increasing"
        elif recent_7 < prev_7 * 0.8:
            trend = "decreasing"
        else:
            trend = "stable"

        # Top 偏好内容（按出现频率）
        content_counter = Counter(r.get("content", "") for r in records if r.get("content"))
        top_preferences = [
            {"content": content, "count": count}
            for content, count in content_counter.most_common(10)
        ]

        return {
            "book_id": book_id,
            "total_records": total,
            "categories": dict(category_counter),
            "types": dict(type_counter),
            "actions": dict(action_counter),
            "avg_confidence": round(avg_confidence, 3),
            "recent_7_days": recent_7,
            "previous_7_days": prev_7,
            "trend": trend,
            "top_preferences": top_preferences,
            "last_updated": records[-1].get("timestamp", 0) if records else 0,
        }

    def clear_history(self, book_id: str) -> bool:
        """清空学习历史

        Args:
            book_id: 书籍 ID

        Returns:
            是否成功
        """
        self._cache.pop(book_id, None)
        path = _history_path(book_id)
        if path.exists():
            try:
                path.unlink()
            except OSError as e:
                logger.error(f"[LearningHistory] 删除 {path} 失败: {e}")
                return False
        return True

    def export_constraints(self, book_id: str, min_confidence: float = 0.6) -> str:
        """导出学习历史为 KUNLUN.md 约束格式

        Args:
            book_id: 书籍 ID
            min_confidence: 最小置信度过滤

        Returns:
            KUNLUN.md 格式文本
        """
        from kunlun.smart_learn.extractor import get_preference_extractor

        records = self._load(book_id)
        filtered = [r for r in records if r.get("confidence", 0) >= min_confidence]
        extractor = get_preference_extractor()
        return extractor.generate_kunlun_constraints(filtered)

    # ─── 内部工具 ──────────────────────────────────

    def _load(self, book_id: str) -> list[dict]:
        """加载学习历史（带缓存）"""
        if book_id in self._cache:
            return self._cache[book_id]

        data = _read_json(_history_path(book_id), [])
        records = data if isinstance(data, list) else []
        self._cache[book_id] = records
        return records


# ─── 全局单例 ─────────────────────────────────────────────

_history: LearningHistory | None = None


def get_learning_history() -> LearningHistory:
    """获取全局学习历史管理器实例"""
    global _history  # noqa: PLW0603
    if _history is None:
        _history = LearningHistory()
    return _history
