"""
昆仑创作引擎 — 文本嵌入器

封装 sentence-transformers，提供:
- 文本 → 768维向量
- 批量嵌入
- 无GPU降级策略 (CPU + 缓存)

嵌入模型: paraphrase-multilingual-MiniLM-L12-v2 (多语言, 384维 → pad到768)
真实部署可替换为 bge-large-zh-v1.5 (1024维)
"""

from __future__ import annotations

import hashlib
import os
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

# 国内用户：优先使用 HuggingFace 镜像
if not os.environ.get("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"


# 模型缓存目录（打包环境下放到 DATA_DIR/models，避免下载到系统临时目录）
def _get_models_dir() -> str:
    data_dir = os.environ.get("KUNLUN_DATA_DIR", "")
    if data_dir:
        return str(Path(data_dir) / "models")
    return str(Path(__file__).parent.parent.parent / "data" / "models")


os.environ.setdefault("HF_HOME", _get_models_dir())

# 嵌入向量维度
EMBEDDING_DIM = 768

# 模型选择: 优先轻量多语言模型（更快下载），中文专用模型作为升级选项
MODEL_PRIORITY = [
    "paraphrase-multilingual-MiniLM-L12-v2",  # 384维 → pad to 768（~120MB，快速下载）
    "BAAI/bge-large-zh-v1.5",  # 1024维 → 截断到 768（~1.3GB，更准确）
]

# 缓存 — 改用 OrderedDict 实现 O(1) LRU，替代 O(n²) 的 dict+list 组合
_embedding_cache: OrderedDict[str, np.ndarray] = OrderedDict()
MAX_CACHE_SIZE = 5000
EMBED_BATCH_SIZE = 64


class Embedder:
    """
    文本嵌入器

    能力:
    - ✅ 单文本嵌入 (encode)
    - ✅ 批量嵌入 (encode_batch)
    - ✅ 内存缓存 (SHA256 → 向量)
    - ✅ 自动模型降级
    - ✅ 无GPU时 CPU fallback
    - ❌ 不训练模型
    - ❌ 不加载专用微调权重
    """

    def __init__(self):
        self._model: Any | None = None
        self._model_name: str = ""
        self._model_dim: int = 0
        self._encode_count: int = 0
        self._total_time: float = 0.0

    @property
    def model(self) -> Any:
        """懒加载模型"""
        if self._model is None:
            self._load_model()
        return self._model

    def _load_model(self):
        """尝试按优先级加载嵌入模型"""
        for model_name in MODEL_PRIORITY:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(f"Embedder: 尝试加载 {model_name}")
                self._model = SentenceTransformer(model_name, device="cpu")
                self._model_name = model_name
                self._model_dim = self._model.get_sentence_embedding_dimension()
                logger.info(f"Embedder: 已加载 {model_name} (dim={self._model_dim})")
                return
            except ImportError:
                logger.warning("Embedder: sentence-transformers 未安装")
                break
            except Exception as e:
                logger.warning(f"Embedder: {model_name} 加载失败: {e}")

        # 所有模型都不可用 → 使用确定性哈希向量作为回退
        logger.warning("Embedder: 无可用模型，使用哈希向量回退 (不推荐生产使用)")
        self._model = "hash"
        self._model_name = "hash_fallback"
        self._model_dim = EMBEDDING_DIM

    def available(self) -> bool:
        """检查嵌入是否可用"""
        return self._model is not None and self._model != "hash"

    def encode(self, text: str) -> np.ndarray:
        """单文本嵌入"""
        vector = self._try_cache(text)
        if vector is not None:
            return vector

        t0 = time.time()
        vector = self._do_encode(text)
        self._cache_and_count(text, vector, time.time() - t0)
        return vector

    def encode_batch(self, texts: list[str]) -> list[np.ndarray]:
        """批量嵌入 (最多 64 条一批)"""
        results: list[np.ndarray | None] = []
        uncached = []
        uncached_indices = []

        for i, text in enumerate(texts):
            v = self._try_cache(text)
            if v is not None:
                results.append(v)
            else:
                uncached.append(text)
                uncached_indices.append(i)
                results.append(None)

        if uncached:
            t0 = time.time()
            vectors = self._do_encode_batch(uncached)
            elapsed = time.time() - t0
            for pos, (idx, vec) in enumerate(zip(uncached_indices, vectors, strict=True)):
                results[idx] = vec
                self._cache_and_count(uncached[pos], vec, elapsed / len(uncached))

        return [v for v in results if v is not None]

    def _try_cache(self, text: str) -> np.ndarray | None:
        key = hashlib.sha256(text.encode()).hexdigest()
        cached = _embedding_cache.get(key)
        if cached is not None:
            # OrderedDict: move_to_end 是 O(1)，替代原 O(n) 的 list.remove+append
            _embedding_cache.move_to_end(key)
        return cached

    def _cache_and_count(self, text: str, vector: np.ndarray, elapsed: float):
        key = hashlib.sha256(text.encode()).hexdigest()
        if key in _embedding_cache:
            _embedding_cache[key] = vector
            _embedding_cache.move_to_end(key)
        else:
            # LRU 淘汰：缓存满时移除最旧的条目（popitem(last=False) 是 O(1)）
            if len(_embedding_cache) >= MAX_CACHE_SIZE:
                _embedding_cache.popitem(last=False)
            _embedding_cache[key] = vector
        self._encode_count += 1
        self._total_time += elapsed

    def _do_encode(self, text: str) -> np.ndarray:
        """实际调用模型编码"""
        if self._model == "hash":
            return self._hash_vector(text)

        try:
            vec = self.model.encode([text], normalize_embeddings=False)[0]
            return self._pad_to_dim(vec)
        except Exception as e:
            logger.warning(f"Embedder: 编码失败，降级为哈希: {e}")
            return self._hash_vector(text)

    def _do_encode_batch(self, texts: list[str]) -> list[np.ndarray]:
        if self._model == "hash":
            return [self._hash_vector(t) for t in texts]

        all_vecs = []
        try:
            for i in range(0, len(texts), EMBED_BATCH_SIZE):
                chunk = texts[i : i + EMBED_BATCH_SIZE]
                vecs = self.model.encode(chunk, normalize_embeddings=False)
                all_vecs.extend(vecs)
            return [self._pad_to_dim(v) for v in all_vecs]
        except Exception as e:
            logger.warning(f"Embedder: 批量编码失败，降级为哈希: {e}")
            return [self._hash_vector(t) for t in texts]

    def _pad_to_dim(self, vec: np.ndarray) -> np.ndarray:
        """统一输出维度"""
        if vec.shape[0] == EMBEDDING_DIM:
            return vec.astype(np.float32)
        if vec.shape[0] < EMBEDDING_DIM:
            padded = np.zeros(EMBEDDING_DIM, dtype=np.float32)
            padded[: vec.shape[0]] = vec
            return padded
        return vec[:EMBEDDING_DIM].astype(np.float32)

    @staticmethod
    def _hash_vector(text: str) -> np.ndarray:
        """确定性哈希向量 (seed=42 固定)"""
        # 分段哈希累加
        hashes = []
        for i in range(0, len(text), 16):
            chunk = text[i : i + 16]
            digest = hashlib.md5(chunk.encode(), usedforsecurity=False)
            hashes.append(int(digest.hexdigest(), 16))

        rng = np.random.RandomState(42)
        vec = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        for h in hashes:
            rng.seed(h % (2**31 - 1))
            vec += rng.randn(EMBEDDING_DIM).astype(np.float32) / len(hashes)

        # L2归一化
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    @property
    def stats(self) -> dict:
        return {
            "model": self._model_name,
            "dim": self._model_dim,
            "target_dim": EMBEDDING_DIM,
            "available": self.available(),
            "encode_count": self._encode_count,
            "cache_size": len(_embedding_cache),
            "avg_latency_ms": round(self._total_time / max(self._encode_count, 1) * 1000, 1),
        }


# 全局单例
embedder = Embedder()
