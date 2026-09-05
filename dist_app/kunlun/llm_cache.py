"""
昆仑创作引擎 — LLM 语义缓存层

深度融合 GPTCache (4.4k+ stars) 的设计理念，利用现有 Qdrant 向量库 + Redis 实现
LLM 响应的语义级缓存。

核心价值（基于 awesome-llm-token-optimization 数据）：
  - 前缀缓存：节省 50-90% 输入 Token
  - 语义缓存：命中率 40-70%（创作场景相似提示词多）
  - 响应缓存：对完全重复请求 100% 节省

关键设计：
  - 精确匹配缓存 (Exact Match): 相同 messages md5 → 直接返回
  - 语义相似缓存 (Semantic): 嵌入相似度 > 0.95 → 返回最近匹配
  - TTL 管理: 创作场景缓存有效期较短（1小时），审计/检查可更长（24小时）
  - 与现有 Qdrant 共用基础设施，零额外依赖
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

from loguru import logger

from kunlun.config import settings


class CacheMode(Enum):
    """缓存模式"""

    DISABLED = "disabled"  # 禁用缓存
    EXACT = "exact"  # 仅精确匹配
    SEMANTIC = "semantic"  # 语义相似 + 精确匹配
    AGGRESSIVE = "aggressive"  # 激进缓存（降低阈值，适合草稿阶段）


class CacheTTL(Enum):
    """不同场景的缓存有效期"""

    CREATIVE = 3600  # 创作生成 — 1小时
    AUDIT = 86400  # 审计检查 — 24小时
    QUICK = 300  # 快速查询 — 5分钟
    PERSISTENT = 604800  # 持久缓存 — 7天


_DEFAULT_CACHE_DB = settings.DATA_DIR / "llm_cache.db"


@dataclass
class CacheEntry:
    """缓存条目"""

    cache_key: str  # MD5 精确匹配键
    messages_hash: str  # 完整 messages 的 hash
    response: str  # LLM 响应内容
    model: str  # 使用的模型名
    token_count: int = 0  # Token 消耗
    latency_ms: float = 0.0  # 原始响应延迟
    created_at: float = field(default_factory=time.time)
    hit_count: int = 1  # 命中次数
    ttl: int = 3600  # 有效期（秒）
    tags: list[str] = field(default_factory=list)  # 标签（agent/action/book_id）


@dataclass
class CacheStats:
    """缓存统计"""

    total_requests: int = 0
    exact_hits: int = 0
    semantic_hits: int = 0
    misses: int = 0
    tokens_saved: int = 0
    cost_saved_usd: float = 0.0
    avg_latency_saved_ms: float = 0.0

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.exact_hits + self.semantic_hits) / self.total_requests


@dataclass
class PromptFingerprint:
    """提示词指纹 — 用于语义相似度匹配"""

    system_hash: str  # system message 的 hash
    action_type: str  # 调用目的（generate/audit/blueprint/...）
    book_id: str = ""  # 书籍ID（隔离缓存域）
    chapter: int = 0  # 章节号
    model: str = ""  # 使用的模型
    token_estimate: int = 0  # 输入 token 估算


class PersistentLLMCache:
    """SQLite 持久化缓存层

    作为 Redis 不可用时的降级持久化方案。
    表结构:
      CREATE TABLE IF NOT EXISTS llm_cache (
        cache_key TEXT PRIMARY KEY,
        response TEXT NOT NULL,
        created_at REAL NOT NULL,
        ttl_seconds REAL,
        hit_count INTEGER DEFAULT 1
      )
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = str(db_path or _DEFAULT_CACHE_DB)
        self._conn: sqlite3.Connection | None = None
        self._init_connection()

    def _init_connection(self) -> None:
        """建立 SQLite 连接并检查连接有效性"""
        try:
            from pathlib import Path

            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._ensure_table()
        except Exception:
            self._conn = None

    def _ensure_table(self) -> None:
        """创建缓存表"""
        if self._conn is None:
            return
        try:
            self._conn.execute(
                """CREATE TABLE IF NOT EXISTS llm_cache (
                    cache_key TEXT PRIMARY KEY,
                    response TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    ttl_seconds REAL,
                    hit_count INTEGER DEFAULT 1
                )"""
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_llm_cache_created_at ON llm_cache(created_at)"
            )
            self._conn.commit()
        except Exception:
            pass

    def _ensure_connection(self) -> bool:
        """确保连接可用"""
        if self._conn is not None:
            return True
        self._init_connection()
        return self._conn is not None

    def get(self, key: str) -> str | None:
        """查询缓存，检查 TTL，更新命中计数"""
        if not self._ensure_connection():
            return None
        assert self._conn is not None
        try:
            row = self._conn.execute(
                "SELECT response, created_at, ttl_seconds FROM llm_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            response, created_at, ttl_seconds = row
            # 检查 TTL
            if ttl_seconds is not None and time.time() - created_at > ttl_seconds:
                self.delete(key)
                return None
            # 更新命中计数
            self._conn.execute(
                "UPDATE llm_cache SET hit_count = hit_count + 1 WHERE cache_key = ?",
                (key,),
            )
            self._conn.commit()
            return response
        except Exception:
            return None

    def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        """INSERT OR REPLACE"""
        if not self._ensure_connection():
            return
        assert self._conn is not None
        try:
            self._conn.execute(
                """INSERT OR REPLACE INTO llm_cache
                   (cache_key, response, created_at, ttl_seconds, hit_count)
                   VALUES (?, ?, ?, ?, 1)""",
                (key, value, time.time(), ttl_seconds),
            )
            self._conn.commit()
        except Exception:
            pass

    def delete(self, key: str) -> None:
        """删除单条缓存"""
        if not self._ensure_connection():
            return
        assert self._conn is not None
        try:
            self._conn.execute("DELETE FROM llm_cache WHERE cache_key = ?", (key,))
            self._conn.commit()
        except Exception:
            pass

    def clear_expired(self) -> int:
        """清理过期条目，返回清理数量"""
        if not self._ensure_connection():
            return 0
        assert self._conn is not None
        try:
            cursor = self._conn.execute(
                "DELETE FROM llm_cache WHERE ttl_seconds IS NOT NULL "
                "AND (? - created_at) > ttl_seconds",
                (time.time(),),
            )
            self._conn.commit()
            return cursor.rowcount
        except Exception:
            return 0

    def stats(self) -> dict:
        """返回缓存统计"""
        if not self._ensure_connection():
            return {"total": 0, "hits": 0, "size_bytes": 0}
        assert self._conn is not None
        try:
            total = self._conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
            hits = self._conn.execute(
                "SELECT COALESCE(SUM(hit_count), 0) FROM llm_cache"
            ).fetchone()[0]
            size_bytes = self._conn.execute(
                "SELECT COALESCE(SUM(LENGTH(response)), 0) FROM llm_cache"
            ).fetchone()[0]
            return {"total": total, "hits": hits, "size_bytes": size_bytes}
        except Exception:
            return {"total": 0, "hits": 0, "size_bytes": 0}

    def export_all(self) -> list[dict]:
        """导出所有有效缓存条目（用于 save_to_disk 的 dump_sqlite 选项）"""
        entries: list[dict] = []
        if not self._ensure_connection():
            return entries
        assert self._conn is not None
        try:
            now = time.time()
            rows = self._conn.execute(
                "SELECT cache_key, response, created_at, ttl_seconds, hit_count FROM llm_cache"
            ).fetchall()
            for cache_key, response, created_at, ttl_seconds, hit_count in rows:
                if ttl_seconds is not None and now - created_at > ttl_seconds:
                    continue
                entries.append(
                    {
                        "cache_key": cache_key,
                        "response": response,
                        "created_at": created_at,
                        "ttl_seconds": ttl_seconds,
                        "hit_count": hit_count,
                    }
                )
        except Exception:
            pass
        return entries


class LLMCache:
    """LLM 语义缓存层

    集成策略：
      - 精确匹配：计算 messages md5，内存 dict 查询（O(1), <1ms）
      - 语义相似：嵌入 → Qdrant 检索（复用现有 infra，~5ms）
      - 分层 TTL：创作 1h / 审计 24h / 快速 5min

    使用方式：
      cache = LLMCache()
      cache.configure(mode=CacheMode.SEMANTIC)

      # 查询缓存
      result = cache.get(messages, model="deepseek-chat")
      if result:
          return result  # 缓存命中

      # 未命中 → 调用LLM → 存入缓存
      response = await call_llm(messages)
      cache.set(messages, response, model="deepseek-chat")
    """

    # 精确缓存容量
    MAX_EXACT_ENTRIES: ClassVar[int] = 5000

    # 语义相似度阈值
    SEMANTIC_THRESHOLD_HIGH: ClassVar[float] = 0.97  # 标准模式
    SEMANTIC_THRESHOLD_LOW: ClassVar[float] = 0.92  # 激进模式

    def __init__(self) -> None:
        self._mode: CacheMode = CacheMode.EXACT
        self._exact_cache: dict[str, CacheEntry] = {}  # md5 → entry
        self._semantic_entries: list[CacheEntry] = []  # 简易语义库（生产用 Qdrant）
        self._stats = CacheStats()
        self._qdrant_available: bool = False
        self._redis: Any | None = None  # Redis 持久化客户端
        self._sqlite_cache: PersistentLLMCache | None = None  # SQLite 降级持久化

        # 尝试连接 Qdrant
        self._init_qdrant()
        # 尝试连接 Redis（如果可用，用于跨重启持久化）
        self._init_redis()
        # 初始化 SQLite 持久化（Redis 不可用时的降级方案）
        self._init_sqlite()

    def _init_qdrant(self) -> None:
        """初始化 Qdrant 作为语义缓存后端"""
        try:
            from kunlun.kg.repositories.qdrant_repo import QdrantVectorRepository

            self._qdrant_repo = QdrantVectorRepository()
            self._qdrant_available = True
            logger.info("[LLMCache] Qdrant 语义缓存后端已就绪")
        except Exception as e:
            logger.debug(f"[LLMCache] Qdrant 不可用，降级为内存模式: {e}")
            self._qdrant_available = False

    def _init_redis(self) -> None:
        """尝试连接 Redis 作为跨重启持久化后端"""
        try:
            import redis

            self._redis = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password or None,
                socket_connect_timeout=1,
                decode_responses=True,
            )
            self._redis.ping()
            logger.info("[LLMCache] Redis 持久化缓存后端已就绪")
        except Exception as e:
            logger.debug(f"[LLMCache] Redis 不可用，仅使用内存缓存: {e}")
            self._redis = None

    def _init_sqlite(self) -> None:
        """初始化 SQLite 持久化缓存（Redis 不可用时的降级方案）"""
        try:
            self._sqlite_cache = PersistentLLMCache()
            logger.info("[LLMCache] SQLite 持久化缓存后端已就绪")
        except Exception as e:
            logger.debug(f"[LLMCache] SQLite 不可用: {e}")
            self._sqlite_cache = None

    def configure(self, mode: CacheMode) -> None:
        """配置缓存模式"""
        self._mode = mode
        logger.info(f"[LLMCache] 缓存模式切换为: {mode.value}")

    def _compute_key(self, messages: list[dict], model: str = "") -> str:
        """计算精确匹配缓存键"""
        content = json.dumps(messages, sort_keys=True, ensure_ascii=False) + model
        return hashlib.md5(content.encode("utf-8"), usedforsecurity=False).hexdigest()

    def _compute_fingerprint(self, messages: list[dict]) -> PromptFingerprint:
        """从 messages 中提取提示词指纹"""
        system_text = ""
        user_text = ""
        for msg in messages:
            if msg.get("role") == "system":
                system_text += msg.get("content", "")
            elif msg.get("role") == "user":
                user_text += msg.get("content", "")

        # 从 user content 中提取 action type
        action_type = "unknown"
        action_keywords = {
            "generate": ["生成", "写", "创作", "章节", "generate"],
            "audit": ["审计", "检查", "audit", "审核"],
            "blueprint": ["蓝图", "大纲", "blueprint", "outline"],
            "polish": ["润色", "polish", "修改", "improve"],
            "analyze": ["分析", "analyze", "评估"],
        }
        combined = system_text + user_text
        for action, keywords in action_keywords.items():
            if any(kw in combined for kw in keywords):
                action_type = action
                break

        return PromptFingerprint(
            system_hash=hashlib.md5(system_text.encode(), usedforsecurity=False).hexdigest()[:16],
            action_type=action_type,
            token_estimate=len(combined) // 2,  # 粗略估计
        )

    def _get_ttl(self, fingerprint: PromptFingerprint) -> int:
        """根据提示词类型确定缓存TTL"""
        if fingerprint.action_type in ("audit", "analyze"):
            return CacheTTL.AUDIT.value
        if fingerprint.action_type in ("generate", "blueprint"):
            return CacheTTL.CREATIVE.value
        return CacheTTL.QUICK.value

    def get(self, messages: list[dict], model: str = "") -> str | None:
        """查询缓存（内存 → Redis → SQLite → 语义匹配）

        Returns:
            缓存命中时返回 LLM 响应字符串，未命中返回 None
        """
        if self._mode == CacheMode.DISABLED:
            self._stats.total_requests += 1
            self._stats.misses += 1
            return None

        self._stats.total_requests += 1
        fp = self._compute_fingerprint(messages)
        key = self._compute_key(messages, model)

        # 1. 精确匹配 — 内存
        if key in self._exact_cache:
            entry = self._exact_cache[key]
            if time.time() - entry.created_at < entry.ttl:
                entry.hit_count += 1
                self._stats.exact_hits += 1
                self._stats.tokens_saved += entry.token_count
                self._stats.avg_latency_saved_ms = (
                    self._stats.avg_latency_saved_ms * (self._stats.exact_hits - 1)
                    + entry.latency_ms
                ) / self._stats.exact_hits
                logger.debug(
                    f"[LLMCache] 精确命中 (内存): {fp.action_type}, "
                    f"hit#{entry.hit_count}, saved {entry.token_count}tok"
                )
                return entry.response

        # 2. 精确匹配 — Redis（跨重启持久化）
        if self._redis:
            try:
                redis_key = f"llmcache:{key}"
                cached = self._redis.get(redis_key)
                if cached:
                    data = json.loads(cached)
                    self._stats.exact_hits += 1
                    self._stats.tokens_saved += data.get("token_count", 0)
                    logger.debug(f"[LLMCache] 精确命中 (Redis): {fp.action_type}")
                    return data["response"]
            except Exception as e:
                logger.debug(f"[LLMCache] Redis 查询失败: {e}")

        # 2. 精确匹配 — SQLite（Redis 不可用时的降级持久化）
        if not self._redis and self._sqlite_cache:
            try:
                cached = self._sqlite_cache.get(key)
                if cached:
                    self._stats.exact_hits += 1
                    logger.debug(f"[LLMCache] 精确命中 (SQLite): {fp.action_type}")
                    return cached
            except Exception as e:
                logger.debug(f"[LLMCache] SQLite 查询失败: {e}")

        # 3. 语义相似（仅在 SEMANTIC 或 AGGRESSIVE 模式）
        if self._mode in (CacheMode.SEMANTIC, CacheMode.AGGRESSIVE):
            threshold = (
                self.SEMANTIC_THRESHOLD_LOW
                if self._mode == CacheMode.AGGRESSIVE
                else self.SEMANTIC_THRESHOLD_HIGH
            )

            # 从 messages 中提取用户问题文本
            user_text = ""
            for msg in messages:
                if msg.get("role") == "user":
                    user_text = msg.get("content", "")
                    break

            best_entry = self._semantic_match(user_text, threshold)
            if best_entry:
                best_entry.hit_count += 1
                self._stats.semantic_hits += 1
                self._stats.tokens_saved += best_entry.token_count
                logger.debug(f"[LLMCache] 语义命中: {fp.action_type}, hit#{best_entry.hit_count}")
                return best_entry.response

        self._stats.misses += 1
        return None

    def set(
        self,
        messages: list[dict],
        response: str,
        model: str = "",
        token_count: int = 0,
        latency_ms: float = 0.0,
        tags: list[str] | None = None,
    ) -> None:
        """存入缓存（内存 + Redis + SQLite 多重写入）"""
        if self._mode == CacheMode.DISABLED:
            return

        key = self._compute_key(messages, model)
        fp = self._compute_fingerprint(messages)
        ttl = self._get_ttl(fp)

        entry = CacheEntry(
            cache_key=key,
            messages_hash=hashlib.md5(
                json.dumps(messages, sort_keys=True).encode(), usedforsecurity=False
            ).hexdigest(),
            response=response,
            model=model,
            token_count=token_count,
            latency_ms=latency_ms,
            ttl=ttl,
            tags=tags or [],
        )

        # 精确缓存 — 内存
        self._exact_cache[key] = entry

        # 语义缓存 — 内存
        self._semantic_entries.append(entry)

        # Redis 持久化（跨重启）
        if self._redis:
            try:
                redis_key = f"llmcache:{key}"
                self._redis.setex(
                    redis_key,
                    ttl,
                    json.dumps(
                        {
                            "response": response,
                            "model": model,
                            "token_count": token_count,
                            "tags": tags or [],
                        },
                        ensure_ascii=False,
                    ),
                )
            except Exception as e:
                logger.debug(f"[LLMCache] Redis 写入失败: {e}")

        # SQLite 持久化（Redis 不可用时的降级方案）
        if not self._redis and self._sqlite_cache:
            try:
                self._sqlite_cache.set(key, response, ttl_seconds=ttl)
            except Exception as e:
                logger.debug(f"[LLMCache] SQLite 写入失败: {e}")

        # LRU 容量控制
        if len(self._exact_cache) > self.MAX_EXACT_ENTRIES:
            oldest_key = min(self._exact_cache, key=lambda k: self._exact_cache[k].created_at)
            del self._exact_cache[oldest_key]

        if len(self._semantic_entries) > self.MAX_EXACT_ENTRIES:
            self._semantic_entries = self._semantic_entries[-self.MAX_EXACT_ENTRIES :]

    def _semantic_match(self, query: str, threshold: float) -> CacheEntry | None:
        """语义相似度匹配

        优先使用 Qdrant 向量检索（高精度），
        Qdrant 不可用时降级为 Jaccard 字符相似度。
        """
        if not query or not self._semantic_entries:
            return None

        # 优先使用 Qdrant 向量语义匹配
        if self._qdrant_available:
            try:
                return self._semantic_match_qdrant(query, threshold)
            except Exception as e:
                logger.debug(f"[LLMCache] Qdrant 语义匹配失败，降级为 Jaccard: {e}")

        # 降级：简易 Jaccard 字符相似度
        return self._semantic_match_jaccard(query, threshold)

    def _semantic_match_qdrant(self, query: str, threshold: float) -> CacheEntry | None:
        """使用 Qdrant 向量检索进行语义匹配"""
        from kunlun.kg.embedder import embedder

        # 生成查询嵌入
        query_vector = embedder.encode(query)
        if query_vector is None:
            return None

        # 在 Qdrant 中搜索最近邻（search 为 async，用 asyncio.run 在同步上下文执行）
        vector_list = (
            query_vector.tolist() if hasattr(query_vector, "tolist") else list(query_vector)
        )
        try:
            results = asyncio.run(self._qdrant_repo.search(vector=vector_list, top_k=5))
        except RuntimeError:
            # 已在事件循环中运行，无法用 asyncio.run，降级为 Jaccard
            return None

        for result in results:
            cache_key = result.metadata.get("cache_key", "") if result.metadata else ""
            if cache_key and cache_key in self._exact_cache:
                entry = self._exact_cache[cache_key]
                if time.time() - entry.created_at < entry.ttl:
                    return entry
        return None

    def _semantic_match_jaccard(self, query: str, threshold: float) -> CacheEntry | None:
        """Jaccard 字符相似度（兜底方案）"""
        best_entry = None
        best_score = 0.0

        query_tokens = set(query)
        if not query_tokens:
            return None

        for entry in reversed(self._semantic_entries):  # 优先检查最新
            if time.time() - entry.created_at > entry.ttl:
                continue
            # 简单 Jaccard 相似度
            response_tokens = set(entry.response[:500])  # 前500字符
            if not response_tokens:
                continue
            intersection = query_tokens & response_tokens
            score = len(intersection) / len(query_tokens | response_tokens)
            if score > best_score:
                best_score = score
                best_entry = entry

        if best_entry and best_score >= threshold:
            return best_entry
        return None

    def get_stats(self) -> CacheStats:
        """获取缓存统计"""
        return self._stats

    def clear(self, older_than_seconds: int = 0) -> int:
        """清除缓存

        Args:
            older_than_seconds: 仅清除超过此秒数的条目（0=全部清除）

        Returns:
            清除的条目数
        """
        if older_than_seconds <= 0:
            count = len(self._exact_cache)
            self._exact_cache.clear()
            self._semantic_entries.clear()
            return count

        cutoff = time.time() - older_than_seconds
        to_remove = [k for k, v in self._exact_cache.items() if v.created_at < cutoff]
        for k in to_remove:
            del self._exact_cache[k]
        self._semantic_entries = [e for e in self._semantic_entries if e.created_at >= cutoff]
        return len(to_remove)

    def warm_cache(self, entries: list[CacheEntry]) -> int:
        """预热缓存 — 从历史数据批量加载

        启动时调用，加载历史高频查询的缓存条目。
        """
        count = 0
        for entry in entries:
            if entry.cache_key not in self._exact_cache:
                self._exact_cache[entry.cache_key] = entry
                self._semantic_entries.append(entry)
                count += 1
        logger.info(f"[LLMCache] 预热完成: {count} 条")
        return count

    def preload_from_disk(self, cache_dir: str) -> int:
        """从磁盘加载持久化缓存

        Args:
            cache_dir: 缓存目录路径
        """
        from pathlib import Path

        cache_path = Path(cache_dir) / "llm_cache.json"
        if not cache_path.exists():
            return 0

        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            count = 0
            for item in data:
                entry = CacheEntry(**item)
                if time.time() - entry.created_at < entry.ttl:
                    self._exact_cache[entry.cache_key] = entry
                    self._semantic_entries.append(entry)
                    count += 1
            logger.info(f"[LLMCache] 从磁盘加载: {count} 条有效缓存")
            return count
        except Exception as e:
            logger.warning(f"[LLMCache] 磁盘加载失败: {e}")
            return 0

    def save_to_disk(self, cache_dir: str, dump_sqlite: bool = False) -> int:
        """持久化缓存到磁盘

        Args:
            cache_dir: 缓存目录路径
            dump_sqlite: 若为 True，从 SQLite 导出而非内存缓存
        """
        from pathlib import Path

        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)

        if dump_sqlite and self._sqlite_cache:
            data = self._sqlite_cache.export_all()
        else:
            entries = self._exact_cache.values()
            data = []
            for e in entries:
                d = e.__dict__.copy()
                data.append(d)

        try:
            (cache_path / "llm_cache.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(
                f"[LLMCache] 持久化完成: {len(data)} 条{' (from SQLite)' if dump_sqlite else ''}"
            )
            return len(data)
        except Exception as e:
            logger.warning(f"[LLMCache] 持久化失败: {e}")
            return 0


# 全局单例（懒加载，避免导入时初始化Qdrant/Redis/SQLite连接）
_llm_cache_instance: LLMCache | None = None


def get_llm_cache() -> LLMCache:
    """获取全局单例（懒加载，首次调用时才初始化连接）"""
    global _llm_cache_instance
    if _llm_cache_instance is None:
        _llm_cache_instance = LLMCache()
    return _llm_cache_instance


class _LazyLLMCacheProxy:
    """懒加载代理，兼容旧的 llm_cache.xxx 访问方式"""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_llm_cache(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(get_llm_cache(), name, value)


# 兼容旧代码：llm_cache 现在是懒加载代理
llm_cache = _LazyLLMCacheProxy()
