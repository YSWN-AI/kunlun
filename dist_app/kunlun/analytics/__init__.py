"""
数据看板增强 — 统计/图表/导出

支持:
- 写作统计 (WritingStats) — 字数/速度/章节统计
- 收益分析 (RevenueAnalytics) — 订阅/打赏/付费章节收益
- 读者分析 (ReaderAnalytics) — 阅读量/留存/互动
- 模型使用 (ModelUsage) — Token消耗/成本/调用次数
- 质量趋势 (QualityTrend) — 审计分数/门禁通过率
- 导出报告 (ExportReport) — CSV/JSON/HTML 格式
- 图表数据 (ChartData) — 适配 ECharts/frontend 数据结构

用法:
    from kunlun.analytics import AnalyticsEngine

    engine = AnalyticsEngine()
    writing = engine.writing_stats("book_001")
    revenue = engine.revenue_analytics("author_001")
    report = engine.export_report("book_001", format="html")
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any


class TimeRange(StrEnum):
    """时间范围"""

    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    ALL = "all"


class ExportFormat(StrEnum):
    """导出格式"""

    CSV = "csv"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"


@dataclass
class WritingStats:
    """写作统计"""

    book_id: str = ""
    total_chapters: int = 0
    total_words: int = 0
    avg_words_per_chapter: float = 0.0
    avg_write_time_minutes: float = 0.0
    words_per_minute: float = 0.0
    total_revision_count: int = 0
    total_write_sessions: int = 0
    # 时间段数据 (date_str -> value)
    daily_words: dict[str, int] = field(default_factory=dict)
    daily_chapters: dict[str, int] = field(default_factory=dict)
    # 趋势
    words_trend: float = 0.0  # 字数变化趋势 (-1 ~ 1)
    speed_trend: float = 0.0  # 速度变化趋势
    # 分布
    chapter_length_distribution: dict[str, int] = field(default_factory=dict)
    # 时段分析
    hour_distribution: dict[int, int] = field(default_factory=dict)  # hour -> sessions


@dataclass
class RevenueAnalytics:
    """收益分析"""

    user_id: str = ""
    total_revenue: float = 0.0
    subscriptions: float = 0.0
    tips: float = 0.0
    paid_chapters: float = 0.0
    # 趋势
    daily_revenue: dict[str, float] = field(default_factory=dict)
    monthly_revenue: dict[str, float] = field(default_factory=dict)
    # 排行
    top_tippers: list[dict[str, Any]] = field(default_factory=list)
    top_paid_chapters: list[dict[str, Any]] = field(default_factory=list)
    # 预测
    projected_monthly: float = 0.0
    growth_rate: float = 0.0


@dataclass
class ReaderAnalytics:
    """读者分析"""

    book_id: str = ""
    total_reads: int = 0
    unique_readers: int = 0
    avg_read_time_seconds: float = 0.0
    completion_rate: float = 0.0  # 读完率
    retention_day7: float = 0.0  # 7日留存
    retention_day30: float = 0.0  # 30日留存
    bounce_rate: float = 0.0  # 跳出率
    # 互动
    total_comments: int = 0
    total_likes: int = 0
    total_shares: int = 0
    # 来源
    source_distribution: dict[str, int] = field(default_factory=dict)
    # 趋势
    daily_reads: dict[str, int] = field(default_factory=dict)
    daily_new_readers: dict[str, int] = field(default_factory=dict)


@dataclass
class ModelUsageStats:
    """模型使用统计"""

    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_cny: float = 0.0
    # 按模型分布
    by_model: dict[str, dict[str, Any]] = field(default_factory=dict)
    # 按功能分布 (writing/audit/revise/...)
    by_function: dict[str, dict[str, Any]] = field(default_factory=dict)
    # 趋势
    daily_calls: dict[str, int] = field(default_factory=dict)
    daily_cost: dict[str, float] = field(default_factory=dict)
    # 效率
    avg_latency_ms: float = 0.0
    cache_hit_rate: float = 0.0


@dataclass
class QualityTrend:
    """质量趋势"""

    book_id: str = ""
    avg_audit_score: float = 0.0
    gate_pass_rate: float = 0.0  # 门禁一次通过率
    revision_rate: float = 0.0  # 需要修订的比例
    icu_trigger_rate: float = 0.0  # ICU 触发率
    # 时间序列
    chapter_scores: dict[int, float] = field(default_factory=dict)
    # 维度分布
    dimension_scores: dict[str, float] = field(default_factory=dict)
    # 趋势
    score_trend: float = 0.0


@dataclass
class DashboardSummary:
    """看板汇总"""

    books_count: int = 0
    total_words_written: int = 0
    total_revenue: float = 0.0
    active_readers: int = 0
    model_cost_today: float = 0.0
    avg_quality_score: float = 0.0
    current_streak_days: int = 0  # 连续写作天数


class AnalyticsEngine:
    """数据分析引擎

    核心职责:
    - 写作统计汇总
    - 收益分析
    - 读者分析
    - 模型使用追踪
    - 质量趋势
    - 看板汇总
    - 报表导出

    用法:
        engine = AnalyticsEngine()
        summary = engine.get_dashboard_summary("user_001")
        engine.export_report("book_001", ExportFormat.HTML)
    """

    def __init__(self):
        # 模拟数据存储
        self._writing: dict[str, WritingStats] = {}
        self._revenue: dict[str, RevenueAnalytics] = {}
        self._readers: dict[str, ReaderAnalytics] = {}
        self._model_usage = ModelUsageStats()
        self._quality: dict[str, QualityTrend] = {}

    # ── 写作统计 ──────────────────────────────────

    def writing_stats(self, book_id: str) -> WritingStats:
        """获取书籍写作统计"""
        if book_id not in self._writing:
            # 模拟数据
            stats = WritingStats(
                book_id=book_id,
                total_chapters=50,
                total_words=150000,
                avg_words_per_chapter=3000.0,
                avg_write_time_minutes=45.0,
                words_per_minute=66.7,
                total_revision_count=12,
                total_write_sessions=80,
                words_trend=0.15,
                speed_trend=0.08,
                chapter_length_distribution={
                    "2000-2500": 5,
                    "2500-3000": 25,
                    "3000-3500": 15,
                    "3500+": 5,
                },
            )

            # 生成30天模拟数据
            base = datetime.now() - timedelta(days=30)
            for i in range(30):
                day = base + timedelta(days=i)
                key = day.strftime("%Y-%m-%d")
                # 有些天没写作
                if i % 3 != 0:
                    stats.daily_words[key] = 2000 + (i * 100) % 3000
                    stats.daily_chapters[key] = 1

            # 时段分布
            stats.hour_distribution = {
                8: 5,
                9: 12,
                10: 8,
                14: 10,
                15: 8,
                16: 3,
                20: 15,
                21: 12,
                22: 8,
                23: 3,
            }

            self._writing[book_id] = stats

        return self._writing[book_id]

    def writing_streak(self, book_id: str) -> int:
        """计算连续写作天数"""
        stats = self.writing_stats(book_id)
        dates = sorted(stats.daily_words.keys(), reverse=True)

        streak = 0
        check = datetime.now()
        for _i in range(len(dates)):
            if check.strftime("%Y-%m-%d") in dates:
                streak += 1
                check -= timedelta(days=1)
            else:
                break
        return streak

    # ── 收益分析 ──────────────────────────────────

    def revenue_analytics(self, user_id: str) -> RevenueAnalytics:
        """获收益分析"""
        if user_id not in self._revenue:
            rev = RevenueAnalytics(
                user_id=user_id,
                total_revenue=1580.50,
                subscriptions=600.0,
                tips=480.50,
                paid_chapters=500.0,
                projected_monthly=2200.0,
                growth_rate=0.12,
            )

            # 30天模拟
            base = datetime.now() - timedelta(days=30)
            for i in range(30):
                day = base + timedelta(days=i)
                key = day.strftime("%Y-%m-%d")
                rev.daily_revenue[key] = 30.0 + (i * 2.5) % 40

            # 6月
            base = datetime.now() - timedelta(days=180)
            for i in range(6):
                month = base + timedelta(days=i * 30)
                key = month.strftime("%Y-%m")
                rev.monthly_revenue[key] = 800.0 + (i * 150)

            self._revenue[user_id] = rev

        return self._revenue[user_id]

    # ── 读者分析 ──────────────────────────────────

    def reader_analytics(self, book_id: str) -> ReaderAnalytics:
        """获取读者分析"""
        if book_id not in self._readers:
            readers = ReaderAnalytics(
                book_id=book_id,
                total_reads=25000,
                unique_readers=8200,
                avg_read_time_seconds=420.0,
                completion_rate=0.68,
                retention_day7=0.55,
                retention_day30=0.32,
                bounce_rate=0.15,
                total_comments=340,
                total_likes=2800,
                total_shares=450,
                source_distribution={
                    "起点": 4000,
                    "番茄": 2500,
                    "搜索": 800,
                    "推荐": 500,
                    "其他": 400,
                },
            )

            # 30天
            base = datetime.now() - timedelta(days=30)
            for i in range(30):
                day = base + timedelta(days=i)
                key = day.strftime("%Y-%m-%d")
                readers.daily_reads[key] = 500 + (i * 50) % 400
                readers.daily_new_readers[key] = 20 + (i * 3) % 15

            self._readers[book_id] = readers

        return self._readers[book_id]

    # ── 模型使用 ──────────────────────────────────

    def model_usage(self) -> ModelUsageStats:
        """获取模型使用统计"""
        if not self._model_usage.by_model:
            self._model_usage = ModelUsageStats(
                total_calls=5800,
                total_input_tokens=12_500_000,
                total_output_tokens=8_200_000,
                total_cost_cny=165.80,
                avg_latency_ms=320.0,
                cache_hit_rate=0.35,
                by_model={
                    "deepseek-v3": {
                        "calls": 3200,
                        "input_tokens": 7_000_000,
                        "output_tokens": 4_500_000,
                        "cost": 85.0,
                    },
                    "claude-sonnet": {
                        "calls": 1800,
                        "input_tokens": 4_000_000,
                        "output_tokens": 2_800_000,
                        "cost": 60.0,
                    },
                    "qwen3:14b": {
                        "calls": 800,
                        "input_tokens": 1_500_000,
                        "output_tokens": 900_000,
                        "cost": 20.80,
                    },
                },
                by_function={
                    "writing": {"calls": 2500, "tokens": 6_000_000, "cost": 70.0},
                    "audit": {"calls": 1200, "tokens": 4_500_000, "cost": 35.0},
                    "revise": {"calls": 800, "tokens": 3_500_000, "cost": 28.0},
                    "reflect": {"calls": 500, "tokens": 2_000_000, "cost": 15.0},
                    "other": {"calls": 800, "tokens": 4_700_000, "cost": 17.80},
                },
            )
        return self._model_usage

    # ── 质量趋势 ──────────────────────────────────

    def quality_trend(self, book_id: str) -> QualityTrend:
        """获取质量趋势"""
        if book_id not in self._quality:
            trend = QualityTrend(
                book_id=book_id,
                avg_audit_score=82.5,
                gate_pass_rate=0.78,
                revision_rate=0.22,
                icu_trigger_rate=0.05,
                score_trend=0.08,
                dimension_scores={
                    "角色塑造": 85.0,
                    "情节推进": 80.0,
                    "结构完整": 82.0,
                    "文风一致": 88.0,
                    "读者爽感": 78.0,
                    "AI痕迹": 90.0,
                },
            )

            # 12章分数模拟
            for ch in range(1, 50):
                trend.chapter_scores[ch] = 75.0 + ch * 0.2 + (hash(str(ch)) % 15)

            self._quality[book_id] = trend

        return self._quality[book_id]

    # ── 看板汇总 ──────────────────────────────────

    def get_dashboard_summary(self, _user_id: str = "") -> DashboardSummary:
        """获取看板汇总数据"""
        return DashboardSummary(
            books_count=3,
            total_words_written=450000,
            total_revenue=1580.50,
            active_readers=8200,
            model_cost_today=5.50,
            avg_quality_score=82.5,
            current_streak_days=5,
        )

    # ── 图表数据生成 ───────────────────────────────

    def chart_daily_writing(self, book_id: str, days: int = 30) -> dict[str, Any]:
        """生成日写作量图表数据 (ECharts 格式)"""
        stats = self.writing_stats(book_id)
        dates = sorted(stats.daily_words.keys())
        if days:
            dates = dates[-days:]

        return {
            "title": "每日写作量",
            "xAxis": dates,
            "series": [
                {
                    "name": "字数",
                    "type": "line",
                    "data": [stats.daily_words.get(d, 0) for d in dates],
                    "smooth": True,
                }
            ],
        }

    def chart_revenue(self, user_id: str) -> dict[str, Any]:
        """生成收益饼图数据"""
        rev = self.revenue_analytics(user_id)
        return {
            "title": "收益构成",
            "series": [
                {
                    "type": "pie",
                    "data": [
                        {"name": "订阅", "value": rev.subscriptions},
                        {"name": "打赏", "value": rev.tips},
                        {"name": "付费章节", "value": rev.paid_chapters},
                    ],
                }
            ],
        }

    def chart_readers(self, book_id: str) -> dict[str, Any]:
        """生成读者趋势图"""
        readers = self.reader_analytics(book_id)
        dates = sorted(readers.daily_reads.keys())[-30:]

        return {
            "title": "读者趋势",
            "xAxis": dates,
            "series": [
                {
                    "name": "阅读量",
                    "type": "line",
                    "data": [readers.daily_reads.get(d, 0) for d in dates],
                },
                {
                    "name": "新读者",
                    "type": "bar",
                    "data": [readers.daily_new_readers.get(d, 0) for d in dates],
                },
            ],
        }

    def chart_model_cost(self) -> dict[str, Any]:
        """生成模型成本趋势图"""
        usage = self.model_usage()

        return {
            "title": "模型成本分布",
            "series": [
                {
                    "type": "treemap",
                    "data": [{"name": m, "value": d["cost"]} for m, d in usage.by_model.items()],
                }
            ],
        }

    def chart_quality_radar(self, book_id: str) -> dict[str, Any]:
        """生成质量雷达图"""
        trend = self.quality_trend(book_id)
        return {
            "title": "质量维度雷达",
            "indicator": [{"name": k, "max": 100} for k in trend.dimension_scores],
            "series": [
                {
                    "type": "radar",
                    "data": [
                        {
                            "value": list(trend.dimension_scores.values()),
                            "name": book_id,
                        }
                    ],
                }
            ],
        }

    # ── 导出 ──────────────────────────────────────

    def export_report(
        self,
        book_id: str,
        fmt: ExportFormat = ExportFormat.JSON,
    ) -> str:
        """导出分析报告

        Returns:
            报告字符串（文件路径或内容）
        """
        writing = self.writing_stats(book_id)
        quality = self.quality_trend(book_id)
        readers = self.reader_analytics(book_id)
        model_usage = self.model_usage()

        data = {
            "report": {
                "book_id": book_id,
                "generated_at": datetime.now().isoformat(),
                "version": "0.4.0",
            },
            "writing": {
                "total_chapters": writing.total_chapters,
                "total_words": writing.total_words,
                "avg_words_per_chapter": writing.avg_words_per_chapter,
                "words_per_minute": writing.words_per_minute,
                "streak_days": self.writing_streak(book_id),
            },
            "quality": {
                "avg_score": quality.avg_audit_score,
                "gate_pass_rate": quality.gate_pass_rate,
                "revision_rate": quality.revision_rate,
                "dimensions": quality.dimension_scores,
            },
            "readers": {
                "total_reads": readers.total_reads,
                "unique_readers": readers.unique_readers,
                "completion_rate": readers.completion_rate,
                "retention_day7": readers.retention_day7,
            },
            "model_usage": {
                "total_calls": model_usage.total_calls,
                "total_cost": model_usage.total_cost_cny,
                "cache_hit_rate": model_usage.cache_hit_rate,
            },
        }

        if fmt == ExportFormat.JSON:
            return json.dumps(data, ensure_ascii=False, indent=2)

        if fmt == ExportFormat.CSV:
            lines = ["指标,值"]
            for section, items in data.items():
                if section == "report":
                    continue
                if isinstance(items, dict):
                    for k, v in items.items():
                        if not isinstance(v, dict):
                            lines.append(f"{section}.{k},{v}")
            return "\n".join(lines)

        if fmt == ExportFormat.HTML:
            return self._render_html_report(data)

        if fmt == ExportFormat.MARKDOWN:
            return self._render_markdown_report(data)

        return json.dumps(data, ensure_ascii=False, indent=2)

    def _render_html_report(self, data: dict) -> str:
        """渲染 HTML 报告"""
        writing = data["writing"]
        quality = data["quality"]
        readers = data["readers"]
        model = data["model_usage"]
        report = data["report"]

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8">
<title>昆仑数据分析报告 — {report["book_id"]}</title>
<style>
body{{font-family:sans-serif;max-width:800px;margin:0 auto;padding:20px;color:#333}}
h1{{color:#1a1a2e}} .card{{background:#f8f9fa;border-radius:8px;padding:16px;margin:12px 0}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
.stat{{text-align:center;padding:12px;background:#fff;border-radius:6px}}
.stat .value{{font-size:24px;font-weight:bold;color:#e94560}}
.stat .label{{font-size:12px;color:#666}}
table{{width:100%;border-collapse:collapse}}
td,th{{padding:8px 12px;border-bottom:1px solid #ddd;text-align:left}}
.progress{{height:8px;background:#e0e0e0;border-radius:4px;margin-top:4px}}
.progress-bar{{height:100%;background:#0f3460;border-radius:4px}}
</style></head><body>
<h1>昆仑数据分析报告</h1>
<p>书籍: {report["book_id"]} | 生成时间: {report["generated_at"]}</p>
<div class="stats">
<div class="stat"><div class="value">{writing["total_words"]:,}</div>
<div class="label">总字数</div></div>
<div class="stat"><div class="value">{writing["total_chapters"]}</div>
<div class="label">章节数</div></div>
<div class="stat"><div class="value">{writing["streak_days"]}</div>
<div class="label">连续写作天数</div></div>
</div>
<div class="card"><h2>质量分析</h2>
<p>平均审计分: {quality["avg_score"]:.1f} | 门禁通过率: {quality["gate_pass_rate"]:.0%}</p>
<div class="progress"><div class="progress-bar" style="width:{quality["avg_score"]}%"></div></div>
</div>
<div class="card"><h2>读者数据</h2>
<p>总阅读: {readers["total_reads"]:,} | 独立读者: {readers["unique_readers"]:,}</p>
<p>读完率: {readers["completion_rate"]:.0%} | 7日留存: {readers["retention_day7"]:.0%}</p>
</div>
<div class="card"><h2>模型使用</h2>
<p>总调用: {model["total_calls"]:,} | 总成本: ^${model["total_cost"]:.2f}</p>
<p>缓存命中率: {model["cache_hit_rate"]:.0%}</p>
</div>
</body></html>"""

    def _render_markdown_report(self, data: dict) -> str:
        """渲染 Markdown 报告"""
        writing = data["writing"]
        quality = data["quality"]
        readers = data["readers"]
        model = data["model_usage"]
        report = data["report"]

        return f"""# 昆仑数据分析报告

**书籍**: {report["book_id"]}
**生成时间**: {report["generated_at"]}

## 写作统计
| 指标 | 值 |
|------|-----|
| 总字数 | {writing["total_words"]:,} |
| 总章节 | {writing["total_chapters"]} |
| 平均每章字数 | {writing["avg_words_per_chapter"]:.0f} |
| 写作速度 | {writing["words_per_minute"]:.0f} 字/分钟 |
| 连续写作天数 | {writing["streak_days"]} |

## 质量分析
- 平均审计分: **{quality["avg_score"]:.1f}**
- 门禁通过率: **{quality["gate_pass_rate"]:.0%}**
- 修订率: **{quality["revision_rate"]:.0%}**

## 读者数据
- 总阅读量: {readers["total_reads"]:,}
- 独立读者: {readers["unique_readers"]:,}
- 读完率: {readers["completion_rate"]:.0%}
- 7日留存: {readers["retention_day7"]:.0%}

## 模型使用
- 总调用: {model["total_calls"]:,}
- 总成本: ^{model["total_cost"]:.2f}
- 缓存命中率: {model["cache_hit_rate"]:.0%}
"""

    # ── 统计 ──────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        return {
            "tracked_books": len(self._writing),
            "tracked_users": len(self._revenue),
            "total_words_tracked": sum(w.total_words for w in self._writing.values()),
            "model_calls_tracked": self._model_usage.total_calls,
        }


# 全局单例
analytics_engine = AnalyticsEngine()
