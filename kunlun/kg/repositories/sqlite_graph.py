"""
昆仑创作引擎 — SQLite 图数据库降级仓储实现

当 Neo4j 不可用时，使用 SQLite 模拟图数据库操作。
支持基本的节点/关系 CRUD 和简化的 Cypher 翻译。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from loguru import logger

from kunlun.config import settings
from kunlun.kg.repositories.base import GraphRepository


class SQLiteGraphRepository(GraphRepository):
    """SQLite 图数据库降级仓储

    使用 SQLite 存储节点和关系表，实现基本的图查询能力。
    """

    def __init__(self):
        db_path = getattr(
            settings,
            "sqlite_graph_path",
            str(settings.DATA_DIR / "kunlun_graph.db"),
        )
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._ensure_schema()

    @property
    def backend_name(self) -> str:
        return "sqlite_graph"

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _ensure_schema(self) -> None:
        """创建节点和关系表"""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT UNIQUE NOT NULL,
                labels TEXT NOT NULL DEFAULT '[]',  -- JSON array
                properties TEXT NOT NULL DEFAULT '{}',  -- JSON object
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_entity ON nodes(entity_id);
            CREATE INDEX IF NOT EXISTS idx_nodes_labels ON nodes(labels);

            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                properties TEXT NOT NULL DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (source_id) REFERENCES nodes(entity_id),
                FOREIGN KEY (target_id) REFERENCES nodes(entity_id)
            );
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(relation_type);
        """)
        conn.commit()

    def health_check_sync(self) -> bool:
        try:
            conn = self._get_conn()
            conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    async def query(self, cypher: str, params: dict | None = None) -> list[dict]:
        """简化 Cypher 翻译器 — 支持常见的 MATCH/RETURN/MERGE/CREATE 语句

        注意：这是一个最小化实现，不支持复杂 Cypher。
        对于复杂查询，请使用 Neo4j。
        """
        params = params or {}

        # 预处理：替换参数占位符
        cypher_upper = cypher.strip().upper()
        conn = self._get_conn()

        try:
            if cypher_upper.startswith("MATCH"):
                return self._translate_match(conn, cypher, params)
            if cypher_upper.startswith("CREATE"):
                return self._translate_create(conn, cypher, params)
            if cypher_upper.startswith("MERGE"):
                return self._translate_merge(conn, cypher, params)
            if cypher_upper.startswith("DELETE"):
                return self._translate_delete(conn, cypher, params)
            if cypher_upper.startswith("SET"):
                return self._translate_set(conn, cypher, params)
            if cypher_upper.startswith("RETURN"):
                return [{"result": 1}]
            logger.warning(f"SQLiteGraph: 不支持的 Cypher 语句: {cypher[:80]}")
            return []
        except Exception as e:
            logger.warning(f"SQLiteGraph Cypher 翻译失败: {e}")
            return []

    def _translate_match(self, conn: sqlite3.Connection, cypher: str, params: dict) -> list[dict]:
        """简化的 MATCH 翻译"""
        # 基本模式: MATCH (n:Label {key: value}) RETURN n
        # 提取标签
        import re

        # 提取节点变量和标签
        label_match = re.search(r"\((\w+):(\w+)\s*\{?([^}]*)\}?\)", cypher)
        if not label_match:
            # 尝试不带标签的 MATCH
            label_match = re.search(r"\((\w+)\)", cypher)
            if label_match:
                var = label_match.group(1)
                rows = conn.execute("SELECT entity_id, labels, properties FROM nodes").fetchall()
                return [_row_to_dict(r, var) for r in rows]
            return []

        var = label_match.group(1)
        label = label_match.group(2)
        props_str = label_match.group(3)

        # 构建 WHERE 条件 (使用参数化查询防止SQL注入)
        where_clauses = ["labels LIKE '%\"' || ? || '\"%'"]
        query_params = [label]
        if props_str:
            for p in props_str.split(","):
                p = p.strip()  # noqa: PLW2901
                if ":" in p:
                    k, v = p.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    # 检查是否是参数引用
                    if v.startswith("$"):
                        param_key = v[1:]
                        if param_key in params:
                            v = str(params[param_key])
                    where_clauses.append("json_extract(properties, ?) = ?")
                    query_params.append(f"$.{k}")
                    query_params.append(v)

        where = " AND ".join(where_clauses)
        rows = conn.execute(
            f"SELECT entity_id, labels, properties FROM nodes WHERE {where}",
            query_params,
        ).fetchall()

        return [_row_to_dict(r, var) for r in rows]

    def _translate_create(self, conn: sqlite3.Connection, cypher: str, params: dict) -> list[dict]:
        """简化的 CREATE 翻译"""
        import json as json_mod
        import re

        # MATCH (n:Label {props})
        node_match = re.search(r"\((\w*):(\w+)\s*\{([^}]+)\}\)", cypher)
        if not node_match:
            return []

        _var = node_match.group(1) or ""
        label = node_match.group(2)
        props = node_match.group(3)

        # 解析属性
        props_dict = {}
        for p in props.split(","):
            p = p.strip()  # noqa: PLW2901
            if ":" in p:
                k, v = p.split(":", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if v.startswith("$"):
                    param_key = v[1:]
                    if param_key in params:
                        v = params[param_key]
                props_dict[k] = str(v)

        entity_id = props_dict.get("entity_id", props_dict.get("name", "unknown"))
        labels_list = [label]

        conn.execute(
            """INSERT OR IGNORE INTO nodes(entity_id, labels, properties)
               VALUES (?, ?, ?)""",
            (
                entity_id,
                json_mod.dumps(labels_list),
                json_mod.dumps(props_dict, ensure_ascii=False),
            ),
        )
        conn.commit()

        return [{"entity_id": entity_id, "labels": labels_list, "properties": props_dict}]

    def _translate_merge(self, conn: sqlite3.Connection, cypher: str, params: dict) -> list[dict]:
        """MERGE = 先查找再创建"""
        # 先用 MATCH 查找
        result = self._translate_match(conn, cypher, params)
        if result:
            return result
        # 找不到则 CREATE
        return self._translate_create(conn, cypher, params)

    def _translate_delete(self, conn: sqlite3.Connection, cypher: str, params: dict) -> list[dict]:
        """简化的 DELETE 翻译 — 只删除匹配条件的节点/边"""
        import re as _re

        cypher_upper = cypher.strip().upper()

        # 如果包含 MATCH 子句，先匹配再删除
        match_result = _re.search(r"MATCH\s+(.*?)\s+DELETE", cypher, _re.IGNORECASE | _re.DOTALL)
        if match_result:
            match_clause = "MATCH " + match_result.group(1)
            matched = self._translate_match(conn, match_clause, params)
            entity_ids: list[str] = []
            for item in matched:
                entity_ids.extend(
                    var_data["entity_id"]
                    for var_data in item.values()
                    if isinstance(var_data, dict) and "entity_id" in var_data
                )
            if entity_ids:
                placeholders = ",".join(["?"] * len(entity_ids))
                conn.execute(
                    f"DELETE FROM nodes WHERE entity_id IN ({placeholders})",
                    entity_ids,
                )
                conn.execute(
                    f"DELETE FROM edges WHERE source_id IN ({placeholders}) "
                    f"OR target_id IN ({placeholders})",
                    entity_ids * 2,
                )
            conn.commit()
            return []

        # 检测节点模式 (n:Label)
        node_match = _re.search(r"\((\w*):?(\w*)\)", cypher)
        if node_match:
            label = node_match.group(2)
            if label:
                matched = self._translate_match(conn, f"MATCH (n:{label}) RETURN n", params)
                entity_ids = []
                for item in matched:
                    for var_data in item.values():
                        if isinstance(var_data, dict) and "entity_id" in var_data:
                            entity_ids.append(var_data["entity_id"])
                if entity_ids:
                    placeholders = ",".join(["?"] * len(entity_ids))
                    conn.execute(
                        f"DELETE FROM nodes WHERE entity_id IN ({placeholders})",
                        entity_ids,
                    )
                    conn.execute(
                        f"DELETE FROM edges WHERE source_id IN ({placeholders}) "
                        f"OR target_id IN ({placeholders})",
                        entity_ids * 2,
                    )
            else:
                conn.execute("DELETE FROM nodes WHERE 1=1")
            conn.commit()
            return []

        # 检测边模式
        if "EDGE" in cypher_upper or "-[" in cypher or "]->" in cypher or "<-[" in cypher:
            conn.execute("DELETE FROM edges WHERE 1=1")
            conn.commit()
            return []

        # 保守策略：仅清理孤儿边，不删除所有数据
        conn.execute(
            """DELETE FROM edges WHERE source_id NOT IN (SELECT entity_id FROM nodes)
               OR target_id NOT IN (SELECT entity_id FROM nodes)"""
        )
        conn.commit()
        return []

    def _translate_set(self, _conn: sqlite3.Connection, _cypher: str, _params: dict) -> list[dict]:
        """简化的 SET 翻译"""
        return []

    async def query_single(self, cypher: str, params: dict | None = None) -> dict | None:
        results = await self.query(cypher, params)
        return results[0] if results else None

    async def execute(self, cypher: str, params: dict | None = None) -> None:
        await self.query(cypher, params)

    async def health_check(self) -> bool:
        return self.health_check_sync()

    async def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def close_sync(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


def _row_to_dict(row: sqlite3.Row, var: str) -> dict:
    """将 SQLite Row 转换为 KG 字典格式"""
    return {
        var: {
            "entity_id": row["entity_id"],
            "labels": json.loads(row["labels"]) if row["labels"] else [],
            "properties": json.loads(row["properties"]) if row["properties"] else {},
        }
    }
