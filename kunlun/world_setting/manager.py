"""
昆仑创作引擎 — 世界观设定管理器

核心功能:
  - 30 类结构化设定条目的 CRUD
  - 按卷渐进开放（visible_from_volume）
  - 对 AI 隐藏防剧透（hidden_from_ai）
  - 版本历史追溯（每次更新自动记录）
  - RAG 检索时的可见性过滤
  - 关键词搜索

数据存储:
  data/books/book_<id>/world_settings.json

数据模型:
  SettingEntry: {id, category, name, fields, created_at, updated_at,
                 version, visible_from_volume, hidden_from_ai, tags, history}
  SettingVersion: {version, timestamp, fields, change_note}
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from loguru import logger

from kunlun.world_setting.schema import get_all_categories, get_category


# ─── 数据模型（TypedDict 风格，实际用 dict 存储便于 JSON 序列化） ───────────
def _make_entry(
    entry_id: str,
    category: str,
    name: str,
    fields: dict[str, Any],
    visible_from_volume: int = 0,
    hidden_from_ai: bool = False,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """构造一个新的设定条目。"""
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    return {
        "id": entry_id,
        "category": category,
        "name": name,
        "fields": fields,
        "created_at": now,
        "updated_at": now,
        "version": 1,
        "visible_from_volume": visible_from_volume,
        "hidden_from_ai": hidden_from_ai,
        "tags": tags or [],
        "history": [
            {
                "version": 1,
                "timestamp": now,
                "fields": dict(fields),
                "change_note": "初始创建",
            }
        ],
    }


def _make_version(version: int, fields: dict[str, Any], change_note: str) -> dict[str, Any]:
    """构造一个版本记录。"""
    return {
        "version": version,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "fields": dict(fields),
        "change_note": change_note,
    }


class WorldSettingManager:
    """世界观设定管理器 — 结构化设定的 CRUD、版本追溯与可见性过滤。

    用法:
        manager = WorldSettingManager("book_001")
        entry = manager.create_entry("power_system", "炼气期", {...})
        visible = manager.get_visible_settings(current_volume=3)
    """

    def __init__(self, book_id: str, data_dir: str = "data"):
        """初始化管理器。

        Args:
            book_id: 书籍 ID（用于定位数据目录）
            data_dir: 数据根目录，默认 "data"
        """
        self.book_id = book_id
        self.data_dir = data_dir
        self._book_dir = Path(data_dir) / "books" / f"book_{book_id}"
        self._file_path = self._book_dir / "world_settings.json"
        self._entries: list[dict[str, Any]] = []
        self._load()

    # ─── 持久化 ────────────────────────────────────────────────────────────
    def _load(self) -> None:
        """从 JSON 文件加载设定数据，文件不存在则初始化为空。"""
        if not self._file_path.exists():
            self._entries = []
            return
        try:
            with self._file_path.open(encoding="utf-8") as f:
                data = json.load(f)
            self._entries = data.get("entries", [])
        except Exception as e:
            logger.error(f"[world_setting] 加载失败 book={self.book_id}: {e}")
            self._entries = []

    def _save(self) -> bool:
        """将设定数据保存到 JSON 文件。

        Returns:
            保存成功返回 True，失败返回 False
        """
        try:
            self._book_dir.mkdir(parents=True, exist_ok=True)
            data = {"entries": self._entries, "book_id": self.book_id}
            with self._file_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"[world_setting] 保存失败 book={self.book_id}: {e}")
            return False

    # ─── 类别 Schema ────────────────────────────────────────────────────────
    def get_categories(self) -> list[dict[str, Any]]:
        """返回所有类别 Schema。

        Returns:
            30 类世界观设定的结构化字段定义列表
        """
        return get_all_categories()

    # ─── 条目 CRUD ──────────────────────────────────────────────────────────
    def list_entries(self, category: str | None = None) -> list[dict[str, Any]]:
        """列出设定条目，可按类别过滤。

        Args:
            category: 类别 ID，传 None 返回全部

        Returns:
            设定条目列表（不含 history 字段以减小体积）
        """
        result = []
        for entry in self._entries:
            if category is not None and entry.get("category") != category:
                continue
            # 返回时剥离 history 以减小体积
            summary = {k: v for k, v in entry.items() if k != "history"}
            result.append(summary)
        return result

    def get_entry(self, entry_id: str) -> dict[str, Any] | None:
        """根据 ID 获取单个设定条目（含完整 history）。

        Args:
            entry_id: 条目 ID

        Returns:
            设定条目字典，不存在返回 None
        """
        for entry in self._entries:
            if entry.get("id") == entry_id:
                return dict(entry)
        return None

    def create_entry(
        self,
        category: str,
        name: str,
        fields: dict[str, Any],
        visible_from_volume: int = 0,
        hidden_from_ai: bool = False,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """创建新的设定条目。

        Args:
            category: 类别 ID（必须在 schema 中存在）
            name: 条目名称
            fields: 结构化字段值字典
            visible_from_volume: 从第几卷开始可见，0=始终可见
            hidden_from_ai: 是否对 AI 隐藏（防剧透）
            tags: 标签列表

        Returns:
            新创建的设定条目

        Raises:
            ValueError: 类别不存在时
        """
        if get_category(category) is None:
            raise ValueError(f"未知类别: {category}")

        entry_id = f"ws_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        entry = _make_entry(
            entry_id=entry_id,
            category=category,
            name=name,
            fields=fields,
            visible_from_volume=visible_from_volume,
            hidden_from_ai=hidden_from_ai,
            tags=tags,
        )
        self._entries.append(entry)
        self._save()
        logger.info(
            f"[world_setting] 创建条目 book={self.book_id} "
            f"id={entry_id} category={category} name={name}"
        )
        return dict(entry)

    def update_entry(
        self,
        entry_id: str,
        fields: dict[str, Any],
        change_note: str = "",
    ) -> dict[str, Any] | None:
        """更新设定条目，自动记录版本历史。

        Args:
            entry_id: 条目 ID
            fields: 新的字段值（全量替换 fields）
            change_note: 变更说明

        Returns:
            更新后的条目，不存在返回 None
        """
        for entry in self._entries:
            if entry.get("id") == entry_id:
                new_version = entry.get("version", 1) + 1
                entry["version"] = new_version
                entry["fields"] = dict(fields)
                entry["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

                version_record = _make_version(
                    version=new_version,
                    fields=fields,
                    change_note=change_note or f"更新至 v{new_version}",
                )
                entry.setdefault("history", []).append(version_record)

                self._save()
                logger.info(
                    f"[world_setting] 更新条目 book={self.book_id} id={entry_id} → v{new_version}"
                )
                return dict(entry)
        return None

    def delete_entry(self, entry_id: str) -> bool:
        """删除设定条目。

        Args:
            entry_id: 条目 ID

        Returns:
            删除成功返回 True，条目不存在返回 False
        """
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.get("id") != entry_id]
        if len(self._entries) == before:
            return False
        self._save()
        logger.info(f"[world_setting] 删除条目 book={self.book_id} id={entry_id}")
        return True

    # ─── 版本历史 ───────────────────────────────────────────────────────────
    def get_entry_history(self, entry_id: str) -> list[dict[str, Any]]:
        """获取条目的版本历史。

        Args:
            entry_id: 条目 ID

        Returns:
            版本记录列表（按版本号升序），条目不存在返回空列表
        """
        for entry in self._entries:
            if entry.get("id") == entry_id:
                history = entry.get("history", [])
                return sorted(history, key=lambda v: v.get("version", 0))
        return []

    # ─── 可见性过滤（RAG 核心） ─────────────────────────────────────────────
    def get_visible_settings(
        self,
        current_volume: int,
        include_hidden: bool = False,
    ) -> list[dict[str, Any]]:
        """获取对当前卷可见的设定（RAG 检索核心过滤方法）。

        过滤逻辑:
          visible_from_volume <= current_volume
          AND (not hidden_from_ai OR include_hidden)

        Args:
            current_volume: 当前卷号
            include_hidden: 是否包含对 AI 隐藏的设定（仅人工查看时用 True）

        Returns:
            可见的设定条目列表（不含 history）
        """
        result = []
        for entry in self._entries:
            visible_from = entry.get("visible_from_volume", 0)
            hidden = entry.get("hidden_from_ai", False)

            # 按卷渐进开放
            if visible_from > current_volume:
                continue
            # 对 AI 隐藏防剧透
            if hidden and not include_hidden:
                continue

            summary = {k: v for k, v in entry.items() if k != "history"}
            result.append(summary)
        return result

    # ─── 搜索 ───────────────────────────────────────────────────────────────
    def search_entries(
        self,
        query: str,
        current_volume: int = 999,
    ) -> list[dict[str, Any]]:
        """简单关键词搜索 + 可见性过滤。

        在条目名称、字段值、标签中进行不区分大小写的子串匹配，
        然后应用可见性过滤。

        Args:
            query: 搜索关键词
            current_volume: 当前卷号（用于可见性过滤，默认 999 表示全部可见）

        Returns:
            匹配且可见的设定条目列表
        """
        if not query:
            return self.get_visible_settings(current_volume)

        query_lower = query.lower()
        matched = []
        for entry in self._entries:
            # 名称匹配
            if query_lower in entry.get("name", "").lower():
                matched.append(entry)
                continue
            # 标签匹配
            if any(query_lower in tag.lower() for tag in entry.get("tags", [])):
                matched.append(entry)
                continue
            # 字段值匹配
            fields = entry.get("fields", {})
            for value in fields.values():
                if isinstance(value, str) and query_lower in value.lower():
                    matched.append(entry)
                    break
                if isinstance(value, list) and any(query_lower in str(v).lower() for v in value):
                    matched.append(entry)
                    break

        # 应用可见性过滤
        visible_ids = {
            e["id"] for e in self.get_visible_settings(current_volume, include_hidden=True)
        }
        result = []
        for entry in matched:
            if entry.get("id") in visible_ids:
                summary = {k: v for k, v in entry.items() if k != "history"}
                result.append(summary)
        return result

    # ─── 统计 ───────────────────────────────────────────────────────────────
    def get_stats(self) -> dict[str, Any]:
        """返回设定统计信息。"""
        category_counts: dict[str, int] = {}
        hidden_count = 0
        volume_gated = 0
        for entry in self._entries:
            cat = entry.get("category", "unknown")
            category_counts[cat] = category_counts.get(cat, 0) + 1
            if entry.get("hidden_from_ai", False):
                hidden_count += 1
            if entry.get("visible_from_volume", 0) > 0:
                volume_gated += 1
        return {
            "total": len(self._entries),
            "by_category": category_counts,
            "hidden_from_ai": hidden_count,
            "volume_gated": volume_gated,
        }
