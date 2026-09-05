"""
昆仑创作引擎 — 仓储工厂

提供单例仓储实例的获取函数。
根据配置自动选择后端实现（Neo4j ↔ SQLite 图, Qdrant ↔ 嵌入式向量）。
"""

from __future__ import annotations

from loguru import logger

from kunlun.kg.repositories.base import FullTextRepository, GraphRepository, VectorRepository

# ── 全局单例 ─────────────────────────────────────────

_graph_repo: GraphRepository | None = None
_vector_repo: VectorRepository | None = None
_fulltext_repo: FullTextRepository | None = None


def get_graph_repo() -> GraphRepository:
    """获取图数据库仓储实例（单例）

    优先级: Neo4j > SQLite Graph 降级
    """
    global _graph_repo  # noqa: PLW0603
    if _graph_repo is not None:
        return _graph_repo

    # 尝试 Neo4j
    try:
        from kunlun.kg.repositories.neo4j_repo import Neo4jGraphRepository

        _graph_repo = Neo4jGraphRepository()
        if _graph_repo.health_check_sync():
            logger.info("GraphRepository: Neo4j 就绪")
            return _graph_repo
        logger.warning("GraphRepository: Neo4j 不可用，降级到 SQLite Graph")
    except Exception as e:
        logger.warning(f"GraphRepository: Neo4j 初始化失败 ({e})，降级到 SQLite Graph")

    # 降级到 SQLite Graph
    from kunlun.kg.repositories.sqlite_graph import SQLiteGraphRepository

    _graph_repo = SQLiteGraphRepository()
    logger.info("GraphRepository: SQLite Graph 就绪（降级模式）")
    return _graph_repo


def get_vector_repo() -> VectorRepository:
    """获取向量数据库仓储实例（单例）

    优先级: Qdrant > 嵌入式（numpy/scipy）
    """
    global _vector_repo  # noqa: PLW0603
    if _vector_repo is not None:
        return _vector_repo

    # 尝试 Qdrant
    try:
        from kunlun.kg.repositories.qdrant_repo import QdrantVectorRepository

        _vector_repo = QdrantVectorRepository()
        logger.info("VectorRepository: Qdrant 就绪")
        return _vector_repo
    except Exception as e:
        logger.warning(f"VectorRepository: Qdrant 不可用 ({e})，降级到嵌入式")

    raise RuntimeError("VectorRepository: 无可用的向量存储后端")


def get_fulltext_repo() -> FullTextRepository:
    """获取全文搜索仓储实例（单例）

    实现: SQLite FTS5
    """
    global _fulltext_repo  # noqa: PLW0603
    if _fulltext_repo is not None:
        return _fulltext_repo

    from kunlun.kg.repositories.sqlite_fts import SQLiteFTSRepository

    _fulltext_repo = SQLiteFTSRepository()
    logger.info("FullTextRepository: SQLite FTS5 就绪")
    return _fulltext_repo


def reset_repositories() -> None:
    """重置所有仓储实例（主要用于测试）"""
    global _graph_repo, _vector_repo, _fulltext_repo  # noqa: PLW0603

    for repo in (_graph_repo, _vector_repo, _fulltext_repo):
        if repo is not None:
            try:
                close_fn = getattr(repo, "close_sync", None)
                if close_fn is not None:
                    close_fn()
            except Exception:
                logger.debug(f"仓库 {type(repo).__name__} 关闭失败（忽略）")

    _graph_repo = None
    _vector_repo = None
    _fulltext_repo = None
