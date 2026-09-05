"""
SEO 优化器 — 标题/摘要/标签优化

支持:
- 标题优化（增加吸引力）
- 摘要生成（SEO 友好）
- 标签推荐（基于内容分析）
- 关键词提取
- 平台特化优化策略

用法:
    optimizer = SEOOptimizer()
    result = optimizer.optimize(
        title="第42章 决战",
        content="...",
        platform="qidian",
    )
    print(result.optimized_title)  # "第42章 决战！巅峰对决"
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SEOOptimizeResult:
    """SEO 优化结果"""

    original_title: str = ""
    optimized_title: str = ""
    summary: str = ""
    keywords: list[str] = field(default_factory=list)
    suggested_tags: list[str] = field(default_factory=list)
    clickbait_score: int = 0  # 0-100 吸引力评分


class SEOOptimizer:
    """SEO 优化器

    根据不同平台的特点，优化标题、摘要和标签，提升搜索排名和点击率。

    用法:
        optimizer = SEOOptimizer()
        result = optimizer.optimize("第42章 决战", content)
    """

    # 高频情绪词（提升标题吸引力）
    _POWER_WORDS = [
        "惊天",
        "绝密",
        "震撼",
        "逆天",
        "绝世",
        "无双",
        "终极",
        "无限",
        "至极",
        "巅峰",
        "逆转",
        "重生",
        "碾压",
        "横扫",
        "制霸",
        "无敌",
        "封神",
        "觉醒",
    ]

    # 各平台标签权重
    _PLATFORM_TAG_STRATEGIES: dict[str, dict[str, Any]] = {
        "qidian": {
            "max_tags": 5,
            "prefer_genre": True,
            "prefer_length": "short",
            "description": "起点中文网 — 标签影响推荐分发",
        },
        "fanqie": {
            "max_tags": 8,
            "prefer_genre": True,
            "prefer_length": "normal",
            "description": "番茄小说 — 标签是推荐算法的核心",
        },
        "jinjiang": {
            "max_tags": 4,
            "prefer_genre": True,
            "prefer_length": "short",
            "description": "晋江文学城 — 风格标签权重最高",
        },
        "zongheng": {
            "max_tags": 6,
            "prefer_genre": False,
            "prefer_length": "normal",
        },
        "feilu": {
            "max_tags": 10,
            "prefer_genre": False,
            "prefer_length": "long",
            "description": "飞卢小说网 — 标签越多曝光越高",
        },
    }

    def optimize(
        self,
        title: str,
        content: str,
        platform: str = "",
        genre: str = "",
    ) -> SEOOptimizeResult:
        """优化标题/摘要/标签"""
        keywords = self._extract_keywords(content)
        tags = self._suggest_tags(keywords, genre, platform)
        summary = self._generate_seo_summary(content, keywords)
        optimized_title = self._optimize_title(title, keywords)
        clickbait = self._score_clickbait(optimized_title, keywords)

        return SEOOptimizeResult(
            original_title=title,
            optimized_title=optimized_title,
            summary=summary,
            keywords=keywords[:10],
            suggested_tags=tags,
            clickbait_score=clickbait,
        )

    def _extract_keywords(self, content: str, top_n: int = 20) -> list[str]:
        """从内容中提取关键词"""
        # 中文分词简化版（提取 2-4 字词）
        text = re.sub(r"[^\u4e00-\u9fff]", "", content)

        words: list[str] = []
        for length in (4, 3, 2):
            words.extend(text[i : i + length] for i in range(len(text) - length + 1))

        counter = Counter(words)
        # 过滤低质量词
        stop_pattern = re.compile(
            r"(这是|那是|一个|这个|那个|可以|不是|已经|还是|而且|但是|因为|所以|如果|虽然|不过)"
        )
        keywords = [w for w, _ in counter.most_common(top_n * 2) if not stop_pattern.match(w)]
        return keywords[:top_n]

    def _suggest_tags(
        self,
        keywords: list[str],
        genre: str,
        platform: str,
    ) -> list[str]:
        """推荐标签"""
        strategy = self._PLATFORM_TAG_STRATEGIES.get(
            platform, {"max_tags": 6, "prefer_genre": True}
        )
        max_tags = strategy.get("max_tags", 6)

        tags: list[str] = []
        if genre and strategy.get("prefer_genre", True):
            tags.append(genre)

        # 从关键词中筛选独特标签
        for kw in keywords:
            if len(tags) >= max_tags:
                break
            if kw not in tags and len(kw) >= 2:
                tags.append(kw)

        return tags[:max_tags]

    def _optimize_title(self, title: str, keywords: list[str]) -> str:
        """优化标题"""
        optimized = title

        # 为短标题添加修饰
        if len(optimized) < 15 and keywords:
            # 尝试添加一个关键词增强标题
            for kw in keywords[:5]:
                if len(kw) >= 2 and kw not in optimized:
                    optimized = f"{optimized}！{kw}"
                    break

        return optimized

    def _generate_seo_summary(
        self,
        content: str,
        keywords: list[str],
        max_length: int = 200,
    ) -> str:
        """生成 SEO 友好摘要"""
        # 去 HTML
        plain = re.sub(r"<[^>]+>", "", content)

        # 截取
        if len(plain) <= max_length:
            return plain

        # 尽量在句号处截断
        summary = plain[:max_length]
        last_period = max(
            summary.rfind("。"),
            summary.rfind("！"),
            summary.rfind("？"),
        )
        if last_period > max_length // 2:
            summary = plain[: last_period + 1]

        # 确保关键词出现
        for kw in keywords[:3]:
            if kw not in summary and kw in plain:
                keyword_pos = plain.find(kw)
                if keyword_pos > 0:
                    start = max(0, keyword_pos - 20)
                    end = min(len(plain), keyword_pos + len(kw) + 30)
                    snippet = plain[start:end]
                    if snippet not in summary:
                        summary = summary[: max_length // 2] + "……" + snippet + "……"

        return summary

    def _score_clickbait(self, title: str, keywords: list[str]) -> int:
        """评估标题吸引力 (0-100)"""
        score = 30  # 基础分

        # 长度适中加分
        if 10 <= len(title) <= 30:
            score += 20
        elif len(title) < 5:
            score -= 10

        # 情绪词加分
        for word in self._POWER_WORDS:
            if word in title:
                score += 10
                break

        # 关键词覆盖加分
        matched = sum(1 for kw in keywords if kw in title)
        score += min(matched * 5, 20)

        # 标点符号（感叹号/问号增加吸引力）
        score += title.count("！") * 5
        score += title.count("？") * 3

        return min(max(score, 0), 100)

    def batch_optimize(
        self,
        titles: list[dict[str, str]],
        platform: str = "",
    ) -> list[SEOOptimizeResult]:
        """批量优化（仅标题）"""
        results: list[SEOOptimizeResult] = []
        for item in titles:
            result = self.optimize(
                title=item.get("title", ""),
                content=item.get("content", ""),
                platform=platform,
                genre=item.get("genre", ""),
            )
            results.append(result)
        return results
