"""
昆仑创作引擎 — 仪表盘引擎 (真实实现)

替代占位实现，提供全书级数据可视化和概览。

核心能力:
  1. 全书概览 — 字数/章节/质量/进展一站式视图
  2. 质量雷达图数据 — 8 维度雷达图 JSON
  3. 进度追踪 — 目标 vs 实际进度
  4. 快照功能 — 保存某个时刻的完整仪表盘状态
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from kunlun.config import settings

# ══════════════════════════════════════════════════════
# 数据类型
# ══════════════════════════════════════════════════════


@dataclass
class WordStats:
    """字数统计"""

    total_words: int = 0
    chapter_count: int = 0
    avg_words_per_chapter: int = 0
    min_chapter_words: int = 0
    max_chapter_words: int = 0
    daily_output_avg: int = 0  # 日均产出
    weekly_output: int = 0  # 本周产出
    total_goal: int = 0  # 总目标
    progress_pct: float = 0.0  # 完成度百分比
    estimated_days_to_finish: int = 0


@dataclass
class QualityRadar:
    """质量雷达图数据"""

    labels: list[str] = field(default_factory=list)  # 维度名
    scores: list[float] = field(default_factory=list)  # 当前分值
    avg_scores: list[float] = field(default_factory=list)  # 平均分值
    max_scores: list[float] = field(default_factory=list)  # 历史最高


@dataclass
class DashboardSnapshot:
    """仪表盘快照 — 可序列化的完整状态"""

    book_id: str
    captured_at: float
    word_stats: WordStats = field(default_factory=WordStats)
    quality_radar: QualityRadar = field(default_factory=QualityRadar)
    chapter_list: list[dict] = field(default_factory=list)
    recent_issues: list[str] = field(default_factory=list)
    overall_health: str = "unknown"  # "excellent" | "good" | "needs_attention" | "critical"


# ══════════════════════════════════════════════════════
# 仪表盘引擎
# ══════════════════════════════════════════════════════


class DashboardEngine:
    """仪表盘引擎 — 汇集全书数据生成统一视图

    数据来源:
      - 质量引擎 (QualityEvaluator/QualityTrendTracker)
      - AIGC 检测 (AIGCDetector/AIGCTrendTracker)
      - 追读力 (RetentionPredictor)
      - 连续性 (ContinuityEngine)
      - 文件系统 (章节文件)

    用法:
        dash = DashboardEngine(book_id="my_book")
        overview = dash.generate_overview()
        radar = dash.get_quality_radar()
        snapshot = dash.take_snapshot()
    """

    def __init__(self, book_id: str):
        self.book_id = book_id
        self.dash_dir = settings.DATA_DIR / "dashboard" / book_id
        self.dash_dir.mkdir(parents=True, exist_ok=True)
        self.story_dir = settings.DATA_DIR / "story" / book_id

    # ── 全书概览 ──────────────────────────────────────

    def generate_overview(self) -> dict[str, Any]:
        """生成全书概览数据"""
        overview: dict[str, Any] = {
            "book_id": self.book_id,
            "generated_at": time.time(),
            "word_stats": self._build_word_stats(),
            "quality_summary": self._build_quality_summary(),
            "aigc_summary": self._build_aigc_summary(),
            "retention_summary": self._build_retention_summary(),
            "continuity_summary": self._build_continuity_summary(),
            "overall_health": "unknown",
        }

        # 综合健康度
        scores = []
        if overview["quality_summary"].get("avg_score"):
            scores.append(overview["quality_summary"]["avg_score"])
        aigc = overview["aigc_summary"].get("avg_human_score", 0)
        if aigc:
            scores.append(aigc)

        if scores:
            health_score = sum(scores) / len(scores)
            if health_score >= 0.85:
                overview["overall_health"] = "excellent"
            elif health_score >= 0.70:
                overview["overall_health"] = "good"
            elif health_score >= 0.50:
                overview["overall_health"] = "needs_attention"
            else:
                overview["overall_health"] = "critical"

        return overview

    def _build_word_stats(self) -> dict[str, Any]:
        """构建字数统计"""
        # 扫描章节文件
        chapters: dict[int, int] = {}
        if self.story_dir.exists():
            import re as _re

            pattern = _re.compile(r"ch(?:apter)?[_-]?(\d+)", _re.IGNORECASE)
            for f in sorted(self.story_dir.glob("*.md")):
                match = pattern.search(f.stem)
                if match:
                    ch = int(match.group(1))
                    text = f.read_text(encoding="utf-8")
                    chapters[ch] = len(text)

        word_counts = list(chapters.values())
        return {
            "chapter_count": len(word_counts),
            "total_words": sum(word_counts),
            "avg_words_per_chapter": int(sum(word_counts) / max(len(word_counts), 1)),
            "min_chapter_words": min(word_counts) if word_counts else 0,
            "max_chapter_words": max(word_counts) if word_counts else 0,
            "chapters": [{"chapter": ch, "words": wc} for ch, wc in sorted(chapters.items())],
        }

    def _build_quality_summary(self) -> dict[str, Any]:
        """构建质量摘要 (从 QualityTrendTracker)"""
        try:
            from kunlun.quality.engine import get_quality_tracker

            tracker = get_quality_tracker(self.book_id)
            stats = tracker.get_statistics()
            trend = tracker.get_trend(last_n=20)
            return {
                **stats,
                "trend": trend.get("trend", "stable"),
                "trend_slope": trend.get("slope", 0),
            }
        except Exception as e:
            logger.debug(f"[Dashboard] 质量摘要获取失败: {e}")
            return {"avg_score": 0, "total_chapters": 0}

    def _build_aigc_summary(self) -> dict[str, Any]:
        """构建 AIGC 摘要"""
        try:
            from kunlun.aigc_detect import get_tracker as get_aigc_tracker

            tracker = get_aigc_tracker(self.book_id)
            trend = tracker.get_trend()
            return {
                "avg_human_score": trend.get("avg_human_score", 0),
                "trend": trend.get("trend", "stable"),
            }
        except Exception as e:
            logger.debug(f"[Dashboard] AIGC摘要获取失败: {e}")
            return {"avg_human_score": 0, "trend": "unknown"}

    def _build_retention_summary(self) -> dict[str, Any]:
        """构建追读力摘要"""
        return {"available": False, "note": "运行 /retention/analyze 获取"}

    def _build_continuity_summary(self) -> dict[str, Any]:
        """构建连续性摘要"""
        try:
            from kunlun.continuity import get_continuity_engine

            engine = get_continuity_engine(self.book_id)
            latest = engine.snapshots.get_latest_snapshot()
            return {
                "has_snapshot": latest is not None,
                "latest_snapshot": latest.chapter_number if latest else 0,
            }
        except Exception as e:
            logger.debug(f"[Dashboard] 连续性摘要获取失败: {e}")
            return {"has_snapshot": False}

    # ── 质量雷达图 ────────────────────────────────────

    def get_quality_radar(self) -> dict[str, Any]:
        """获取质量雷达图数据"""
        try:
            from kunlun.quality.engine import QualityDimension, get_quality_tracker

            tracker = get_quality_tracker(self.book_id)

            # 获取最新章节的各维度评分
            latest_ch = max(tracker._history.keys()) if tracker._history else 0
            radar: dict[str, Any] = {
                "dimensions": [],
                "latest_chapter": latest_ch,
            }

            for dim in QualityDimension:
                trend = tracker.get_dimension_trend(dim, last_n=20)
                scores = [t["score"] for t in trend]
                radar["dimensions"].append(
                    {
                        "name": dim.value,
                        "label": {
                            "word_count": "字数合规",
                            "dialogue_density": "对话密度",
                            "action_density": "动作密度",
                            "description_richness": "描写丰富度",
                            "sentence_variety": "句式多样性",
                            "pacing": "节奏控制",
                            "info_density": "信息密度",
                            "chapter_structure": "章节完整性",
                        }.get(dim.value, dim.value),
                        "current": scores[-1] if scores else 0,
                        "avg": round(sum(scores) / max(len(scores), 1), 2) if scores else 0,
                        "max": max(scores) if scores else 0,
                    }
                )

            return radar
        except Exception as e:
            logger.debug(f"[Dashboard] 质量雷达图获取失败: {e}")
            return {"dimensions": [], "latest_chapter": 0}

    # ── 进度追踪 ──────────────────────────────────────

    def get_progress(
        self, target_chapters: int = 100, target_words: int = 500000
    ) -> dict[str, Any]:
        """获取进度信息"""
        word_stats = self._build_word_stats()
        current_words = word_stats["total_words"]
        current_chapters = word_stats["chapter_count"]

        return {
            "chapters": {
                "current": current_chapters,
                "target": target_chapters,
                "progress_pct": round(current_chapters / max(target_chapters, 1) * 100, 1),
                "remaining": max(0, target_chapters - current_chapters),
            },
            "words": {
                "current": current_words,
                "target": target_words,
                "progress_pct": round(current_words / max(target_words, 1) * 100, 1),
                "remaining": max(0, target_words - current_words),
            },
            "avg_words_per_chapter": word_stats["avg_words_per_chapter"],
            "estimated_chapters_remaining": 0,
        }

    # ── 快照 ──────────────────────────────────────────

    def take_snapshot(self) -> DashboardSnapshot:
        """拍摄当前仪表盘快照"""
        snapshot = DashboardSnapshot(
            book_id=self.book_id,
            captured_at=time.time(),
            word_stats=WordStats(**self._build_word_stats()),
            overall_health=self.generate_overview().get("overall_health", "unknown"),
        )
        self._save_snapshot(snapshot)
        return snapshot

    def _save_snapshot(self, snapshot: DashboardSnapshot):
        """保存快照"""
        path = self.dash_dir / f"snapshot_{int(snapshot.captured_at)}.json"
        data = {
            "book_id": snapshot.book_id,
            "captured_at": snapshot.captured_at,
            "word_stats": {
                "total_words": snapshot.word_stats.total_words,
                "chapter_count": snapshot.word_stats.chapter_count,
                "avg_words_per_chapter": snapshot.word_stats.avg_words_per_chapter,
            },
            "overall_health": snapshot.overall_health,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_snapshots(self) -> list[dict[str, Any]]:
        """列出所有快照"""
        snapshots: list[dict] = []
        for f in sorted(self.dash_dir.glob("snapshot_*.json"), reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                snapshots.append(data)
            except Exception as e:
                logger.debug(f"快照数据加载失败: {f.name}: {e}")
        return snapshots[:20]  # 最多返回最近 20 个

    # ── 导出 ──────────────────────────────────────────

    def export_summary(self) -> dict[str, Any]:
        """导出仪表盘摘要 (供前端消费)"""
        overview = self.generate_overview()
        radar = self.get_quality_radar()
        progress = self.get_progress()

        return {
            "book_id": self.book_id,
            "generated_at": time.time(),
            "overall_health": overview["overall_health"],
            "word_stats": overview["word_stats"],
            "quality": overview["quality_summary"],
            "aigc": overview["aigc_summary"],
            "quality_radar": radar,
            "progress": progress,
        }


# ══════════════════════════════════════════════════════
# 工厂函数
# ══════════════════════════════════════════════════════

_dashboards: dict[str, DashboardEngine] = {}


def get_dashboard(book_id: str) -> DashboardEngine:
    """获取仪表盘引擎实例"""
    if book_id not in _dashboards:
        _dashboards[book_id] = DashboardEngine(book_id)
    return _dashboards[book_id]


__all__ = [
    "DashboardEngine",
    "DashboardSnapshot",
    "QualityRadar",
    "WordStats",
    "get_dashboard",
]
