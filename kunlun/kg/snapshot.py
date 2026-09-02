"""
昆仑创作引擎 — KG 快照管理

每次章节开始前拍摄 KG 快照，记录:
- 当前所有角色、物品、地点、技能、事件、组织
- 伏笔状态 (已种/已揭示/逾期)
- 关系图 (人物关系、所属关系、冲突关系)
- 前文章节摘要索引

快照作为生成蓝图的上下文输入，确保跨章一致性。
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from kunlun.config import settings
from kunlun.kg.client import kg_client


@dataclass
class KGSnapshot:
    """KG 快照"""

    snapshot_id: str
    book_id: str
    chapter: int
    created_at: float = field(default_factory=time.time)

    # 实体清单
    characters: list[dict] = field(default_factory=list)
    items: list[dict] = field(default_factory=list)
    locations: list[dict] = field(default_factory=list)
    skills: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    organizations: list[dict] = field(default_factory=list)

    # 伏笔状态
    foreshadowing_planted: list[dict] = field(default_factory=list)
    foreshadowing_revealed: list[dict] = field(default_factory=list)
    foreshadowing_overdue: list[dict] = field(default_factory=list)

    # 关系摘要
    relationships: list[dict] = field(default_factory=list)

    # 元信息
    entity_count: int = 0
    relationship_count: int = 0

    # 爽点追踪（供 Gate G4 使用）
    last_pleasure_chapter: int = 0

    def to_context_dict(self) -> dict:
        """返回供 blueprint 生成和审计门禁使用的上下文"""
        return {
            "snapshot_id": self.snapshot_id,
            "chapter": self.chapter,
            "character_count": len(self.characters),
            "active_foreshadowing": len(self.foreshadowing_planted),
            "overdue_foreshadowing": len(self.foreshadowing_overdue),
            "last_pleasure_chapter": self.last_pleasure_chapter,
            "summary": self.to_summary(),
        }

    def to_summary(self) -> str:
        """生成简洁文本摘要，注入 LLM prompt"""
        lines = [f"## KG 快照 (第 {self.chapter} 章前)", ""]

        if self.characters:
            lines.append(f"### 角色 ({len(self.characters)})")
            for c in self.characters[:20]:
                traits = c.get("e", {}).get("traits", "")
                lines.append(
                    f"- {c.get('e', {}).get('name', '?')}: {traits}"
                    if traits
                    else f"- {c.get('e', {}).get('name', '?')}"
                )
            if len(self.characters) > 20:
                lines.append(f"  ... 还有 {len(self.characters) - 20} 个角色")

        if self.items:
            lines.append(f"\n### 物品 ({len(self.items)})")
            lines.extend(f"- {i.get('e', {}).get('name', '?')}" for i in self.items[:10])

        if self.locations:
            lines.append(f"\n### 地点 ({len(self.locations)})")
            lines.extend(f"- {loc.get('e', {}).get('name', '?')}" for loc in self.locations[:10])

        if self.foreshadowing_planted:
            lines.append(f"\n### 待揭示伏笔 ({len(self.foreshadowing_planted)})")
            for f in self.foreshadowing_planted[:10]:
                # Neo4j: RETURN f → {"f": {...}}; SQLite降级也可能返回 {"e": {...}}
                node = f.get("f", f.get("e", {}))
                lines.append(
                    f"- [{node.get('priority', '?')}] {node.get('name', '?')} "
                    f"(预计第{node.get('expectedRevealChapter', '?')}章)"
                )

        if self.foreshadowing_overdue:
            lines.append(f"\n### ⚠️ 逾期未揭示伏笔 ({len(self.foreshadowing_overdue)})")
            for f in self.foreshadowing_overdue[:10]:
                node = f.get("f", f.get("e", {}))
                lines.append(
                    f"- {node.get('name', '?')} "
                    f"(应于第{node.get('expectedRevealChapter', '?')}章揭示)"
                )

        if self.relationships:
            lines.append(f"\n### 关键关系 ({len(self.relationships)})")
            for r in self.relationships[:10]:
                r_data = r.get("r", {})
                lines.append(
                    f"- {r.get('start', '?')} → {r_data.get('type', '?')} → {r.get('end', '?')}"
                )

        return "\n".join(lines)


class SnapshotManager:
    """快照管理：创建、存储、检索"""

    # 单次查询最大实体/关系数，大型作品可调高（影响快照大小和性能）
    MAX_ENTITIES = 500
    MAX_RELATIONSHIPS = 500

    def __init__(self):
        self._storage_dir = settings.DATA_DIR / "snapshots"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, KGSnapshot] = {}

    def create_snapshot(self, book_id: str, chapter: int) -> KGSnapshot:
        """
        拍摄当前 KG 快照

        从 Neo4j（或 SQLite 图降级）提取所有实体和关系，生成不可变快照。
        如果底层存储完全不可用，生成空快照（不阻塞流程）。
        """
        snapshot_id = f"{book_id}_ch{chapter}_{uuid.uuid4().hex[:8]}"
        snapshot = KGSnapshot(
            snapshot_id=snapshot_id,
            book_id=book_id,
            chapter=chapter,
        )

        # 检测当前图存储模式
        if kg_client.neo4j_available:
            logger.info("KG Snapshot: 使用 Neo4j 图存储")
        else:
            logger.info("KG Snapshot: Neo4j 不可用，使用 SQLite 图存储提取快照")
            kg_client._init_sqlite_graph()  # 确保表已创建

        try:
            # 提取实体
            entity_types = [
                ("Character", "characters"),
                ("Item", "items"),
                ("Location", "locations"),
                ("Skill", "skills"),
                ("Event", "events"),
                ("Organization", "organizations"),
            ]
            for entity_type, attr_name in entity_types:
                try:
                    results = kg_client.query_cypher(
                        f"MATCH (e:{entity_type}) RETURN e LIMIT {self.MAX_ENTITIES}"
                    )
                    setattr(snapshot, attr_name, results)
                    snapshot.entity_count += len(results)
                except Exception as e:
                    logger.warning(f"KG Snapshot: 提取 {entity_type} 失败: {e}")

            # 提取伏笔
            try:
                snapshot.foreshadowing_planted = kg_client.query_cypher(
                    "MATCH (f:Foreshadowing) WHERE f.status = 'planted' "
                    "RETURN f ORDER BY f.priority"
                )
                snapshot.foreshadowing_revealed = kg_client.query_cypher(
                    "MATCH (f:Foreshadowing) WHERE f.status = 'revealed' "
                    "RETURN f ORDER BY f.revealedChapter DESC LIMIT 50"
                )
                snapshot.foreshadowing_overdue = kg_client.query_cypher(
                    "MATCH (f:Foreshadowing) WHERE f.status = 'planted' "
                    "AND f.expectedRevealChapter <= $chapter RETURN f",
                    {"chapter": chapter},
                )
            except Exception as e:
                logger.warning(f"KG Snapshot: 提取伏笔失败: {e}")

            # 提取关系
            try:
                snapshot.relationships = kg_client.query_cypher(
                    "MATCH (a)-[r]->(b) RETURN a.name AS start, "
                    f"type(r) AS type, b.name AS end, r LIMIT {self.MAX_RELATIONSHIPS}"
                )
                snapshot.relationship_count = len(snapshot.relationships)
            except Exception as e:
                logger.warning(f"KG Snapshot: 提取关系失败: {e}")

        except Exception as e:
            logger.warning(f"KG Snapshot: 图存储不可用，创建空快照 ({e})")

        # 从上一章快照继承 last_pleasure_chapter（供 Gate G4 使用）
        # 若上一章的值不为 0，保留；否则用当前章节号填充，确保有意义的初始值
        try:
            prev_snapshot = self.get_latest(book_id)
            if prev_snapshot and prev_snapshot.chapter < chapter:
                snapshot.last_pleasure_chapter = prev_snapshot.last_pleasure_chapter or chapter
            else:
                snapshot.last_pleasure_chapter = chapter
        except Exception:
            snapshot.last_pleasure_chapter = chapter

        # 持久化
        self._save(snapshot)

        # 缓存
        self._cache[snapshot_id] = snapshot
        self._cache[f"{book_id}_latest"] = snapshot

        # 自动清理旧版本 (同一 book_id+chapter 最多保留 3 个)
        self.cleanup_old_snapshots(book_id, chapter, max_versions=3)

        logger.info(
            f"KG Snapshot 已创建: {snapshot_id} "
            f"(实体={snapshot.entity_count}, 关系={snapshot.relationship_count}, "
            f"伏笔={len(snapshot.foreshadowing_planted)})"
        )
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> KGSnapshot | None:
        """按 ID 检索快照"""
        if snapshot_id in self._cache:
            return self._cache[snapshot_id]

        file_path = self._storage_dir / f"{snapshot_id}.json"
        if file_path.exists():
            snapshot = self._load(file_path)
            if snapshot:
                self._cache[snapshot_id] = snapshot
                return snapshot
        return None

    def get_latest(self, book_id: str) -> KGSnapshot | None:
        """获取某本书的最新快照"""
        cache_key = f"{book_id}_latest"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 扫描文件找最新
        snapshots = sorted(
            self._storage_dir.glob(f"{book_id}_ch*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if snapshots:
            snapshot = self._load(snapshots[0])
            if snapshot:
                self._cache[cache_key] = snapshot
                return snapshot
        return None

    def cleanup_old_snapshots(self, book_id: str, chapter: int, max_versions: int = 3) -> None:
        """
        清理旧快照：同一 book_id+chapter 最多保留 max_versions 个版本。

        按 mtime 从旧到新排序，删除超过上限的最旧版本。
        """
        pattern = f"{book_id}_ch{chapter}_*.json"
        snapshot_files = sorted(
            self._storage_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
        )

        if len(snapshot_files) <= max_versions:
            return

        # 删除最旧的超出部分
        to_delete = snapshot_files[: len(snapshot_files) - max_versions]
        for fp in to_delete:
            try:
                snapshot_id = fp.stem
                fp.unlink()
                # 清理缓存：删除具体快照（用 pop 安全移除，重复调用无副作用）
                self._cache.pop(snapshot_id, None)
                # 如果 latest 指针正好指向被删除的快照，也一并清理
                latest_key = f"{book_id}_latest"
                if latest_key in self._cache and self._cache[latest_key].snapshot_id == snapshot_id:
                    self._cache.pop(latest_key, None)
                logger.debug(f"快照清理: 删除旧版本 {snapshot_id}")
            except Exception as e:
                logger.warning(f"快照清理失败: {fp} — {e}")

        if to_delete:
            logger.info(
                f"快照清理: {book_id}_ch{chapter} 保留 {max_versions}/{len(snapshot_files)} 版本, "
                f"删除 {len(to_delete)} 个旧版本"
            )

    def _save(self, snapshot: KGSnapshot):
        """持久化快照到 JSON"""
        data = {
            "snapshot_id": snapshot.snapshot_id,
            "book_id": snapshot.book_id,
            "chapter": snapshot.chapter,
            "created_at": snapshot.created_at,
            "characters": snapshot.characters,
            "items": snapshot.items,
            "locations": snapshot.locations,
            "skills": snapshot.skills,
            "events": snapshot.events,
            "organizations": snapshot.organizations,
            "foreshadowing_planted": snapshot.foreshadowing_planted,
            "foreshadowing_revealed": snapshot.foreshadowing_revealed,
            "foreshadowing_overdue": snapshot.foreshadowing_overdue,
            "relationships": snapshot.relationships,
            "entity_count": snapshot.entity_count,
            "relationship_count": snapshot.relationship_count,
            "last_pleasure_chapter": snapshot.last_pleasure_chapter,
        }
        file_path = self._storage_dir / f"{snapshot.snapshot_id}.json"
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load(self, file_path: Path) -> KGSnapshot | None:
        """从 JSON 恢复快照"""
        try:
            data = json.loads(file_path.read_text())
            snapshot = KGSnapshot(
                snapshot_id=data["snapshot_id"],
                book_id=data["book_id"],
                chapter=data["chapter"],
                created_at=data["created_at"],
            )
            for attr in [
                "characters",
                "items",
                "locations",
                "skills",
                "events",
                "organizations",
                "foreshadowing_planted",
                "foreshadowing_revealed",
                "foreshadowing_overdue",
                "relationships",
            ]:
                if attr in data:
                    setattr(snapshot, attr, data[attr])
            snapshot.entity_count = data.get("entity_count", 0)
            snapshot.relationship_count = data.get("relationship_count", 0)
            snapshot.last_pleasure_chapter = data.get("last_pleasure_chapter", 0)
            return snapshot
        except Exception as e:
            logger.error(f"KG Snapshot: 加载失败 {file_path}: {e}")
            return None


# 全局单例
snapshot_manager = SnapshotManager()
