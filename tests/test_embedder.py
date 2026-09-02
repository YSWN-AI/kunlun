"""
测试: Embedder 文本嵌入器
"""

import pytest

pytestmark = pytest.mark.integration

import numpy as np

from kunlun.kg.embedder import EMBEDDING_DIM, Embedder, _embedding_cache


class TestEmbedder:
    """嵌入器基础测试"""

    @pytest.fixture
    def embedder(self):
        emb = Embedder()
        # 强制加载模型 (不 mock——依赖 sentence-transformers 包)
        yield emb
        # 清缓存
        _embedding_cache.clear()

    def test_model_loading(self, embedder):
        _ = embedder.model  # 触发懒加载
        assert embedder._model is not None
        assert embedder._model_name != ""

    def test_encode_single(self, embedder):
        vec = embedder.encode("这是一段测试文本，用于验证嵌入功能。")
        assert isinstance(vec, np.ndarray)
        assert vec.shape[0] == EMBEDDING_DIM
        assert vec.dtype == np.float32

    def test_encode_batch(self, embedder):
        texts = [
            "第一段文本",
            "第二段文本，稍微长一些的内容",
            "第三段",
        ]
        vecs = embedder.encode_batch(texts)
        assert len(vecs) == 3
        for v in vecs:
            assert v.shape[0] == EMBEDDING_DIM

    def test_encode_empty_string(self, embedder):
        vec = embedder.encode("")
        assert vec.shape[0] == EMBEDDING_DIM

    def test_encode_cache_hit(self, embedder):
        text = "缓存测试文本"
        vec1 = embedder.encode(text)
        count_before = embedder._encode_count
        vec2 = embedder.encode(text)
        # 缓存命中不增加计数
        assert embedder._encode_count == count_before
        np.testing.assert_array_equal(vec1, vec2)

    def test_encode_batch_uses_cache(self, embedder):
        text = "批缓存文本"
        embedder.encode(text)  # 预热缓存
        count_before = embedder._encode_count
        vecs = embedder.encode_batch([text, text])
        # 两个都命中缓存
        assert embedder._encode_count == count_before
        assert len(vecs) == 2

    def test_pad_to_dim_smaller(self, embedder):
        small = np.ones(384, dtype=np.float32)
        padded = embedder._pad_to_dim(small)
        assert padded.shape[0] == EMBEDDING_DIM
        assert padded[0] == 1.0
        assert padded[400] == 0.0

    def test_pad_to_dim_larger(self, embedder):
        large = np.arange(1024, dtype=np.float32)
        cropped = embedder._pad_to_dim(large)
        assert cropped.shape[0] == EMBEDDING_DIM

    def test_pad_to_dim_exact(self, embedder):
        exact = np.random.randn(EMBEDDING_DIM).astype(np.float32)
        result = embedder._pad_to_dim(exact)
        np.testing.assert_array_almost_equal(exact, result)

    def test_hash_vector_deterministic(self, embedder):
        text = "确定性测试"
        v1 = embedder._hash_vector(text)
        v2 = embedder._hash_vector(text)
        np.testing.assert_array_equal(v1, v2)
        assert v1.shape[0] == EMBEDDING_DIM

    def test_hash_vector_different_texts(self, embedder):
        v1 = embedder._hash_vector("文本A")
        v2 = embedder._hash_vector("完全不同的文本B")
        diff = np.linalg.norm(v1 - v2)
        assert diff > 0.01

    def test_hash_vector_normalized(self, embedder):
        v = embedder._hash_vector("测试归一化")
        norm = np.linalg.norm(v)
        assert abs(norm - 1.0) < 0.01

    def test_stats(self, embedder):
        embedder.encode("统计测试")
        stats = embedder.stats
        assert "model" in stats
        assert "dim" in stats
        assert "encode_count" in stats
        assert stats["encode_count"] >= 1
        assert "avg_latency_ms" in stats

    def test_available_flag(self, embedder):
        _ = embedder.model
        # 有真实模型时应为 True
        assert embedder.available() is True or embedder._model == "hash"
