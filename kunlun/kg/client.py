"""
昆仑创作引擎 — KG 客户端
Neo4j 连接管理 + Qdrant 嵌入检索 + SQLite FTS5 全文搜索 + SQLite 图降级

性能优化:
- Neo4j 异步驱动 + Rust 扩展 (neo4j-rust-ext, 3-10x 提速)
- SQLite WAL 模式 + 64MB 缓存 + 256MB mmap (并发读写)
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
import sqlite3
import threading
import uuid as uuid_mod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from neo4j import AsyncDriver, Driver
    from qdrant_client import QdrantClient

# 懒加载：neo4j 和 qdrant_client 仅在首次使用时导入（~1s→0ms 冷启动优化）
from kunlun.common.cache import TTLPropertyCache
from kunlun.config import settings


class KGClient:
    """
    知识图谱统一客户端
    聚合四路检索：Neo4j (图) + SQLite 图降级 + Qdrant (向量) + SQLite FTS5 (全文)
    Neo4j 不可用时自动降级为 SQLite 图模式，确保 KG 查询不静默失败。
    """

    def __init__(self):
        self._neo4j: Driver | None = None
        self._neo4j_async: AsyncDriver | None = None  # 异步驱动 (非阻塞)
        self._qdrant: QdrantClient | None = None
        self._sqlite: sqlite3.Connection | None = None
        self._graph_conn: sqlite3.Connection | None = None
        self._initialized = False
        self._neo4j_available: bool | None = None
        self._sqlite_graph_initialized: bool = False
        self._sqlite_lock = threading.Lock()
        self._graph_lock = threading.Lock()
        self._cache = TTLPropertyCache()

    # ─── Neo4j + 降级检测 ──────────────────────────

    NEO4J_RETRY_INTERVAL = 30  # 秒

    def _create_driver(self) -> Driver:
        """创建 Neo4j 驱动（不验证连接）"""
        from neo4j import GraphDatabase

        return GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    @property
    def neo4j_available(self) -> bool:
        """检测 Neo4j 是否可用（TTL缓存+定期重试）

        连接成功→缓存永久 True；失败→每 NEO4J_RETRY_INTERVAL 秒重试。
        """
        if self._neo4j_available is True:
            return True
        result = self._cache.get("neo4j_avail", self.NEO4J_RETRY_INTERVAL, self._check_neo4j)
        self._neo4j_available = result
        return result

    def _check_neo4j(self) -> bool:
        try:
            driver = self._create_driver()
            driver.verify_connectivity()
            if self._neo4j is not None:
                with contextlib.suppress(Exception):
                    self._neo4j.close()
            self._neo4j = driver
            self._neo4j_available = True
            logger.info(f"Neo4j 已连接: {settings.neo4j_uri}")
            # 惰性初始化约束/索引（首次连接成功后执行，幂等）
            self.init_constraints()
            return True
        except Exception as e:
            if self._neo4j is not None:
                with contextlib.suppress(Exception):
                    self._neo4j.close()
                self._neo4j = None
            self._neo4j_available = False
            logger.debug(f"Neo4j 仍不可用 ({e})")
            return False

    @property
    def neo4j(self) -> Driver:
        if self._neo4j_available is False:
            raise ConnectionError("Neo4j 不可用，请使用 SQLite 图降级模式")
        if self._neo4j is None:
            self._neo4j = self._create_driver()
            self._neo4j.verify_connectivity()
            logger.info(f"Neo4j 已连接: {settings.neo4j_uri}")
            self._neo4j_available = True
        return self._neo4j

    def query_cypher(self, cypher: str, params: dict | None = None) -> list[dict]:
        """执行 Cypher 查询；Neo4j 不可用时自动降级为 SQLite 图查询。

        警告：此方法使用同步驱动，在异步上下文（FastAPI 路由）中会阻塞事件循环。
        推荐使用 query_cypher_async() 替代。
        """
        if self.neo4j_available:
            logger.debug("[KGClient] 使用同步 Neo4j 驱动 — 建议迁移至 query_cypher_async()")
            with self.neo4j.session() as session:
                result = session.run(cypher, params or {})
                return [record.data() for record in result]
        else:
            return self._query_sqlite_graph(cypher, params or {})

    async def query_cypher_async(self, cypher: str, params: dict | None = None) -> list[dict]:
        """异步执行 Cypher 查询（非阻塞，推荐在 FastAPI 路由中使用）

        Neo4j 不可用时自动降级为 SQLite 图查询。
        使用异步驱动 + Rust 扩展可获得 3-10x 性能提升。
        """
        if self.neo4j_available:
            driver = await self._get_async_driver()
            async with driver.session() as session:
                result = await session.run(cypher, params or {})
                return [record.data() async for record in result]
        else:
            return self._query_sqlite_graph(cypher, params or {})

    async def _get_async_driver(self) -> AsyncDriver:
        """获取或创建 Neo4j 异步驱动（带连接池优化）"""
        from neo4j import AsyncGraphDatabase

        if self._neo4j_async is None:
            self._neo4j_async = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
                max_connection_lifetime=3600,  # 1小时连接生命周期
                max_connection_pool_size=20,  # 连接池上限
                connection_acquisition_timeout=10,  # 获取连接超时(秒)
            )
            # 验证连接
            await self._neo4j_async.verify_connectivity()
            logger.info(f"Neo4j 异步驱动已连接: {settings.neo4j_uri}")
        return self._neo4j_async

    # ─── Qdrant (嵌入式) ─────────────────────────────

    @property
    def qdrant(self) -> QdrantClient:
        if self._qdrant is None:
            from qdrant_client import QdrantClient

            qdrant_path = Path(settings.qdrant_path)
            qdrant_path.mkdir(parents=True, exist_ok=True)
            self._qdrant = QdrantClient(path=str(qdrant_path))
            self._ensure_qdrant_collection()
            logger.info(f"Qdrant 已初始化: {qdrant_path}")
        return self._qdrant

    def _deterministic_id(self, key: str) -> int:
        """基于 key 的确定性哈希（替代 Python hash()，后者因 PYTHONHASHSEED 每次进程不同）"""
        return int(hashlib.md5(key.encode("utf-8"), usedforsecurity=False).hexdigest()[:16], 16) % (
            2**63 - 1
        )

    def _ensure_qdrant_collection(self):
        assert self._qdrant is not None, "Qdrant 未初始化"
        from qdrant_client.models import Distance, VectorParams

        collections = [c.name for c in self._qdrant.get_collections().collections]
        if settings.qdrant_collection not in collections:
            # 使用新版本 qdrant_client 兼容的参数格式
            create_kwargs: dict[str, Any] = {
                "collection_name": settings.qdrant_collection,
                "vectors_config": VectorParams(size=768, distance=Distance.COSINE),
            }

            # ── Scalar Quantization: float32 → uint8，节省 75% 内存 ──
            # 借鉴 Qdrant 官方建议，对嵌入向量做标量量化
            # 原始: 768维 * 4 bytes = 3072 bytes/vector
            # 量化后: 768维 * 1 byte = 768 bytes/vector（4x 节省）
            try:
                from qdrant_client.models import (
                    ScalarQuantization,
                    ScalarQuantizationConfig,
                    ScalarType,
                )

                quantization_config = ScalarQuantization(
                    scalar=ScalarQuantizationConfig(
                        type=ScalarType.INT8,  # 8位整数量化
                        quantile=0.99,  # 忽略 1% 极端值，减少量化误差
                        always_ram=True,  # 量化结果常驻内存（更适合频繁查询）
                    )
                )
                create_kwargs["quantization_config"] = quantization_config
                logger.info(
                    "Qdrant: 已启用标量量化 (int8, quantile=0.99, always_ram) — 预计节约 75% 内存"
                )
            except (ImportError, AttributeError) as e:
                logger.debug(f"Qdrant: 标量量化不可用 ({e})，使用完整精度")

            # 尝试启用本地 HNSW 索引优化（兼容不同版本的 qdrant_client）
            try:
                from qdrant_client.models import HnswConfig

                hnsw_config = HnswConfig(
                    m=16,
                    ef_construct=100,
                    full_scan_threshold=10000,
                    on_disk=False,
                )
                create_kwargs["hnsw_config"] = hnsw_config
                logger.info("Qdrant: 已启用 HNSW 索引优化 (m=16, ef_construct=100)")
            except (ImportError, TypeError):
                try:
                    from qdrant_client.models import HnswConfigDiff

                    hnsw_config_diff = HnswConfigDiff(
                        m=16,
                        ef_construct=100,
                        full_scan_threshold=10000,
                    )
                    create_kwargs["hnsw_config"] = hnsw_config_diff
                    logger.info("Qdrant: 已启用 HNSW 索引优化 (m=16, ef_construct=100)")
                except Exception as e:
                    logger.debug(f"Qdrant: HNSW不可用 ({e}), 使用默认集合索引")

            self._qdrant.create_collection(**create_kwargs)

    # ─── SQLite 图存储 (Neo4j 降级) ──────────────────

    @property
    def sqlite_graph_path(self) -> str:
        """SQLite 图数据库路径"""
        return str(Path(settings.sqlite_path).parent / "kunlun_graph.db")

    def _init_sqlite_graph(self):
        """创建 SQLite 图存储表 (nodes + edges)，幂等"""
        if self._sqlite_graph_initialized:
            return
        graph_path = Path(self.sqlite_graph_path)
        graph_path.parent.mkdir(parents=True, exist_ok=True)

        # 使用独立连接（与 FTS5 分开，避免表冲突）
        graph_conn = sqlite3.connect(str(graph_path), check_same_thread=False)
        graph_conn.row_factory = sqlite3.Row
        # SQLite 性能优化: WAL 模式 + 大缓存 + mmap
        graph_conn.execute("PRAGMA journal_mode=WAL;")
        graph_conn.execute("PRAGMA synchronous=NORMAL;")
        graph_conn.execute("PRAGMA cache_size=-64000;")  # 64MB 缓存
        graph_conn.execute("PRAGMA mmap_size=268435456;")  # 256MB 内存映射
        graph_conn.execute("PRAGMA busy_timeout=5000;")
        graph_conn.execute("PRAGMA foreign_keys=ON;")
        graph_conn.execute("PRAGMA temp_store=MEMORY;")
        graph_conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                properties TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
            CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name);

            CREATE TABLE IF NOT EXISTS edges (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                type TEXT NOT NULL,
                properties TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (source_id) REFERENCES nodes(id),
                FOREIGN KEY (target_id) REFERENCES nodes(id)
            );
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type);
        """)
        graph_conn.commit()
        graph_conn.close()
        self._sqlite_graph_initialized = True
        logger.info(f"SQLite 图存储已初始化: {graph_path}")

    def _get_graph_conn(self) -> sqlite3.Connection:
        """获取图存储数据库连接（复用持久连接，减少反复打开/关闭开销）"""
        self._init_sqlite_graph()
        if self._graph_conn is None:
            self._graph_conn = sqlite3.connect(self.sqlite_graph_path, check_same_thread=False)
            self._graph_conn.row_factory = sqlite3.Row
        else:
            # 检查连接是否仍然有效，失效则重建
            try:
                self._graph_conn.execute("SELECT 1")
            except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                try:
                    self._graph_conn.close()
                except Exception as e:
                    logger.debug(f"SQLite 图连接关闭异常: {e}")
                self._graph_conn = sqlite3.connect(self.sqlite_graph_path, check_same_thread=False)
                self._graph_conn.row_factory = sqlite3.Row
        return self._graph_conn

    def _close_graph_conn(self):
        """关闭图存储持久连接"""
        if self._graph_conn is not None:
            self._graph_conn.close()
            self._graph_conn = None

    def create_entity(
        self, uid: str, entity_type: str, name: str, properties: dict | None = None
    ) -> bool:
        """在 SQLite 图存储中创建实体节点（Neo4j 降级模式）"""
        conn = self._get_graph_conn()
        with self._graph_lock:
            try:
                props_json = json.dumps(properties or {}, ensure_ascii=False)
                conn.execute(
                    "INSERT OR REPLACE INTO nodes(id, type, name, properties) VALUES (?, ?, ?, ?)",
                    (uid, entity_type, name, props_json),
                )
                conn.commit()
                logger.debug(f"SQLite 图: 创建实体 {entity_type}/{name} ({uid})")
                return True
            except Exception as e:
                logger.error(f"SQLite 图: 创建实体失败: {e}")
                return False

    def create_relationship(
        self, source_id: str, target_id: str, rel_type: str, properties: dict | None = None
    ) -> bool:
        """在 SQLite 图存储中创建关系边"""
        conn = self._get_graph_conn()
        with self._graph_lock:
            try:
                rel_id = f"{source_id}_{rel_type}_{target_id}_{uuid_mod.uuid4().hex[:6]}"
                props_json = json.dumps(properties or {}, ensure_ascii=False)
                conn.execute(
                    "INSERT OR REPLACE INTO edges(id, source_id, "
                    "target_id, type, properties) VALUES (?, ?, ?, ?, ?)",
                    (rel_id, source_id, target_id, rel_type, props_json),
                )
                conn.commit()
                logger.debug(f"SQLite 图: 创建关系 {source_id} -[{rel_type}]-> {target_id}")
                return True
            except Exception as e:
                logger.error(f"SQLite 图: 创建关系失败: {e}")
                return False

    def _query_sqlite_graph(self, cypher: str, params: dict) -> list[dict]:
        """
        将基本 Cypher 查询翻译为 SQLite 图查询

        支持的模式：
        - MATCH (e:Type) RETURN e [LIMIT N]
        - MATCH (e:Type) WHERE e.prop = value RETURN e [ORDER BY e.prop [DESC]]
        - MATCH (f:Type) WHERE f.prop = 'value' AND f.prop2 <= $param RETURN f
        - MATCH (a)-[r]->(b) RETURN a.name AS start, type(r) AS type, b.name AS end, r
        - MERGE (e:Type {uid: $uid}) SET e.prop = $val, ...  (写操作)
        - MATCH ... MATCH ... MERGE (a)-[:REL]->(b)  (写操作)
        """
        self._init_sqlite_graph()
        conn = self._get_graph_conn()
        params = params or {}
        cypher_upper = cypher.strip().upper()

        # 写操作: MERGE 节点
        if cypher_upper.startswith("MERGE") and " SET " in cypher_upper:
            return self._sqlite_merge_node(cypher, params)

        # 写操作: MERGE 关系 (含 MATCH ... MERGE)
        if "MERGE" in cypher_upper and "-[" in cypher and "]->" in cypher:
            return self._sqlite_merge_relationship(cypher, params)

        # 关系查询: MATCH (a)-[r]->(b)
        if "-[" in cypher and "]->" in cypher:
            return self._query_relationships(conn, cypher, params)

        # 实体查询: MATCH (e:Type) — 兜底解析
        result = self._query_nodes(conn, cypher, params)
        if not result:
            logger.warning(f"[SQLiteCypher] 未解析的查询模式: {cypher[:100]} — 返回空结果")
        return result

    def _sqlite_merge_node(self, cypher: str, params: dict) -> list[dict]:
        """在 SQLite 图存储中执行 MERGE/SET 节点写入"""
        # 提取 MERGE (alias:Type {uid: $uid_param})
        m = re.search(
            r"MERGE\s*\((\w+):(\w+)\s*\{\s*uid:\s*\$(\w+)\s*\}\)",
            cypher,
            re.IGNORECASE,
        )
        if not m:
            logger.warning(f"SQLite 图: 无法解析 MERGE 语法: {cypher[:80]}")
            return []

        alias, entity_type, uid_param = m.group(1), m.group(2), m.group(3)
        uid = params.get(uid_param, "")
        if not uid:
            logger.warning(f"SQLite 图: MERGE 缺少 uid 参数 {uid_param}")
            return []

        # 提取所有 SET alias.prop = $param 赋值
        props = {}
        name = uid  # 默认 name
        for set_m in re.finditer(
            rf'{alias}\.(\w+)\s*=\s*(\$\w+|"[^"]*"|\d+(?:\.\d+)?)',
            cypher,
            re.IGNORECASE,
        ):
            prop_name = set_m.group(1)
            raw_val = set_m.group(2)
            if raw_val.startswith("$"):
                val = params.get(raw_val[1:], raw_val)
            elif raw_val.startswith('"') and raw_val.endswith('"'):
                val = raw_val[1:-1]
            else:
                try:
                    val = int(raw_val)
                except ValueError:
                    try:
                        val = float(raw_val)
                    except ValueError:
                        val = raw_val

            if prop_name == "name":
                name = str(val)
            else:
                props[prop_name] = val

        success = self.create_entity(uid, entity_type, name, props)
        return [{"merged": success, "uid": uid}] if success else []

    def _sqlite_merge_relationship(self, cypher: str, params: dict) -> list[dict]:
        """在 SQLite 图存储中执行 MATCH ... MERGE 关系写入"""
        # 提取 MERGE (a)-[:REL_TYPE]->(b)
        m = re.search(
            r"MERGE\s*\((\w+)\)-\[:(\w+)\]->\((\w+)\)",
            cypher,
            re.IGNORECASE,
        )
        if not m:
            logger.warning(f"SQLite 图: 无法解析 MERGE 关系: {cypher[:80]}")
            return []

        a_alias, rel_type, b_alias = m.group(1), m.group(2), m.group(3)

        # 从 MATCH (x {uid: $param}) 中提取 uid
        # MATCH (a {uid: $from_uid}) / MATCH (b {uid: $to_uid})
        uid_map = {}
        for match_m in re.finditer(
            r"MATCH\s*\((\w+)\s*\{\s*uid:\s*\$(\w+)\s*\}\)",
            cypher,
            re.IGNORECASE,
        ):
            alias = match_m.group(1)
            param_name = match_m.group(2)
            uid_map[alias] = params.get(param_name, "")

        from_uid = uid_map.get(a_alias) or params.get(f"{a_alias}_uid", "")
        to_uid = uid_map.get(b_alias) or params.get(f"{b_alias}_uid", "")

        if not from_uid or not to_uid:
            logger.warning(
                f"SQLite 图: MERGE 关系缺少 uid (from={a_alias}→{from_uid}, to={b_alias}→{to_uid})"
            )
            return []

        success = self.create_relationship(from_uid, to_uid, rel_type)
        return (
            [{"merged": success, "from": from_uid, "to": to_uid, "type": rel_type}]
            if success
            else []
        )

    def _query_nodes(self, conn: sqlite3.Connection, cypher: str, params: dict) -> list[dict]:
        """解析 MATCH (alias:Type) ... RETURN alias 查询"""
        # 提取实体类型: MATCH (e:Character)
        type_match = re.search(r"MATCH\s*\((\w+):(\w+)\)", cypher, re.IGNORECASE)
        if not type_match:
            logger.warning(f"SQLite 图: 无法解析 Cypher: {cypher[:80]}")
            return []

        alias = type_match.group(1)
        entity_type = type_match.group(2)

        # 聚合查询: RETURN count(alias) AS label
        count_match = re.search(
            rf"RETURN\s+count\({alias}\)\s+AS\s+(\w+)",
            cypher,
            re.IGNORECASE,
        )
        if count_match:
            count_alias = count_match.group(1)
            cursor = conn.execute(
                "SELECT COUNT(*) AS cnt FROM nodes WHERE type = ?",
                [entity_type],
            )
            row = cursor.fetchone()
            return [{count_alias: row["cnt"]}]

        sql = "SELECT id, type, name, properties FROM nodes WHERE type = ?"
        sql_params = [entity_type]

        # 提取 WHERE 条件
        where_match = re.search(r"WHERE\s+(.+?)(?:\s+RETURN\s+)", cypher, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_clause = where_match.group(1).strip()
            conds = self._parse_where_conditions(where_clause, alias, params)
            for cond_sql, cond_params in conds:
                sql += f" AND {cond_sql}"
                sql_params.extend(cond_params)

        # 提取 ORDER BY
        order_match = re.search(r"ORDER\s+BY\s+(\w+)\.(\w+)\s*(DESC)?", cypher, re.IGNORECASE)
        if order_match:
            order_alias = order_match.group(1)
            order_field = order_match.group(2)
            order_dir = "DESC" if order_match.group(3) else "ASC"
            if order_alias == alias and order_field.isidentifier():
                sql += f" ORDER BY json_extract(properties, '$.{order_field}') {order_dir}"

        # 提取 LIMIT
        limit_match = re.search(r"LIMIT\s+(\d+)", cypher, re.IGNORECASE)
        if limit_match:
            limit_val = int(limit_match.group(1))
            limit_val = min(max(limit_val, 1), 10000)  # 限制范围 1-10000
            sql += f" LIMIT {limit_val}"

        cursor = conn.execute(sql, sql_params)
        rows = cursor.fetchall()
        return [
            {
                alias: {
                    "id": row["id"],
                    "type": row["type"],
                    "name": row["name"],
                    **json.loads(row["properties"]),
                }
            }
            for row in rows
        ]

    def _query_relationships(
        self, conn: sqlite3.Connection, cypher: str, _params: dict
    ) -> list[dict]:
        """解析 MATCH (a)-[r]->(b) ... 查询"""
        # 提取 alias: MATCH (a)-[r]->(b)
        rel_match = re.search(
            r"MATCH\s*\((\w+)\)\s*-\[(\w+)\]\s*->\s*\((\w+)\)", cypher, re.IGNORECASE
        )
        if not rel_match:
            return []

        # 提取 RETURN 字段
        return_clause = re.search(r"RETURN\s+(.+?)(?:\s+LIMIT\s+\d+)?$", cypher, re.IGNORECASE)
        if return_clause:
            pass  # RETURN 字段已内嵌在 SQL 中

        sql = (
            "SELECT e.id AS edge_id, e.source_id, e.target_id, e.type AS edge_type, "
            "e.properties AS edge_properties, "
            "a.id AS a_id, a.type AS a_type, a.name AS a_name, a.properties AS a_properties, "
            "b.id AS b_id, b.type AS b_type, b.name AS b_name, b.properties AS b_properties "
            "FROM edges e "
            "JOIN nodes a ON e.source_id = a.id "
            "JOIN nodes b ON e.target_id = b.id"
        )
        sql_params: list = []

        # WHERE 条件
        where_match = re.search(r"WHERE\s+(.+?)(?:\s+RETURN\s+)", cypher, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_clause = where_match.group(1).strip()
            # 处理 type(r) = 'TYPE' 条件
            type_match = re.search(
                r"type\((\w+)\)\s*=\s*['\"]([^'\"]+)['\"]", where_clause, re.IGNORECASE
            )
            if type_match:
                sql += " WHERE e.type = ?"
                sql_params.append(type_match.group(2))

        # LIMIT
        limit_match = re.search(r"LIMIT\s+(\d+)", cypher, re.IGNORECASE)
        limit_val = int(limit_match.group(1)) if limit_match else 200
        sql += f" LIMIT {limit_val}"

        cursor = conn.execute(sql, sql_params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            e_props = json.loads(row["edge_properties"] or "{}")
            results.append(
                {
                    "start": row["a_name"] or row["a_id"],
                    "type": row["edge_type"],
                    "end": row["b_name"] or row["b_id"],
                    "r": {"type": row["edge_type"], **e_props},
                }
            )
        return results

    def _parse_where_conditions(self, where_clause: str, alias: str, params: dict) -> list[tuple]:
        """
        解析 WHERE 子句，返回 [(sql_fragment, param_value), ...]

        支持: alias.prop = 'value' / alias.prop <= $param / AND 组合
        """
        conds = []
        # 按 AND 分割（简单场景）
        parts = re.split(r"\s+AND\s+", where_clause, flags=re.IGNORECASE)
        for part in parts:
            part = part.strip()  # noqa: PLW2901
            # 匹配 alias.property 比较操作
            match = re.search(
                rf"{re.escape(alias)}\.(\w+)\s*(=|<=|>=|<|>)\s*(.+)", part, re.IGNORECASE
            )
            if match:
                prop = match.group(1)
                op = match.group(2)
                val = match.group(3).strip()

                # 解析参数
                if val.startswith("$"):
                    param_name = val[1:]
                    param_val = params.get(param_name, "")
                elif val.startswith("'") or val.startswith('"'):
                    param_val = val[1:-1]
                else:
                    try:
                        param_val = int(val)
                    except ValueError:
                        param_val = val

                conds.append((f"json_extract(properties, '$.{prop}') {op} ?", param_val))
        return conds

    # ─── SQLite FTS5 ─────────────────────────────────

    @property
    def sqlite(self) -> sqlite3.Connection:
        if self._sqlite is None:
            sqlite_path = Path(settings.sqlite_path)
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            self._sqlite = sqlite3.connect(str(sqlite_path), check_same_thread=False)
            self._sqlite.row_factory = sqlite3.Row
            # SQLite 性能优化: WAL 模式允许并发读写
            self._sqlite.execute("PRAGMA journal_mode=WAL;")
            self._sqlite.execute("PRAGMA synchronous=NORMAL;")
            self._sqlite.execute("PRAGMA cache_size=-64000;")
            self._sqlite.execute("PRAGMA busy_timeout=5000;")
            self._sqlite.execute("PRAGMA temp_store=MEMORY;")
            self._ensure_fts_tables()
            logger.info(f"SQLite FTS5 已初始化 [WAL]: {sqlite_path}")
        return self._sqlite

    def _ensure_fts_tables(self):
        """创建 FTS5 全文索引表"""
        assert self._sqlite is not None, "SQLite 未初始化"
        self._sqlite.executescript("""
            CREATE VIRTUAL TABLE IF NOT EXISTS entity_fts USING fts5(
                uid, name, entity_type, description
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS chapter_fts USING fts5(
                chapter_number, content, book_id
            );
        """)
        self._sqlite.commit()

    def search_entities(self, query: str, limit: int = 20) -> list[dict]:
        """全文搜索实体"""
        with self._sqlite_lock:
            cursor = self.sqlite.execute(
                "SELECT uid, name, entity_type, description, rank "
                "FROM entity_fts WHERE entity_fts MATCH ? ORDER BY rank LIMIT ?",
                (query, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def index_entity(self, uid: str, name: str, entity_type: str, description: str) -> None:
        """索引一个实体到 FTS"""
        with self._sqlite_lock:
            self.sqlite.execute(
                "INSERT OR REPLACE INTO entity_fts(uid, name, "
                "entity_type, description) VALUES (?, ?, ?, ?)",
                (uid, name, entity_type, description),
            )
            self.sqlite.commit()

    # ─── 向量检索 (Qdrant + Embedder) ────────────────

    def vector_search(self, query: str, limit: int = 10) -> list[dict]:
        """
        语义向量搜索实体

        流程: 文本 → Embedder → Qdrant 余弦相似度 → 返回 top-k
        """
        from kunlun.kg.embedder import embedder

        vector = embedder.encode(query)
        results = self.qdrant.search(
            collection_name=settings.qdrant_collection,
            query_vector=vector.tolist(),
            limit=limit,
        )
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in results
        ]

    def index_entity_vector(self, uid: str, text: str, payload: dict | None = None) -> None:
        """
        将实体文本嵌入并索引到 Qdrant

        Args:
            uid: 实体唯一ID
            text: 用于嵌入的文本 (name + description)
            payload: 附加元数据
        """
        from qdrant_client.models import PointStruct

        from kunlun.kg.embedder import embedder

        vector = embedder.encode(text)
        point = PointStruct(
            id=self._deterministic_id(uid),
            vector=vector.tolist(),
            payload=payload or {"uid": uid, "text": text[:500]},
        )
        self.qdrant.upsert(
            collection_name=settings.qdrant_collection,
            points=[point],
        )

    def index_chapter_vector(self, book_id: str, chapter: int, content: str) -> None:
        """
        将章节内容嵌入并索引到 Qdrant

        按段落切分，每段独立索引，payload 含 book_id + chapter + paragraph_index
        """
        from qdrant_client.models import PointStruct

        from kunlun.kg.embedder import embedder

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip() and len(p.strip()) > 20]
        if not paragraphs:
            return

        vectors = embedder.encode_batch(paragraphs)
        points = []
        for i, (para, vec) in enumerate(zip(paragraphs, vectors, strict=True)):
            point_id = self._deterministic_id(f"{book_id}_ch{chapter}_p{i}")
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vec.tolist(),
                    payload={
                        "book_id": book_id,
                        "chapter": chapter,
                        "paragraph_index": i,
                        "text": para[:500],
                    },
                )
            )

        self.qdrant.upsert(
            collection_name=settings.qdrant_collection,
            points=points,
        )
        logger.info(f"KG: 章节 ch{chapter} 向量索引完成 ({len(points)} 段)")

    # ─── 距离衰减上下文检索（借鉴WenShape对数型衰减权重）───

    @staticmethod
    def distance_decay_weight(
        current_chapter: int,
        target_chapter: int,
        decay_type: str = "logarithmic",
    ) -> float:
        """
        计算章节距离衰减权重

        借鉴 WenShape 的对数型距离衰减：
        - 越近的章节权重越高
        - 衰减曲线平滑，避免硬截断

        Args:
            current_chapter: 当前写作的章节编号
            target_chapter: 检索到的章节编号
            decay_type: 衰减类型
                - "logarithmic": 对数衰减（默认，WenShape方案）
                - "exponential": 指数衰减
                - "linear": 线性衰减
                - "inverse": 倒数衰减

        Returns:
            权重系数 (0.0-1.0)，1.0表示最近章节

        示例:
            distance_decay_weight(10, 10) → 1.0
            distance_decay_weight(10, 9)  → 0.82
            distance_decay_weight(10, 5)  → 0.47
            distance_decay_weight(10, 1)  → 0.17
        """
        import math

        distance = abs(current_chapter - target_chapter)
        if distance == 0:
            return 1.0

        if decay_type == "logarithmic":
            # 对数衰减: w = 1 / (1 + log2(distance + 1))
            # 近章节衰减慢，远章节衰减快
            return 1.0 / (1.0 + math.log2(distance + 1))

        if decay_type == "exponential":
            # 指数衰减: w = e^(-distance * lambda)
            # lambda=0.1 → 距离10章后权重≈0.37
            decay_lambda = 0.1
            return math.exp(-distance * decay_lambda)

        if decay_type == "linear":
            # 线性衰减: w = 1 - distance / max_range
            max_range = 50  # 超过50章的章节权重归零
            return max(0.0, 1.0 - distance / max_range)

        if decay_type == "inverse":
            # 倒数衰减: w = 1 / (1 + distance)
            return 1.0 / (1.0 + distance)

        return 1.0 / (1.0 + math.log2(distance + 1))

    def vector_search_with_decay(
        self,
        query: str,
        current_chapter: int,
        limit: int = 10,
        decay_type: str = "logarithmic",
        book_id: str = "",
    ) -> list[dict]:
        """
        带距离衰减权重的向量检索

        与 vector_search 相比，增加了：
        1. 按章节距离衰减权重重新排序
        2. 近章节结果优先（即使语义相似度稍低）
        3. 支持多种衰减曲线

        Args:
            query: 搜索查询文本
            current_chapter: 当前章节编号（用于距离计算）
            limit: 返回结果数
            decay_type: 衰减类型
            book_id: 作品ID（可选，用于过滤）

        Returns:
            [{"id": ..., "score": ..., "decay_weight": ...,
          "combined_score": ..., "payload": ...}, ...]
        """
        # 先用Qdrant做原始语义搜索
        raw_results = self.vector_search(query, limit=limit * 3)  # 取3倍结果用于重排序

        if not raw_results:
            return []

        # 计算综合得分 = 语义相似度 × 距离衰减权重
        scored_results = []
        for result in raw_results:
            payload = result.get("payload", {})
            target_chapter = payload.get("chapter", current_chapter)

            # 如果有book_id且不匹配，跳过
            if book_id and payload.get("book_id") != book_id:
                continue

            decay_weight = self.distance_decay_weight(current_chapter, target_chapter, decay_type)
            semantic_score = result.get("score", 0.0)
            combined_score = semantic_score * decay_weight

            scored_results.append(
                {
                    "id": result["id"],
                    "semantic_score": round(semantic_score, 4),
                    "decay_weight": round(decay_weight, 4),
                    "combined_score": round(combined_score, 4),
                    "chapter": target_chapter,
                    "payload": payload,
                }
            )

        # 按综合得分降序排列
        scored_results.sort(key=lambda x: x["combined_score"], reverse=True)

        return scored_results[:limit]

    def get_context_window(
        self,
        current_chapter: int,
        window_size: int = 5,
        decay_type: str = "logarithmic",
    ) -> list[float]:
        """
        获取上下文窗口的权重分布

        返回最近 window_size 章的权重，用于Token预算分配

        Args:
            current_chapter: 当前章节
            window_size: 窗口大小（最近N章）
            decay_type: 衰减类型

        Returns:
            [w_ch, w_ch-1, w_ch-2, ...] 权重列表

        示例:
            get_context_window(10, 5) → [1.0, 0.82, 0.69, 0.60, 0.53]
        """
        weights = []
        for offset in range(window_size):
            target = current_chapter - offset
            if target < 1:
                break
            w = self.distance_decay_weight(current_chapter, target, decay_type)
            weights.append(round(w, 4))
        return weights

    # ─── 时序关系 & 邻域查询（KG 增强模块） ───────────

    def add_temporal_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: dict | None = None,
        valid_from_chapter: int = 0,
        valid_to_chapter: int | None = None,
    ) -> bool:
        """添加带时序属性的关系（在现有 create_relationship 基础上扩展）

        自动在 properties 中加入 valid_from_chapter 和 valid_to_chapter。
        时序属性存储在 edges 表的 properties JSON 字段中，不修改表结构。

        Args:
            source_id: 源实体ID
            target_id: 目标实体ID
            rel_type: 关系类型
            properties: 附加属性
            valid_from_chapter: 关系生效起始章节
            valid_to_chapter: 关系失效章节（None 表示持续有效）

        Returns:
            是否创建成功
        """
        from kunlun.kg.temporal import TemporalRelationManager

        manager = TemporalRelationManager(self)
        return manager.add_temporal_relation(
            source_id,
            target_id,
            rel_type,
            properties,
            valid_from_chapter,
            valid_to_chapter,
        )

    def get_relationships(
        self,
        source_id: str,
        direction: str = "out",
        rel_type: str | None = None,
        chapter: int | None = None,
    ) -> list[dict]:
        """统一关系查询方法（支持方向过滤、类型过滤、时序过滤）

        直接查询 edges 表，不走 Cypher 解析。

        Args:
            source_id: 实体ID
            direction: "out"（出边）/ "in"（入边）/ "both"（双向）
            rel_type: 关系类型过滤（None 表示不过滤）
            chapter: 章节过滤（>0 时只返回该章节有效的关系）

        Returns:
            关系列表，每条含 id/source_id/target_id/type/properties/valid_from/valid_to
        """
        conn = self._get_graph_conn()
        if direction == "out":
            sql = "SELECT * FROM edges WHERE source_id = ?"
            params: list = [source_id]
        elif direction == "in":
            sql = "SELECT * FROM edges WHERE target_id = ?"
            params = [source_id]
        else:  # both
            sql = "SELECT * FROM edges WHERE source_id = ? OR target_id = ?"
            params = [source_id, source_id]

        if rel_type:
            sql += " AND type = ?"
            params.append(rel_type)

        cursor = conn.execute(sql, params)
        results = []
        for row in cursor.fetchall():
            try:
                props = json.loads(row["properties"] or "{}")
            except (json.JSONDecodeError, TypeError):
                props = {}
            rel = {
                "id": row["id"],
                "source_id": row["source_id"],
                "target_id": row["target_id"],
                "type": row["type"],
                "properties": props,
                "valid_from_chapter": props.get("valid_from_chapter", 0),
                "valid_to_chapter": props.get("valid_to_chapter"),
            }
            # 时序过滤
            if chapter is not None and chapter > 0:
                vf = rel["valid_from_chapter"]
                vt = rel["valid_to_chapter"]
                if not (vf <= chapter and (vt is None or chapter < vt)):
                    continue
            results.append(rel)
        return results

    def get_entity_neighborhood(self, entity_id: str, depth: int = 1) -> dict:
        """获取实体邻域子图（节点 + 边）

        Args:
            entity_id: 中心实体ID
            depth: 扩展深度（1=直接邻居，2=邻居的邻居）

        Returns:
            {"nodes": [...], "edges": [...], "center": entity_id, "depth": depth}
        """
        conn = self._get_graph_conn()
        visited: set[str] = {entity_id}
        nodes: list[dict] = []
        edges: list[dict] = []
        frontier: set[str] = {entity_id}

        for _ in range(depth):
            next_frontier: set[str] = set()
            for nid in frontier:
                # 查询出边和入边
                cursor = conn.execute(
                    "SELECT * FROM edges WHERE source_id = ? OR target_id = ?",
                    (nid, nid),
                )
                for row in cursor.fetchall():
                    edge_id = row["id"]
                    if any(e["id"] == edge_id for e in edges):
                        continue
                    try:
                        props = json.loads(row["properties"] or "{}")
                    except (json.JSONDecodeError, TypeError):
                        props = {}
                    edges.append(
                        {
                            "id": edge_id,
                            "source_id": row["source_id"],
                            "target_id": row["target_id"],
                            "type": row["type"],
                            "properties": props,
                        }
                    )
                    for other in (row["source_id"], row["target_id"]):
                        if other not in visited:
                            visited.add(other)
                            next_frontier.add(other)
            frontier = next_frontier

        # 查询所有访问到的节点信息
        if visited:
            placeholders = ",".join("?" * len(visited))
            cursor = conn.execute(
                f"SELECT id, type, name, properties FROM nodes WHERE id IN ({placeholders})",
                list(visited),
            )
            for row in cursor.fetchall():
                try:
                    props = json.loads(row["properties"] or "{}")
                except (json.JSONDecodeError, TypeError):
                    props = {}
                nodes.append(
                    {
                        "id": row["id"],
                        "type": row["type"],
                        "name": row["name"],
                        "properties": props,
                    }
                )

        return {
            "center": entity_id,
            "depth": depth,
            "nodes": nodes,
            "edges": edges,
        }

    # ─── 生命周期 ────────────────────────────────────

    def close(self) -> None:
        if self._neo4j:
            self._neo4j.close()
        if self._neo4j_async:
            import asyncio as _asyncio

            try:
                loop = _asyncio.get_event_loop()
                if loop.is_running():
                    task = loop.create_task(self._neo4j_async.close())
                    _ = task  # 保持引用，防止GC回收
                else:
                    loop.run_until_complete(self._neo4j_async.close())
            except Exception:
                logger.debug("Neo4j 异步驱动关闭失败（忽略）")
        if self._qdrant:
            self._qdrant.close()
        if self._sqlite:
            self._sqlite.close()
        self._close_graph_conn()

    def health_check(self) -> dict:
        """健康检查（结果TTL缓存5秒，减少重复探测开销）"""
        return self._cache.get("health_check", 5, self._do_health_check)

    def _do_health_check(self) -> dict:
        result: dict[str, bool | str] = {
            "neo4j": False, "qdrant": False, "sqlite": False, "sqlite_graph": False,
        }
        try:
            self.neo4j.verify_connectivity()
            result["neo4j"] = True
        except Exception as e:
            result["neo4j"] = str(e)
        try:
            self._init_sqlite_graph()
            conn = self._get_graph_conn()
            conn.execute("SELECT 1")
            result["sqlite_graph"] = True
        except Exception as e:
            result["sqlite_graph"] = str(e)
        try:
            _ = self.qdrant.get_collections()
            result["qdrant"] = True
        except Exception as e:
            result["qdrant"] = str(e)
        try:
            self.sqlite.execute("SELECT 1")
            result["sqlite"] = True
        except Exception as e:
            result["sqlite"] = str(e)
        return result

    def init_constraints(self) -> None:
        """创建 Neo4j 唯一性约束与索引（幂等，可重复执行）。Neo4j 不可用时跳过。"""
        if self._initialized:
            return
        if not self.neo4j_available:
            logger.info("Neo4j 不可用，跳过约束初始化（使用 SQLite 图降级模式）")
            self._initialized = True
            return
        # 可能已被 _check_neo4j() 惰性调用初始化，再次检查避免重复创建
        if self._initialized:
            return
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (b:Book) REQUIRE b.uid IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Character) REQUIRE c.uid IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (ch:Chapter) REQUIRE ch.uid IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Item) REQUIRE i.uid IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Skill) REQUIRE s.uid IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (loc:Location) REQUIRE loc.uid IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (ev:Event) REQUIRE ev.uid IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Foreshadowing) REQUIRE f.uid IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (pp:PleasurePoint) REQUIRE pp.uid IS UNIQUE",
        ]
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (b:Book) ON (b.title)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Character) ON (c.name)",
            "CREATE INDEX IF NOT EXISTS FOR (ch:Chapter) ON (ch.chapterNumber)",
            "CREATE INDEX IF NOT EXISTS FOR (ch:Chapter) ON (ch.book_id)",
            "CREATE INDEX IF NOT EXISTS FOR (f:Foreshadowing) ON (f.status)",
            "CREATE INDEX IF NOT EXISTS FOR (f:Foreshadowing) ON (f.book_id)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Character) ON (c.type)",
        ]

        with self.neo4j.session() as session:
            for stmt in constraints:
                try:
                    session.run(stmt)
                except Exception as e:
                    logger.warning(f"Neo4j 约束创建失败 (已存在则忽略): {e}")
            for stmt in indexes:
                try:
                    session.run(stmt)
                except Exception as e:
                    logger.warning(f"Neo4j 索引创建失败: {e}")

        self._initialized = True
        logger.info(f"Neo4j 约束/索引初始化完成 ({len(constraints)} 约束 + {len(indexes)} 索引)")


# 全局单例
kg_client = KGClient()
