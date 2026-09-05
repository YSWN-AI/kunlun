"""
昆仑创作引擎 — 仓储模式接口层

将 KGClient 上帝对象（1014 行）拆分为 3 个独立仓储接口：
  - GraphRepository: 图数据库操作（Neo4j / SQLite 图降级）
  - VectorRepository: 向量检索（Qdrant / 嵌入式降级）
  - FullTextRepository: 全文搜索（SQLite FTS5）

设计原则:
  - 接口与实现分离（Dependency Inversion）
  - 每个仓储独立可测试（可 mock）
  - 支持运行时切换后端（Neo4j ↔ SQLite 图）

用法:
    from kunlun.kg.repositories import (
        GraphRepository, VectorRepository, FullTextRepository,
        Neo4jGraphRepository, QdrantVectorRepository, SQLiteFTSRepository,
        get_graph_repo, get_vector_repo, get_fulltext_repo,
    )
"""

from kunlun.kg.repositories.base import (
    FullTextRepository,
    GraphRepository,
    VectorRepository,
)
from kunlun.kg.repositories.factory import (
    get_fulltext_repo,
    get_graph_repo,
    get_vector_repo,
)

__all__ = [
    "FullTextRepository",
    # 接口
    "GraphRepository",
    "VectorRepository",
    "get_fulltext_repo",
    # 工厂
    "get_graph_repo",
    "get_vector_repo",
]
