"""
昆仑创作引擎 — 质量趋势追踪器

跨章节追踪质量指标变化，帮助作者和系统了解写作质量走势。

追踪的指标:
  - AI特征得分 (0-1)
  - 后写验证得分 (0-1)
  - 套路词密度 (每千字)
  - 番茄流量评级
  - 综合质量评分

用法:
    tracker = QualityTracker("my_book")
    tracker.record(chapter=1, overall_score=0.85, ai_score=0.9)
    tracker.record(chapter=2, overall_score=0.72, ai_score=0.8)
    trend = tracker.get_trend()
    print(trend.direction)  # "improving" / "declining" / "stable"
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from loguru import logger

from kunlun.config import settings


@dataclass
class ChapterMetrics:
    """单章质量指标"""

    chapter: int
    overall_score: float = 0.0
    ai_score: float = 0.0
    post_write_score: float = 0.0
    refiner_issues_per_1k: float = 0.0
    fanqie_ai_score: float = 0.0
    traffic_rating: str = ""
    word_count: int = 0


@dataclass
class QualityTrend:
    """质量趋势"""

    direction: str  # improving / declining / stable / insufficient_data
    slope: float  # 线性回归斜率
    avg_score: float  # 平均分
    latest_score: float  # 最新一章分数
    score_std: float  # 标准差（稳定性）
    chapters_analyzed: int = 0
    suggestions: list[str] = field(default_factory=list)


class QualityTracker:
    """
    质量趋势追踪器

    持久化到磁盘，跨会话可用。
    """

    def __init__(self, book_id: str):
        self.book_id = book_id
        self._data_dir = settings.DATA_DIR / "quality_trends" / book_id
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._records: dict[int, ChapterMetrics] = {}
        self._load()

    def record(self, chapter: int, **metrics) -> ChapterMetrics:
        """记录一章的质量指标"""
        m = ChapterMetrics(
            chapter=chapter,
            overall_score=metrics.get("overall_score", 0.0),
            ai_score=metrics.get("ai_score", 0.0),
            post_write_score=metrics.get("post_write_score", 0.0),
            refiner_issues_per_1k=metrics.get("refiner_issues_per_1k", 0.0),
            fanqie_ai_score=metrics.get("fanqie_ai_score", 0.0),
            traffic_rating=metrics.get("traffic_rating", ""),
            word_count=metrics.get("word_count", 0),
        )
        self._records[chapter] = m
        self._save()
        return m

    def record_from_report(
        self, chapter: int, quality_report, fanqie_report=None
    ) -> ChapterMetrics:
        """从质量看板和番茄门禁报告记录"""
        kwargs = {
            "overall_score": getattr(quality_report, "overall_score", 0),
            "ai_score": getattr(quality_report, "ai_score", 0),
            "post_write_score": getattr(quality_report, "post_write_score", 0),
            "refiner_issues_per_1k": getattr(quality_report, "refiner_issues_per_1k", 0),
            "word_count": getattr(quality_report, "word_count", 0),
        }
        if fanqie_report:
            kwargs["fanqie_ai_score"] = getattr(fanqie_report, "fanqie_ai_score", 0)
            kwargs["traffic_rating"] = getattr(fanqie_report, "traffic_rating", "")
        return self.record(chapter, **kwargs)

    def get(self, chapter: int) -> ChapterMetrics | None:
        return self._records.get(chapter)

    def get_all(self) -> list[ChapterMetrics]:
        return [self._records[ch] for ch in sorted(self._records.keys())]

    def get_latest(self) -> ChapterMetrics | None:
        if not self._records:
            return None
        latest_ch = max(self._records.keys())
        return self._records[latest_ch]

    def get_trend(self, metric: str = "overall_score", min_chapters: int = 3) -> QualityTrend:
        """
        计算质量趋势

        Args:
            metric: 指标名 (overall_score / ai_score / post_write_score)
            min_chapters: 最少需要多少章才能计算趋势

        Returns:
            QualityTrend
        """
        chapters = sorted(self._records.keys())
        if len(chapters) < min_chapters:
            return QualityTrend(
                direction="insufficient_data",
                slope=0,
                avg_score=0,
                latest_score=0,
                score_std=0,
                chapters_analyzed=len(chapters),
                suggestions=["至少需要3章数据才能计算趋势"],
            )

        scores = [getattr(self._records[ch], metric, 0) for ch in chapters]

        # 简单线性回归
        n = len(scores)
        xs = list(range(n))
        mean_x = sum(xs) / n
        mean_y = sum(scores) / n

        num = sum((xs[i] - mean_x) * (scores[i] - mean_y) for i in range(n))
        den = sum((xs[i] - mean_x) ** 2 for i in range(n))
        slope = num / den if den != 0 else 0

        # 标准差
        variance = sum((s - mean_y) ** 2 for s in scores) / n
        std = variance**0.5

        # 方向判断
        if slope > 0.03:
            direction = "improving"
        elif slope < -0.03:
            direction = "declining"
        else:
            direction = "stable"

        suggestions = []
        if direction == "declining":
            suggestions.append(
                f"质量呈下降趋势（斜率{slope:.3f}），建议检查近{min(3, n)}章是否有内容质量下滑"
            )
            if metric == "ai_score":
                suggestions.append("AI得分下降，建议增加手动修改比例")
        elif direction == "improving":
            suggestions.append(f"质量呈上升趋势（斜率{slope:.3f}），保持当前写作节奏")
        if std > 0.15:
            suggestions.append(f"质量波动较大（标准差{std:.3f}），建议保持稳定输出")

        return QualityTrend(
            direction=direction,
            slope=round(slope, 4),
            avg_score=round(mean_y, 3),
            latest_score=round(scores[-1], 3),
            score_std=round(std, 3),
            chapters_analyzed=n,
            suggestions=suggestions,
        )

    def get_summary(self) -> dict:
        """获取完整的质量摘要"""
        records = self.get_all()
        if not records:
            return {"book_id": self.book_id, "total_chapters": 0}

        trend = self.get_trend()
        latest = self.get_latest()

        return {
            "book_id": self.book_id,
            "total_chapters": len(records),
            "latest_chapter": latest.chapter if latest else 0,
            "latest_overall": latest.overall_score if latest else 0,
            "trend_direction": trend.direction,
            "trend_slope": trend.slope,
            "avg_score": trend.avg_score,
            "score_std": trend.score_std,
            "chapters": [
                {
                    "chapter": r.chapter,
                    "overall": r.overall_score,
                    "ai_score": r.ai_score,
                    "word_count": r.word_count,
                    "traffic_rating": r.traffic_rating,
                }
                for r in records[-20:]  # 最近20章
            ],
            "suggestions": trend.suggestions,
        }

    def _save(self):
        path = self._data_dir / "quality_trends.json"
        try:
            data = {
                str(ch): {
                    "chapter": m.chapter,
                    "overall_score": m.overall_score,
                    "ai_score": m.ai_score,
                    "post_write_score": m.post_write_score,
                    "refiner_issues_per_1k": m.refiner_issues_per_1k,
                    "fanqie_ai_score": m.fanqie_ai_score,
                    "traffic_rating": m.traffic_rating,
                    "word_count": m.word_count,
                }
                for ch, m in self._records.items()
            }
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.warning(f"[QualityTracker] 保存失败: {e}")

    def _load(self):
        path = self._data_dir / "quality_trends.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for ch_str, d in data.items():
                ch = int(ch_str)
                self._records[ch] = ChapterMetrics(
                    chapter=ch,
                    overall_score=d.get("overall_score", 0.0),
                    ai_score=d.get("ai_score", 0.0),
                    post_write_score=d.get("post_write_score", 0.0),
                    refiner_issues_per_1k=d.get("refiner_issues_per_1k", 0.0),
                    fanqie_ai_score=d.get("fanqie_ai_score", 0.0),
                    traffic_rating=d.get("traffic_rating", ""),
                    word_count=d.get("word_count", 0),
                )
        except Exception as e:
            logger.warning(f"[QualityTracker] 加载失败: {e}")
