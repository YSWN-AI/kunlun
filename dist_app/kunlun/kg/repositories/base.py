"""
昆仑创作引擎 — 仓储模式抽象接口

定义数据访问层的统一契约，实现依赖倒置原则（DIP）。
所有仓储接口均为抽象基类，确保替换存储后端时无需修改业务代码。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

# ── 实体类型 ─────────────────────────────────────────


class KGEntity(dict):
    """知识图谱实体 — 轻量级类型包装

    扩展 dict，支持属性访问模式。
    用法:
        entity = KGEntity(name="张三", labels=["角色"], properties={"age": 25})
        print(entity.name)  # "张三"
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__dict__ = self


class VectorResult:
    """向量检索结果"""

    __slots__ = ("id", "metadata", "score", "text")

    def __init__(self, id: str, score: float, metadata: dict | None = None, text: str = ""):
        self.id = id
        self.score = score
        self.metadata = metadata or {}
        self.text = text

    def __repr__(self) -> str:
        return f"VectorResult(id={self.id!r}, score={self.score:.4f})"


class SearchResult:
    """全文搜索结果"""

    __slots__ = ("content", "doc_id", "metadata", "score", "snippet")

    def __init__(
        self,
        doc_id: str,
        score: float,
        content: str = "",
        snippet: str = "",
        metadata: dict | None = None,
    ):
        self.doc_id = doc_id
        self.score = score
        self.content = content
        self.snippet = snippet
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        return f"SearchResult(doc_id={self.doc_id!r}, score={self.score:.4f})"


# ── 图数据库仓储接口 ──────────────────────────────────


class GraphRepository(ABC):
    """图数据库仓储接口

    职责: 管理知识图谱的节点、关系和 Cypher 查询。
    实现: Neo4jGraphRepository（生产）、SQLiteGraphRepository（降级）
    """

    @abstractmethod
    async def query(self, cypher: str, params: dict | None = None) -> list[dict]:
        """执行 Cypher 查询。

        Args:
            cypher: Cypher 查询语句
            params: 查询参数

        Returns:
            查询结果列表
        """
        ...

    @abstractmethod
    async def query_single(self, cypher: str, params: dict | None = None) -> dict | None:
        """执行 Cypher 查询，返回单条结果。

        Returns:
            单条结果或 None
        """
        ...

    @abstractmethod
    async def execute(self, cypher: str, params: dict | None = None) -> None:
        """执行写操作（CREATE/MERGE/DELETE/SET）。

        Args:
            cypher: Cypher 写语句
            params: 参数
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """检查图数据库连接是否健康"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """关闭连接"""
        ...

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """当前后端名称（neo4j / sqlite_graph）"""
        ...


# ── 向量数据库仓储接口 ────────────────────────────────


class VectorRepository(ABC):
    """向量数据库仓储接口

    职责: 存储和检索向量嵌入，支持语义搜索。
    实现: QdrantVectorRepository（生产）、EmbeddedVectorRepository（降级）
    """

    @abstractmethod
    async def search(
        self,
        vector: list[float],
        top_k: int = 10,
        filter_condition: dict | None = None,
    ) -> list[VectorResult]:
        """向量相似度搜索。

        Args:
            vector: 查询向量
            top_k: 返回结果数
            filter_condition: 元数据过滤条件

        Returns:
            相似度排序的结果列表
        """
        ...

    @abstractmethod
    async def upsert(
        self,
        id: str,
        vector: list[float],
        metadata: dict | None = None,
        text: str = "",
    ) -> None:
        """插入或更新向量。

        Args:
            id: 实体唯一标识
            vector: 嵌入向量
            metadata: 附加元数据
            text: 关联文本
        """
        ...

    @abstractmethod
    async def delete(self, id: str) -> None:
        """删除向量"""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """检查向量数据库是否健康"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """关闭连接"""
        ...

    @property
    @abstractmethod
    def collection_size(self) -> int:
        """集合中的向量总数"""
        ...


# ── 全文搜索仓储接口 ──────────────────────────────────


class FullTextRepository(ABC):
    """全文搜索仓储接口

    职责: 文本内容索引和关键词搜索。
    实现: SQLiteFTSRepository
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        table: str = "chapters",
    ) -> list[SearchResult]:
        """全文搜索。

        Args:
            query: 搜索关键词
            limit: 返回结果数
            offset: 分页偏移
            table: 搜索表名（chapters/notes/outlines）

        Returns:
            搜索结果列表
        """
        ...

    @abstractmethod
    async def index(
        self,
        doc_id: str,
        content: str,
        metadata: dict | None = None,
        table: str = "chapters",
    ) -> None:
        """索引文档。

        Args:
            doc_id: 文档唯一标识
            content: 文档内容
            metadata: 附加元数据
            table: 索引表名
        """
        ...

    @abstractmethod
    async def delete(self, doc_id: str, table: str = "chapters") -> None:
        """删除文档索引"""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """检查全文搜索是否可用"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """关闭连接"""
        ...
