"""
comments 批注与评论分析引擎 — 读者评论分析、情感判定、反馈归类

核心能力:
1. 读者评论情感分析（正面/负面/中性+强度）
2. 评论自动归类（剧情/角色/文笔/节奏/设定/其他）
3. 评论趋势分析（正面率变化、高频关键词）
4. 零LLM纯规则实现（基于关键词词典）
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from loguru import logger

from kunlun.core.extension_base import BaseExtensionModule

# ============================================================================
# 枚举定义
# ============================================================================


class Sentiment(StrEnum):
    """情感倾向"""

    POSITIVE = "positive"  # 正面
    NEGATIVE = "negative"  # 负面
    NEUTRAL = "neutral"  # 中性
    MIXED = "mixed"  # 混合


class FeedbackCategory(StrEnum):
    """反馈类别"""

    PLOT = "plot"  # 剧情
    CHARACTER = "character"  # 角色
    WRITING = "writing"  # 文笔
    PACING = "pacing"  # 节奏
    SETTING = "setting"  # 设定
    EMOTIONAL = "emotional"  # 情感/爽点
    OTHER = "other"  # 其他


# ============================================================================
# 情感词典
# ============================================================================

POSITIVE_WORDS = {
    "好看",
    "精彩",
    "牛逼",
    "厉害",
    "太棒了",
    "神作",
    "经典",
    "追了",
    "好看哭了",
    "绝了",
    "爱了",
    "上头",
    "停不下来",
    "熬夜看",
    "一口气看完",
    "推荐",
    "好书",
    "佳作",
    "满分",
    "感动",
    "泪目",
    "燃",
    "爽",
    "过瘾",
    "舒服",
    "痛快",
    "期待",
    "加油",
    "支持",
    "赞",
    "顶",
    "好评",
    "五星",
    "太强了",
    "太甜了",
    "太虐了（褒义）",
    "吹爆",
    "打call",
    "文笔好",
    "剧情好",
    "人物好",
    "节奏好",
    "设定好",
    "喜欢",
    "棒",
    "强",
    "赞赞赞",
    "完美",
    "惊艳",
    "欲罢不能",
    "入坑",
    "入股不亏",
    "宝藏",
    "收藏",
}

NEGATIVE_WORDS = {
    "不好看",
    "无聊",
    "垃圾",
    "烂",
    "弃书",
    "看不下去了",
    "水",
    "太水了",
    "水文",
    "拖",
    "太拖了",
    "拖沓",
    "毒",
    "毒点",
    "雷",
    "雷点",
    "踩雷",
    "劝退",
    "逻辑不通",
    "不合理",
    "bug",
    "漏洞",
    "矛盾",
    "人设崩了",
    "人设崩塌",
    "角色崩",
    "性格变了",
    "文笔差",
    "小学生文笔",
    "语句不通",
    "错别字",
    "套路",
    "老套",
    "俗套",
    "千篇一律",
    "审美疲劳",
    "太慢了",
    "节奏慢",
    "看不进去",
    "弃了",
    "失望",
    "差评",
    "一星",
    "负分",
    "垃圾书",
    "注水",
    "灌水",
    "骗字数",
    "凑字数",
    "弱智",
    "侮辱智商",
    "白痴",
    "无语了",
}

# ============================================================================
# 类别关键词
# ============================================================================

CATEGORY_KEYWORDS: dict[FeedbackCategory, set[str]] = {
    FeedbackCategory.PLOT: {
        "剧情",
        "情节",
        "故事",
        "主线",
        "支线",
        "发展",
        "转折",
        "反转",
        "悬念",
        "铺垫",
        "伏笔",
        "收尾",
        "开头",
        "结局",
        "高潮",
        "过渡",
    },
    FeedbackCategory.CHARACTER: {
        "角色",
        "人物",
        "主角",
        "女主",
        "男主",
        "配角",
        "人设",
        "性格",
        "塑造",
        "成长",
        "变化",
        "弧光",
        "讨喜",
        "讨厌",
        "喜欢这个角色",
        "不喜欢这个角色",
    },
    FeedbackCategory.WRITING: {
        "文笔",
        "语句",
        "用词",
        "描写",
        "叙述",
        "对话",
        "修辞",
        "句式",
        "流畅",
        "生硬",
        "优美",
        "干瘪",
        "错别字",
        "病句",
    },
    FeedbackCategory.PACING: {
        "节奏",
        "进度",
        "速度",
        "太快",
        "太慢",
        "拖",
        "水",
        "赶",
        "节奏感",
        "张弛",
        "松紧",
    },
    FeedbackCategory.SETTING: {
        "设定",
        "世界观",
        "体系",
        "等级",
        "境界",
        "功法",
        "背景",
        "时代",
        "架空",
        "现实",
        "合理",
    },
    FeedbackCategory.EMOTIONAL: {
        "爽",
        "爽点",
        "燃",
        "感动",
        "泪目",
        "虐",
        "甜",
        "热血",
        "激动",
        "上头",
        "过瘾",
        "平淡",
        "无聊",
    },
}


# ============================================================================
# 数据类
# ============================================================================


@dataclass
class Comment:
    """单条评论"""

    comment_id: str
    text: str
    chapter_id: str = ""
    timestamp: str = ""
    user_id: str = ""

    # 分析结果
    sentiment: Sentiment = Sentiment.NEUTRAL
    sentiment_score: float = 0.0  # -1到1
    categories: list[FeedbackCategory] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    is_actionable: bool = False  # 是否有可操作的反馈


@dataclass
class AnalyzedComment(Comment):
    """已分析的评论（向后兼容别名）"""

    pass


@dataclass
class CommentReport:
    """评论分析报告"""

    book_id: str
    chapter_id: str = ""
    total_comments: int = 0
    sentiment_distribution: dict[str, int] = field(
        default_factory=dict
    )  # {positive: N, negative: N, ...}
    sentiment_ratio: float = 0.0  # 正面率
    category_distribution: dict[str, int] = field(default_factory=dict)
    top_keywords: list[tuple[str, int]] = field(default_factory=list)
    trending_up: list[str] = field(default_factory=list)  # 上升趋势关键词
    trending_down: list[str] = field(default_factory=list)  # 下降趋势关键词
    actionable_feedback: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""

    def overall_sentiment(self) -> Sentiment:
        """总体情感倾向"""
        if self.sentiment_ratio >= 0.7:
            return Sentiment.POSITIVE
        if self.sentiment_ratio <= 0.3:
            return Sentiment.NEGATIVE
        return Sentiment.NEUTRAL


# ============================================================================
# 评论分析器
# ============================================================================


class CommentAnalyzer(BaseExtensionModule):
    """评论分析器 — 分析读者评论的情感、类别、趋势"""

    def __init__(self, book_id: str = ""):
        super().__init__(book_id)
        self._comment_history: list[Comment] = []
        self._keyword_trends: dict[str, list[int]] = defaultdict(list)  # 关键词→各批次计数

    def analyze_comment(self, comment: Comment) -> Comment:
        """分析单条评论"""
        text = comment.text
        if not text.strip():
            return comment

        # 情感分析
        positive_count = sum(1 for w in POSITIVE_WORDS if w in text)
        negative_count = sum(1 for w in NEGATIVE_WORDS if w in text)

        total = positive_count + negative_count
        if total == 0:
            comment.sentiment = Sentiment.NEUTRAL
            comment.sentiment_score = 0.0
        else:
            comment.sentiment_score = (positive_count - negative_count) / total
            if comment.sentiment_score > 0.3:
                comment.sentiment = Sentiment.POSITIVE
            elif comment.sentiment_score < -0.3:
                comment.sentiment = Sentiment.NEGATIVE
            else:
                comment.sentiment = Sentiment.MIXED

        # 类别检测
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                comment.categories.append(cat)

        if not comment.categories:
            comment.categories.append(FeedbackCategory.OTHER)

        # 关键词提取（负面词=可操作反馈）
        comment.keywords = [w for w in NEGATIVE_WORDS if w in text]
        if not comment.keywords:
            comment.keywords = [w for w in POSITIVE_WORDS if w in text]
        comment.is_actionable = len([w for w in NEGATIVE_WORDS if w in text]) > 0

        self._comment_history.append(comment)
        return comment

    def analyze_batch(
        self,
        comments: list[dict[str, str]],
        chapter_id: str = "",
    ) -> CommentReport:
        """批量分析评论并生成报告

        Args:
            comments: 评论列表 [{"id": ..., "text": ..., "user_id": ..., "timestamp": ...}]
            chapter_id: 关联章节ID

        Returns:
            CommentReport: 分析报告
        """
        report = CommentReport(book_id=self.book_id, chapter_id=chapter_id)

        analyzed: list[Comment] = []
        for c in comments:
            comment = Comment(
                comment_id=c.get("id", ""),
                text=c.get("text", ""),
                chapter_id=chapter_id,
                timestamp=c.get("timestamp", ""),
                user_id=c.get("user_id", ""),
            )
            analyzed.append(self.analyze_comment(comment))

        report.total_comments = len(analyzed)

        if not analyzed:
            report.summary = "暂无评论"
            return report

        # 情感分布
        sentiment_counts: Counter[str] = Counter()
        for c in analyzed:
            sentiment_counts[c.sentiment.value] += 1
        report.sentiment_distribution = dict(sentiment_counts)
        report.sentiment_ratio = sentiment_counts.get("positive", 0) / len(analyzed)

        # 类别分布
        cat_counts: Counter[str] = Counter()
        for c in analyzed:
            for cat in c.categories:
                cat_counts[cat.value] += 1
        report.category_distribution = dict(cat_counts.most_common())

        # 高频关键词
        kw_counts: Counter[str] = Counter()
        for c in analyzed:
            for kw in c.keywords:
                kw_counts[kw] += 1
        report.top_keywords = kw_counts.most_common(10)

        # 可操作的负面反馈
        actionable: list[Comment] = [c for c in analyzed if c.is_actionable]
        for c in actionable:
            report.actionable_feedback.append(
                {
                    "comment_id": c.comment_id,
                    "text": c.text[:100],
                    "sentiment": c.sentiment.value,
                    "keywords": c.keywords,
                    "categories": [cat.value for cat in c.categories],
                }
            )

        # 关键词趋势（对比历史）
        current_kw = set(kw_counts.keys())
        for kw in current_kw:
            self._keyword_trends[kw].append(kw_counts[kw])
        report.trending_up, report.trending_down = self._detect_trends()

        # 生成摘要
        report.summary = self._generate_summary(report)

        logger.info(f"评论分析完成: {report.total_comments}条, 正面率{report.sentiment_ratio:.0%}")
        return report

    def _detect_trends(self) -> tuple[list[str], list[str]]:
        """检测关键词趋势变化"""
        trending_up = []
        trending_down = []

        for kw, counts in self._keyword_trends.items():
            if len(counts) < 2:
                continue
            # 最近两批对比
            if counts[-1] > counts[-2] * 1.5:
                trending_up.append(kw)
            elif counts[-1] < counts[-2] * 0.5:
                trending_down.append(kw)

        return trending_up[:5], trending_down[:5]

    def _generate_summary(self, report: CommentReport) -> str:
        """生成分析摘要"""
        lines = [
            f"评论分析 [{report.chapter_id or '全书'}]:",
            f"  共{report.total_comments}条评论",
            f"  正面率: {report.sentiment_ratio:.0%}",
            f"  主要反馈类别: "
            f"{', '.join(f'{k}({v})' for k, v in list(report.category_distribution.items())[:3])}",
        ]

        if report.top_keywords:
            top_words = ", ".join(f"{w}({c})" for w, c in report.top_keywords[:5])
            lines.append(f"  热词: {top_words}")

        if report.actionable_feedback:
            lines.append(f"  可操作反馈: {len(report.actionable_feedback)}条")

        if report.trending_up:
            lines.append(f"  ↑上升: {', '.join(report.trending_up[:3])}")
        if report.trending_down:
            lines.append(f"  ↓下降: {', '.join(report.trending_down[:3])}")

        return "\n".join(lines)

    def get_overall_stats(self) -> dict[str, Any]:
        """获取全书的评论统计"""
        if not self._comment_history:
            return {"total": 0, "positive_ratio": 0, "message": "暂无评论数据"}

        total = len(self._comment_history)
        positive = sum(1 for c in self._comment_history if c.sentiment == Sentiment.POSITIVE)
        negative = sum(1 for c in self._comment_history if c.sentiment == Sentiment.NEGATIVE)

        return {
            "total": total,
            "positive": positive,
            "negative": negative,
            "positive_ratio": positive / total,
            "negative_ratio": negative / total,
            "actionable_count": sum(1 for c in self._comment_history if c.is_actionable),
        }

    def get_trend_data(self) -> list[dict[str, Any]]:
        """获取情感趋势数据（按批次）"""
        if not self._keyword_trends:
            return []

        # 取所有批次中出现的正面/负面关键词趋势
        batches = max(len(v) for v in self._keyword_trends.values())
        if batches <= 1:
            return []

        trend_data = []
        for i in range(batches):
            pos_count = sum(
                self._keyword_trends[kw][i]
                for kw in self._keyword_trends
                if kw in POSITIVE_WORDS and i < len(self._keyword_trends[kw])
            )
            neg_count = sum(
                self._keyword_trends[kw][i]
                for kw in self._keyword_trends
                if kw in NEGATIVE_WORDS and i < len(self._keyword_trends[kw])
            )
            trend_data.append(
                {
                    "batch": i + 1,
                    "positive_keywords": pos_count,
                    "negative_keywords": neg_count,
                }
            )

        return trend_data


# ============================================================================
# 工厂函数
# ============================================================================


_analyzers: dict[str, CommentAnalyzer] = {}


def get_comment_analyzer(book_id: str = "") -> CommentAnalyzer:
    """获取评论分析器实例（按book_id缓存）"""
    if book_id not in _analyzers:
        _analyzers[book_id] = CommentAnalyzer(book_id=book_id)
    return _analyzers[book_id]
