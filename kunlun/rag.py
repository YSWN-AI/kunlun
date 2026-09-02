"""
昆仑创作引擎 — 两阶段RAG召回引擎

设计来源: novel-creator-skill 的两阶段召回 (BM25粗排 + 语义精排)

流程:
  Stage 1 - 粗排 (BM25): 从全量知识库快速筛选候选集（Top-16）
  Stage 2 - 精排 (语义): 用向量相似度对候选集重排序（Top-4）

优势:
  - BM25 保证关键词命中的硬召回（不漏关键实体）
  - 语义排序保证上下文相关性的软匹配（不偏主题）
  - 两阶段结合兼顾精确率和召回率
"""

from __future__ import annotations

import math
from collections import Counter

from loguru import logger


class BM25Scorer:
    """
    BM25 粗排打分器

    纯 Python 实现，不依赖外部数据库。
    用于快速从文本候选集中筛选与查询最相关的条目。

    BM25(q,d) = Σ IDF(qi) × f(qi,d) × (k1+1) / (f(qi,d) + k1 × (1-b + b×|d|/avgdl))

    其中 f(qi,d) = 词 qi 在文档 d 中的出现频率（而非查询中的频率）。
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1  # BM25 参数：词频饱和系数
        self.b = b  # BM25 参数：长度归一化系数
        self._avg_doc_len: float = 0
        self._idf: dict[str, float] = {}
        self._doc_lens: list[int] = []
        self._doc_texts: list[str] = []
        self._doc_tokens: list[list[str]] = []
        self._vocab_size: int = 0

    def fit(self, documents: list[str]):
        """在文档集上计算 IDF 和平均长度，并缓存文档分词结果"""
        if not documents:
            return

        self._doc_texts = documents[:]
        self._doc_tokens = [self._tokenize(d) for d in documents]
        self._doc_lens = [len(toks) for toks in self._doc_tokens]
        self._avg_doc_len = sum(self._doc_lens) / max(len(self._doc_lens), 1)

        # 统计每个词的文档频率
        doc_freq: Counter = Counter()
        for tokens in self._doc_tokens:
            doc_freq.update(set(tokens))

        num_docs = len(documents)
        self._vocab_size = len(doc_freq)
        self._idf = {
            word: math.log((num_docs - freq + 0.5) / (freq + 0.5) + 1.0)
            for word, freq in doc_freq.items()
        }
        logger.debug(f"[BM25] 拟合完成: {num_docs}文档, {self._vocab_size}词")

    def score(self, query: str, doc_idx: int) -> float:
        """计算查询与单个文档的 BM25 分数"""
        if doc_idx < 0 or doc_idx >= len(self._doc_lens):
            return 0.0

        query_terms = self._tokenize(query)
        if not query_terms or not self._idf:
            return 0.0

        score = 0.0
        doc_len = self._doc_lens[doc_idx]
        doc_tokens = self._doc_tokens[doc_idx] if doc_idx < len(self._doc_tokens) else []

        # 构建文档词频表（文档中每个词的出现次数）
        if doc_tokens:
            doc_term_freq: Counter = Counter()
            doc_term_freq.update(doc_tokens)
        else:
            doc_term_freq = Counter()

        for term in set(query_terms):
            if term not in self._idf:
                continue
            idf = self._idf[term]
            # ✅ 关键修复：tf = 词在文档中的出现频率（而非查询频率）
            tf = doc_term_freq.get(term, 0)
            if tf == 0:
                continue
            score += (
                idf
                * (tf * (self.k1 + 1))
                / (tf + self.k1 * (1 - self.b + self.b * doc_len / max(self._avg_doc_len, 1)))
            )

        return score

    def rank(self, query: str, documents: list[str]) -> list[tuple[int, float]]:
        """对文档集排序，返回 [(index, score), ...]"""
        if not self._idf or len(documents) != len(self._doc_lens):
            self.fit(documents)

        scored = [(i, self.score(query, i)) for i in range(len(documents))]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def jaccard_overlap(self, query: str, doc_idx: int) -> float:
        """计算查询与文档的词重叠 Jaccard 系数"""
        query_tokens = set(self._tokenize(query))
        if not query_tokens:
            return 0.0
        doc_tokens = self._doc_tokens[doc_idx] if doc_idx < len(self._doc_tokens) else []
        if not doc_tokens:
            return 0.0
        intersection = query_tokens.intersection(doc_tokens)
        union = query_tokens.union(doc_tokens)
        return len(intersection) / max(len(union), 1)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """简单中文分词（按字/词分割）"""
        text = text.lower()
        # 中文按字符分割，英文按空格
        tokens = [char for char in text if "一" <= char <= "鿿" or char.isalnum()]
        bigrams = [tokens[i] + tokens[i + 1] for i in range(len(tokens) - 1)]
        return tokens + bigrams

    @staticmethod
    def _tokenize_len(text: str) -> int:
        """计算文本的 token 长度"""
        return len([c for c in text if "一" <= c <= "鿿" or c.isalnum()])


class TwoStageRAG:
    """
    两阶段 RAG 召回引擎

    使用方式:
        rag = TwoStageRAG()
        results = rag.retrieve(query, candidate_texts, candidate_metadatas, top_k=4)
    """

    def __init__(self):
        self.bm25 = BM25Scorer()

    def retrieve(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 4,
        entity_names: list[str] | None = None,
    ) -> list[dict]:
        """
        两阶段召回。

        Args:
            query: 查询文本
            candidates: 候选集列表，每项含 {"text": str, "metadata": dict}
            top_k: 最终返回数量
            entity_names: 实体名列表（用于实体增强评分）

        Returns:
            排序后的结果列表，含 score 字段
        """
        if not candidates:
            return []

        texts = [c.get("text", "") for c in candidates]

        # Stage 1: BM25 粗排（全量）
        bm25_scores = self.bm25.rank(query, texts)

        # 取 Top-16 作为精排候选
        stage1_top_k = min(16, len(candidates))
        stage1_indices = [idx for idx, _ in bm25_scores[:stage1_top_k]]

        if len(stage1_indices) <= top_k:
            # 如果粗排后候选已经很少，直接返回
            result = []
            for idx in stage1_indices:
                c = dict(candidates[idx])
                c["retrieval_score"] = round(dict(bm25_scores).get(idx, 0), 4)
                c["retrieval_method"] = "bm25"
                result.append(c)
            return result

        # Stage 2: 混合精排（BM25 + 词重叠 + 实体增强 + 语义）
        stage2_candidates = [candidates[i] for i in stage1_indices]
        return self._hybrid_rerank(
            query, stage2_candidates, stage1_indices, bm25_scores, top_k, entity_names
        )

    def _hybrid_rerank(
        self,
        query: str,
        candidates: list[dict],
        original_indices: list[int],
        bm25_scores: list[tuple[int, float]],
        top_k: int,
        entity_names: list[str] | None = None,
    ) -> list[dict]:
        """混合精排：BM25 × 0.4 + 词重叠 × 0.3 + 实体增强 × 0.3"""
        try:
            from kunlun.kg.client import kg_client

            # 获取向量分数
            vector_results = kg_client.vector_search(query, limit=top_k * 2)
            payload_scores = {}
            for vr in vector_results:
                payload = vr.get("payload") or {}
                text = payload.get("text", "")[:100]
                payload_scores[text] = vr.get("score", 0)

            bm25_score_map = dict(bm25_scores)

            for i, cand in enumerate(candidates):
                text = cand.get("text", "")
                text_preview = text[:100]
                orig_idx = original_indices[i]

                # BM25 分数
                bm25 = bm25_score_map.get(orig_idx, 0)

                # 词重叠 Jaccard
                overlap = self.bm25.jaccard_overlap(query, orig_idx)

                # 实体增强：实体名出现在候选文本中的比例
                entity_boost = 0.0
                if entity_names:
                    matched = sum(1 for e in entity_names if e in text)
                    entity_boost = matched / max(len(entity_names), 1)

                # 向量分数
                vec_score = payload_scores.get(text_preview, 0)

                # 混合分数 (WenShape 混合评分策略)
                cand["bm25_score"] = round(bm25, 4)
                cand["overlap_score"] = round(overlap, 4)
                cand["entity_score"] = round(entity_boost, 4)
                cand["vector_score"] = round(vec_score, 4)
                cand["retrieval_score"] = round(
                    0.4 * bm25 + 0.3 * overlap + 0.3 * entity_boost + 0.2 * vec_score,
                    4,
                )
                cand["retrieval_method"] = "hybrid"

            candidates.sort(key=lambda c: c["retrieval_score"], reverse=True)
            return candidates[:top_k]

        except Exception as e:
            logger.warning(f"[TwoStageRAG] 混合精排失败，回退到 BM25: {e}")
            # 回退：直接返回 BM25 粗排结果
            bm25_score_map = dict(bm25_scores)
            for i, cand in enumerate(candidates):
                orig_idx = original_indices[i]
                cand["retrieval_score"] = round(bm25_score_map.get(orig_idx, 0), 4)
                cand["retrieval_method"] = "bm25_fallback"
            candidates.sort(key=lambda c: c["retrieval_score"], reverse=True)
            return candidates[:top_k]


# 全局单例
two_stage_rag = TwoStageRAG()
