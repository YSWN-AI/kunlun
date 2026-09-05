"""
昆仑创作引擎 — 数据库配置 (Neo4j, Qdrant, Redis, SQLite)
"""

from __future__ import annotations

from pydantic import BaseModel


class DatabaseConfig(BaseModel):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    qdrant_path: str = ""
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "kunlun_entities"

    sqlite_path: str = ""

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    model_config = {"extra": "ignore"}
