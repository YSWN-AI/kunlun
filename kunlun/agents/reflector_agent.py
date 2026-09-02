"""
昆仑创作引擎 — Reflector Agent（反射器）

借鉴 InkOS 的 Observer+Reflector 分离模式：
  - Observer: 从AI生成文本中提取结构化事实（ObserverReport）
  - Reflector: 将Observer提取的事实不可变地写入快照/知识图谱

设计原则:
  1. 不可变写入 — 每次写入生成新的快照版本，保留历史
  2. 零LLM成本 — 纯数据库操作
  3. 增量更新 — 只写入变更的部分，不重写整个KG
  4. 幂等性 — 同一份ObserverReport重复写入不会产生副作用

数据流:
  ObserverReport(JSON delta) → Reflector.write(report) → Neo4j/SQLite图存储 + Qdrant向量索引
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from kunlun.agents.observer import (
    CharacterStateChange,
    EventExtracted,
    ForeshadowingDelta,
    ObserverReport,
)
from kunlun.common.json_store import save_json
from kunlun.config import settings
from kunlun.kg.client import kg_client


@dataclass
class SnapshotVersion:
    """快照版本记录"""

    version_id: str
    book_id: str
    chapter: int
    timestamp: float = field(default_factory=time.time)
    delta: dict = field(default_factory=dict)
    parent_version_id: str = ""


@dataclass
class ReflectorResult:
    """Reflector写入结果"""

    success: bool
    snapshot_version_id: str = ""
    characters_updated: int = 0
    events_recorded: int = 0
    foreshadowing_updated: int = 0
    entities_indexed: int = 0
    errors: list[str] = field(default_factory=list)


class Reflector:
    """
    Reflector Agent — 将Observer提取的事实写入存储

    用法:
        reflector = Reflector()
        result = reflector.write(observer_report, book_id="book_001")
    """

    # 快照版本存储目录
    SNAPSHOT_VERSIONS_DIR = "snapshot_versions"

    def __init__(self):
        self._version_counter: dict[str, int] = {}

    @property
    def _snapshot_dir(self) -> Path:
        p = settings.DATA_DIR / self.SNAPSHOT_VERSIONS_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    def write(self, report: ObserverReport, book_id: str = "") -> ReflectorResult:
        """
        将Observer报告写入存储（不可变增量更新）

        Args:
            report: Observer生成的JSON delta报告
            book_id: 作品ID

        Returns:
            ReflectorResult: 写入结果
        """
        if not report:
            return ReflectorResult(success=True, snapshot_version_id="empty")

        bid = book_id or report.book_id
        if not bid:
            return ReflectorResult(success=False, errors=["book_id is required"])

        errors = []
        chars_updated = 0
        events_recorded = 0
        fp_updated = 0
        entities_indexed = 0

        try:
            # 1. 写入角色状态变更到KG
            chars_updated = self._write_character_changes(
                bid, report.character_changes, report.chapter
            )
        except Exception as e:
            errors.append(f"角色状态写入失败: {e}")
            logger.warning(f"[Reflector] 角色状态写入失败: {e}")

        try:
            # 2. 写入事件到KG
            events_recorded = self._write_events(bid, report.events)
        except Exception as e:
            errors.append(f"事件写入失败: {e}")
            logger.warning(f"[Reflector] 事件写入失败: {e}")

        try:
            # 3. 写入伏笔变更到KG
            fp_updated = self._write_foreshadowing(bid, report.foreshadowing, report.chapter)
        except Exception as e:
            errors.append(f"伏笔写入失败: {e}")
            logger.warning(f"[Reflector] 伏笔写入失败: {e}")

        try:
            # 4. 索引新实体到Qdrant
            entities_indexed = self._index_new_entities(bid, report.new_entities)
        except Exception as e:
            errors.append(f"实体索引失败: {e}")
            logger.warning(f"[Reflector] 实体索引失败: {e}")

        # 5. 保存快照版本
        version_id = self._save_snapshot_version(bid, report)

        result = ReflectorResult(
            success=len(errors) == 0,
            snapshot_version_id=version_id,
            characters_updated=chars_updated,
            events_recorded=events_recorded,
            foreshadowing_updated=fp_updated,
            entities_indexed=entities_indexed,
            errors=errors,
        )

        logger.info(
            f"[Reflector] ch{report.chapter}: {chars_updated}角色/{events_recorded}事件/"
            f"{fp_updated}伏笔/{entities_indexed}实体 → 版本 {version_id}"
        )

        return result

    def _write_character_changes(
        self, book_id: str, changes: list[CharacterStateChange], chapter: int
    ) -> int:
        """将角色状态变更写入KG"""
        if not changes:
            return 0

        count = 0
        for change in changes:
            uid = change.character_uid or f"{book_id}_{change.character_name}"
            props: dict[str, Any] = {"last_updated_chapter": chapter}

            if change.emotion_change:
                props["current_emotion"] = change.emotion_change
            if change.status_change:
                props["status"] = change.status_change
            if change.location_change:
                props["current_location"] = change.location_change
            if change.relationship_change:
                props["last_relationship_change"] = change.relationship_change

            if len(props) > 1:  # 除了 last_updated_chapter 外有其他变更
                try:
                    kg_client.create_entity(
                        uid=uid,
                        entity_type="Character",
                        name=change.character_name,
                        properties=props,
                    )
                    count += 1
                except Exception as e:
                    logger.debug(f"[Reflector] 角色写入失败 {change.character_name}: {e}")

        return count

    def _write_events(self, book_id: str, events: list[EventExtracted]) -> int:
        """将事件写入KG"""
        if not events:
            return 0

        count = 0
        for event in events:
            uid = f"{book_id}_{event.event_name}"
            try:
                kg_client.create_entity(
                    uid=uid,
                    entity_type="Event",
                    name=event.event_name,
                    properties={
                        "type": event.event_type,
                        "description": event.description,
                        "chapter": event.chapter,
                        "characters": json.dumps(event.involved_characters, ensure_ascii=False),
                        "location": event.location,
                    },
                )
                count += 1
            except Exception as e:
                logger.debug(f"[Reflector] 事件写入失败 {event.event_name}: {e}")

        return count

    def _write_foreshadowing(self, book_id: str, delta: ForeshadowingDelta, chapter: int) -> int:
        """将伏笔变更写入KG"""

        count = 0
        # 写入新埋的伏笔
        for plant in delta.planted:
            uid = f"{book_id}_fp_{plant}"
            try:
                kg_client.create_entity(
                    uid=uid,
                    entity_type="Foreshadowing",
                    name=plant,
                    properties={
                        "status": "planted",
                        "planted_chapter": chapter,
                        "book_id": book_id,
                    },
                )
                count += 1
            except Exception as e:
                logger.debug(f"[Reflector] 伏笔种植KG失败（非阻塞）: {e}")

        # 更新已揭示的伏笔
        for reveal in delta.revealed:
            try:
                kg_client.query_cypher(
                    "MATCH (f:Foreshadowing {name: $name, book_id: $book_id}) "
                    "SET f.status = 'revealed', f.revealed_chapter = $chapter",
                    {"name": reveal, "book_id": book_id, "chapter": chapter},
                )
                count += 1
            except Exception as e:
                logger.debug(f"[Reflector] 伏笔揭示KG失败（非阻塞）: {e}")

        return count

    def _index_new_entities(self, book_id: str, new_entities: dict[str, list[str]]) -> int:
        """将新实体批量索引到KG和Qdrant向量库"""
        if not new_entities:
            return 0

        # 收集所有待索引实体
        batch = []
        for entity_type, names in new_entities.items():
            for name in names:
                uid = f"{book_id}_{entity_type}_{name}"
                etype_cap = entity_type.capitalize()
                props = {"book_id": book_id, "type": entity_type}
                batch.append((uid, etype_cap, name, props))

        if not batch:
            return 0

        # 批量写入KG节点 (executemany 减少 commit 次数)
        try:
            conn = kg_client._get_graph_conn()
            with kg_client._graph_lock:
                conn.executemany(
                    "INSERT OR REPLACE INTO nodes(id, type, name, properties) VALUES (?, ?, ?, ?)",
                    [
                        (uid, etype, name, json.dumps(props, ensure_ascii=False))
                        for uid, etype, name, props in batch
                    ],
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"[Reflector] 批量KG写入失败: {e}")

        # 批量向量索引
        count = 0
        for uid, _etype, name, props in batch:
            try:
                kg_client.index_entity_vector(
                    uid=uid,
                    text=f"{props['type']}: {name}",
                    payload={"uid": uid, "type": props["type"], "name": name, "book_id": book_id},
                )
                count += 1
            except Exception as e:
                logger.debug(f"[Reflector] 实体向量索引失败 {name}: {e}")

        return count

    def _save_snapshot_version(self, book_id: str, report: ObserverReport) -> str:
        """保存快照版本到文件"""
        if book_id not in self._version_counter:
            self._version_counter[book_id] = 0
        self._version_counter[book_id] += 1

        version_id = f"{book_id}_ch{report.chapter}_v{self._version_counter[book_id]}"
        snapshot = SnapshotVersion(
            version_id=version_id,
            book_id=book_id,
            chapter=report.chapter,
            delta={
                "character_changes": [c.__dict__ for c in report.character_changes],
                "events": [e.__dict__ for e in report.events],
                "foreshadowing": report.foreshadowing.__dict__,
                "new_entities": report.new_entities,
                "key_plot_points": report.key_plot_points,
                "word_count": report.word_count,
                "dialogue_ratio": report.dialogue_ratio,
                "scene_count": report.scene_count,
            },
        )

        # 写入文件
        save_json(
            self._snapshot_dir / f"{version_id}.json",
            snapshot.__dict__,
            pretty=True,
        )

        return version_id

    def get_latest_snapshot(self, book_id: str) -> dict | None:
        """获取最新快照版本"""
        snapshots = sorted(
            self._snapshot_dir.glob(f"{book_id}_ch*_v*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not snapshots:
            return None

        try:
            return json.loads(snapshots[0].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"[Reflector] 快照读取失败: {e}")
            return None

    def get_chapter_snapshot(self, book_id: str, chapter: int) -> dict | None:
        """获取指定章节的快照"""
        snapshots = sorted(
            self._snapshot_dir.glob(f"{book_id}_ch{chapter}_v*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not snapshots:
            return None

        try:
            return json.loads(snapshots[0].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"[Reflector] 章节快照读取失败: {e}")
            return None


# 全局单例
reflector = Reflector()
