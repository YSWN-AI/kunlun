"""
LLM 语义缓存模块标准 pytest 测试
"""

import pytest

pytestmark = pytest.mark.unit


class TestLLMCache:
    """LLM 语义缓存层"""

    @pytest.fixture
    def cache(self):
        from kunlun.llm_cache import CacheMode, LLMCache

        # 清理持久化 SQLite 缓存，保证测试隔离
        # （Redis 不可用时 LLMCache 会走 SQLite 降级路径，残留数据会导致
        #  test_cache_miss 误命中上一次运行写入的条目）
        import sqlite3
        from pathlib import Path

        db_path = Path(__file__).resolve().parents[1] / "data" / "llm_cache.db"
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("DELETE FROM llm_cache")
            conn.commit()
            conn.close()
        except Exception:
            pass

        c = LLMCache()
        c.configure(CacheMode.SEMANTIC)
        return c

    @pytest.fixture
    def sample_messages(self):
        return [
            {"role": "system", "content": "你是一个网文写作助手。"},
            {"role": "user", "content": "请帮我写一段修真小说的战斗场景。"},
        ]

    def test_cache_miss(self, cache, sample_messages):
        result = cache.get(sample_messages, model="deepseek-chat")
        assert result is None, "新请求应为缓存miss"

    def test_cache_set_and_get(self, cache, sample_messages):
        cache.set(sample_messages, "剑光闪过，林尘侧身避开...", model="deepseek-chat")
        result = cache.get(sample_messages, model="deepseek-chat")
        assert result == "剑光闪过，林尘侧身避开..."

    def test_exact_match_same_messages(self, cache, sample_messages):
        cache.set(sample_messages, "response_A", model="gpt-4o")
        result = cache.get(sample_messages, model="gpt-4o")
        assert result == "response_A"

    def test_exact_match_different_model(self, cache, sample_messages):
        """不同模型应有不同缓存键"""
        cache.set(sample_messages, "deepseek_response", model="deepseek-chat")
        cache.set(sample_messages, "gpt_response", model="gpt-4o")
        assert cache.get(sample_messages, model="deepseek-chat") == "deepseek_response"
        assert cache.get(sample_messages, model="gpt-4o") == "gpt_response"

    def test_different_messages_different_key(self, cache):
        msgs1 = [{"role": "user", "content": "写修仙"}]
        msgs2 = [{"role": "user", "content": "写武侠"}]
        cache.set(msgs1, "修仙内容", model="deepseek-chat")
        assert cache.get(msgs2, model="deepseek-chat") is None
        assert cache.get(msgs1, model="deepseek-chat") == "修仙内容"

    def test_disabled_mode(self, sample_messages):
        from kunlun.llm_cache import CacheMode, LLMCache

        c = LLMCache()
        c.configure(CacheMode.DISABLED)
        result = c.get(sample_messages)
        assert result is None, "DISABLED 模式应始终返回 None"

    def test_cache_stats(self, cache, sample_messages):
        cache.set(sample_messages, "hello", model="deepseek-chat")
        stats = cache.get_stats()
        assert stats.total_requests >= 0
        assert hasattr(stats, "hit_rate")
        assert 0.0 <= stats.hit_rate <= 1.0

    def test_cache_clear(self, cache, sample_messages):
        cache.set(sample_messages, "test", model="deepseek-chat")
        assert cache.get(sample_messages, model="deepseek-chat") == "test"
        removed = cache.clear()
        assert removed >= 0

    def test_compute_key_deterministic(self, cache):
        msgs = [{"role": "user", "content": "你好"}]
        k1 = cache._compute_key(msgs, "gpt-4o")
        k2 = cache._compute_key(msgs, "gpt-4o")
        assert k1 == k2
        assert len(k1) == 32  # MD5 hex
