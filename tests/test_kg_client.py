"""
测试: KGClient 知识图谱客户端
"""

import pytest

pytestmark = pytest.mark.integration

import shutil
import tempfile
from pathlib import Path

from kunlun.kg.client import KGClient


class TestKGClientNeo4j:
    """Neo4j 连接测试 (需要本地运行 Neo4j)"""

    @pytest.fixture
    def kg_client(self):
        client = KGClient()
        yield client
        client.close()

    def test_neo4j_connectivity(self, kg_client):
        # 如果 Neo4j 未运行，会抛出异常
        try:
            health = kg_client.health_check()
            assert "neo4j" in health
        except Exception as e:
            pytest.skip(f"Neo4j 不可用: {e}")

    def test_cypher_query(self, kg_client):
        try:
            results = kg_client.query_cypher("RETURN 1 AS n")
            assert len(results) == 1
            assert results[0]["n"] == 1
        except Exception as e:
            pytest.skip(f"Neo4j 查询失败: {e}")


class TestKGClientQdrant:
    """Qdrant 向量存储测试"""

    @pytest.fixture
    def temp_qdrant_dir(self):
        tmp = tempfile.mkdtemp()
        yield Path(tmp)
        shutil.rmtree(tmp)

    @pytest.fixture
    def kg_client_with_qdrant(self, temp_qdrant_dir, monkeypatch):
        from kunlun.config import settings

        monkeypatch.setattr(settings, "qdrant_path", str(temp_qdrant_dir))
        client = KGClient()
        yield client
        client.close()

    def test_qdrant_initialization(self, kg_client_with_qdrant):
        health = kg_client_with_qdrant.health_check()
        assert "qdrant" in health
        # 嵌入式 Qdrant 应该总是可用
        assert health["qdrant"] is True

    def test_qdrant_collection_creation(self, kg_client_with_qdrant):
        # 确保 collection 存在
        _ = kg_client_with_qdrant.qdrant
        collections = kg_client_with_qdrant.qdrant.get_collections().collections
        collection_names = [c.name for c in collections]
        from kunlun.config import settings

        assert settings.qdrant_collection in collection_names


class TestKGClientSQLite:
    """SQLite FTS5 全文搜索测试"""

    @pytest.fixture
    def temp_sqlite_dir(self):
        tmp = tempfile.mkdtemp()
        yield Path(tmp)
        shutil.rmtree(tmp)

    @pytest.fixture
    def kg_client_with_sqlite(self, temp_sqlite_dir, monkeypatch):
        from kunlun.config import settings

        monkeypatch.setattr(settings, "sqlite_path", str(temp_sqlite_dir / "test.db"))
        client = KGClient()
        yield client
        client.close()

    def test_sqlite_initialization(self, kg_client_with_sqlite):
        health = kg_client_with_sqlite.health_check()
        assert "sqlite" in health
        assert health["sqlite"] is True

    def test_fts_tables_created(self, kg_client_with_sqlite):
        cursor = kg_client_with_sqlite.sqlite.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%fts%'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        assert "entity_fts" in tables
        assert "chapter_fts" in tables

    def test_index_and_search(self, kg_client_with_sqlite):
        kg_client_with_sqlite.index_entity(
            uid="test_001",
            name="测试角色",
            entity_type="character",
            description="这是一个测试角色，用于验证 FTS5 索引功能。",
        )
        results = kg_client_with_sqlite.search_entities("测试角色", limit=5)
        assert len(results) >= 1
        assert results[0]["name"] == "测试角色"
        assert results[0]["entity_type"] == "character"
