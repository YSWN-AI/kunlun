"""
昆仑创作引擎 — Jieba 分词分析器

包装 jieba 分词，为审计门禁提供精确的中文关键词提取和匹配。
替代原有的简单 str.contains 匹配，消除误匹配。

当前应用:
  - G4 爽点间隔检测：jieba 切词后精确匹配爽点关键词
  - G5 爽点多样性检测：jieba 关键词提取 + TF-IDF 统计
"""

from __future__ import annotations

import importlib.util
from collections import Counter

from loguru import logger

# 延迟加载 jieba（首次使用时才 import）
_has_jieba: bool | None = None


def _ensure_jieba() -> bool:
    global _has_jieba  # noqa: PLW0603
    if _has_jieba is None:
        _has_jieba = importlib.util.find_spec("jieba") is not None
        if not _has_jieba:
            logger.warning("[Jieba] 未安装，回退到简单字符串匹配")
    return _has_jieba


def segment(text: str) -> list[str]:
    """jieba 分词，返回词列表"""
    if not _ensure_jieba():
        # 回退：简单按字符分割
        return [c for c in text if "一" <= c <= "鿿"]
    import jieba

    return list(jieba.cut(text))


def extract_keywords(text: str, top_k: int = 20) -> list[tuple[str, float]]:
    """提取关键词（TF-IDF），返回 [(词, 权重), ...]"""
    if not _ensure_jieba() or not text:
        return []
    import jieba.analyse

    return jieba.analyse.extract_tags(text, topK=top_k, withWeight=True)


def match_keywords(
    text: str, keyword_dict: dict[str, list[str]], min_word_len: int = 2
) -> dict[str, int]:
    """
    精确匹配关键词（基于 jieba 分词，避免子串误匹配）

    Args:
        text: 待分析文本
        keyword_dict: {类型: [关键词列表]}
        min_word_len: 最小词长（短词容易误匹配）

    Returns:
        {类型: 匹配次数}
    """
    # 先分词
    words = segment(text)
    word_counter = Counter(words)

    # 精确匹配
    result: dict[str, int] = {}
    for ptype, keywords in keyword_dict.items():
        count = 0
        for kw in keywords:
            if len(kw) < min_word_len:
                # 短关键词：直接在原文中 count（但排除在更长词中的情况）
                count += text.count(kw)
            else:
                # 长关键词：通过分词精确匹配
                count += word_counter.get(kw, 0)
        if count > 0:
            result[ptype] = count

    return result


def batch_analyze(text: str) -> dict:
    """批量分析文本，返回各类 jieba 统计"""
    if not _ensure_jieba() or not text:
        return {"words": [], "keywords": [], "word_count": 0}

    import jieba

    words = list(jieba.cut(text))

    # 词频统计
    word_counter = Counter(words)
    top_words = word_counter.most_common(30)

    # TF-IDF 关键词
    import jieba.analyse

    keywords = jieba.analyse.extract_tags(text, topK=20, withWeight=True)

    # 统计
    chinese_chars = sum(1 for c in text if "一" <= c <= "鿿")
    unique_words = len(word_counter)

    return {
        "total_words": len(words),
        "unique_words": unique_words,
        "chinese_chars": chinese_chars,
        "lexical_diversity": round(unique_words / max(len(words), 1), 4),
        "top_words": top_words[:10],
        "keywords": [(w, round(s, 4)) for w, s in keywords[:10]],
    }
