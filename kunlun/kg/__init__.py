"""Kunlun 创作引擎 — 知识图谱包"""

from kunlun.kg.client import KGClient, kg_client
from kunlun.kg.repositories import (
    FullTextRepository,
    GraphRepository,
    VectorRepository,
    get_fulltext_repo,
    get_graph_repo,
    get_vector_repo,
)

__all__ = [
    "FullTextRepository",
    # 仓储模式接口
    "GraphRepository",
    # 传统客户端（向后兼容）
    "KGClient",
    "VectorRepository",
    "get_fulltext_repo",
    "get_graph_repo",
    "get_vector_repo",
    "kg_client",
]
