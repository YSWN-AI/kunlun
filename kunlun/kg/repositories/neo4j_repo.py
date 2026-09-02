"""
昆仑创作引擎 — Neo4j 图数据库仓储实现

封装 Neo4j Bolt 连接，提供异步 Cypher 查询能力。
"""

from __future__ import annotations

from loguru import logger

from kunlun.config import settings
from kunlun.kg.repositories.base import GraphRepository


class Neo4jGraphRepository(GraphRepository):
    """Neo4j 图数据库仓储 — Bolt 连接"""

    def __init__(self):
        self._uri = getattr(settings, "neo4j_uri", "bolt://localhost:7687")
        self._user = getattr(settings, "neo4j_user", "neo4j")
        self._password = getattr(settings, "neo4j_password", "")
        self._driver = None
        self._available = False

        try:
            from neo4j import AsyncGraphDatabase

            self._driver = AsyncGraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password),
            )
            self._available = True
        except Exception as e:
            logger.warning(f"Neo4j 驱动不可用: {e}")

    @property
    def backend_name(self) -> str:
        return "neo4j"

    def health_check_sync(self) -> bool:
        """同步健康检查（用于工厂初始化）"""
        if not self._driver:
            return False
        try:
            from neo4j import GraphDatabase

            d = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
            with d.session() as s:
                s.run("RETURN 1")
            d.close()
            return True
        except Exception as e:
            logger.debug(f"Neo4j 同步健康检查失败: {e}")
            return False

    async def query(self, cypher: str, params: dict | None = None) -> list[dict]:
        if not self._driver:
            raise RuntimeError("Neo4j 驱动未初始化")

        async with self._driver.session() as session:
            result = await session.run(cypher, parameters=params or {})
            return [dict(record) async for record in result]

    async def query_single(self, cypher: str, params: dict | None = None) -> dict | None:
        results = await self.query(cypher, params)
        return results[0] if results else None

    async def execute(self, cypher: str, params: dict | None = None) -> None:
        if not self._driver:
            raise RuntimeError("Neo4j 驱动未初始化")

        async with self._driver.session() as session:
            await session.run(cypher, parameters=params or {})

    async def health_check(self) -> bool:
        try:
            await self.query("RETURN 1")
            return True
        except Exception as e:
            logger.debug(f"Neo4j 异步健康检查失败: {e}")
            return False

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()

    def close_sync(self) -> None:
        if self._driver:
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    _task = loop.create_task(self._driver.close())  # noqa: RUF006
                else:
                    loop.run_until_complete(self._driver.close())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self._driver.close())
