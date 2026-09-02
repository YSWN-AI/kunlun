"""
昆仑创作引擎 — Qdrant 向量数据库仓储实现

封装 Qdrant REST/gRPC 客户端，提供向量相似度搜索和索引能力。
"""

from __future__ import annotations

from loguru import logger

from kunlun.config import settings
from kunlun.kg.repositories.base import VectorRepository, VectorResult


class QdrantVectorRepository(VectorRepository):
    """Qdrant 向量数据库仓储"""

    def __init__(self):
        self._url = getattr(settings, "qdrant_url", "") or "http://localhost:6333"
        self._collection = getattr(settings, "qdrant_collection", "kunlun_entities")
        self._client = None

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            self._client = QdrantClient(url=self._url)
            self._Distance = Distance
            self._VectorParams = VectorParams
            self._ensure_collection()
        except ImportError:
            logger.warning("Qdrant 客户端不可用，请安装: pip install qdrant-client")
            raise

    def _ensure_collection(self) -> None:
        """确保集合存在"""
        assert self._client is not None, "Qdrant client not initialized"
        try:
            collections = self._client.get_collections()
            names = [c.name for c in collections.collections]
            if self._collection not in names:
                vector_dim = 384  # 默认 sentence-transformers 维度
                self._client.create_collection(
                    collection_name=self._collection,
                    vectors_config=self._VectorParams(
                        size=vector_dim,
                        distance=self._Distance.COSINE,
                    ),
                )
                logger.info(f"Qdrant: 创建集合 '{self._collection}' ({vector_dim}d)")
        except Exception as e:
            logger.warning(f"Qdrant: 集合初始化警告: {e}")

    async def search(
        self,
        vector: list[float],
        top_k: int = 10,
        filter_condition: dict | None = None,
    ) -> list[VectorResult]:
        if self._client is None:
            return []

        try:
            results = self._client.search(
                collection_name=self._collection,
                query_vector=vector,
                limit=top_k,
                query_filter=filter_condition,
            )
            return [
                VectorResult(
                    id=str(r.id),
                    score=r.score,
                    metadata=r.payload or {},
                    text=r.payload.get("text", "") if r.payload else "",
                )
                for r in results
            ]
        except Exception as e:
            logger.warning(f"Qdrant 搜索失败: {e}")
            return []

    async def upsert(
        self,
        id: str,
        vector: list[float],
        metadata: dict | None = None,
        text: str = "",
    ) -> None:
        if self._client is None:
            return

        from qdrant_client.models import PointStruct

        payload = metadata or {}
        if text:
            payload["text"] = text

        self._client.upsert(
            collection_name=self._collection,
            points=[PointStruct(id=id, vector=vector, payload=payload)],
        )

    async def delete(self, id: str) -> None:
        if self._client is None:
            return

        self._client.delete(
            collection_name=self._collection,
            points_selector=[id],
        )

    async def health_check(self) -> bool:
        try:
            if self._client is None:
                return False
            self._client.get_collections()
            return True
        except Exception:
            return False

    @property
    def collection_size(self) -> int:
        try:
            if self._client is None:
                return 0
            info = self._client.get_collection(self._collection)
            return info.points_count or 0
        except Exception:
            return 0

    async def close(self) -> None:
        if self._client:
            self._client.close()

    def close_sync(self) -> None:
        if self._client:
            self._client.close()
