"""
pleasure 爽点引擎 — 网文爽点识别、节奏控制、疲劳度管理

核心能力:
1. 12类爽点模式识别（打脸/升级/获得/碾压/揭秘/暧昧/复仇/守护/装逼/反转/感动/热血）
2. 爽点密度与间隔分析（黄金3章节奏）
3. 爽点类型疲劳度追踪（同类型爽点衰减曲线）
4. 零LLM纯规则实现（基于关键词+句式+结构模式匹配）
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from loguru import logger

from kunlun.core.extension_base import BaseExtensionModule
from kunlun.pleasure.arc_planner import (
    ArcPhase,  # re-export
    PleasureArcPlan,
    PleasureArcPlanner,
)

# Re-export from submodules for backward compatibility
from kunlun.pleasure.detector import PleasureDetector
from kunlun.pleasure.fatigue import FatigueTracker, PleasureFatigueDetector
from kunlun.pleasure.types import (
    PLEASURE_TYPE_CONFIGS,
    FatigueLevel,
    PleasureEvent,
    PleasureReport,
    PleasureType,  # re-export
    PleasureTypeConfig,  # re-export
    TypeFatigue,
    get_pleasure_config,
)

__all__ = [
    "PLEASURE_TYPE_CONFIGS",
    "ArcPhase",
    "FatigueLevel",
    "FatigueTracker",
    "PleasureArcPlan",
    "PleasureArcPlanner",
    "PleasureDetector",
    "PleasureEngine",
    "PleasureEvent",
    "PleasureFatigueDetector",
    "PleasureReport",
    "PleasureType",
    "PleasureTypeConfig",
    "TypeFatigue",
    "get_pleasure_config",
]

# ============================================================================
# 爽点引擎（主入口）
# ============================================================================


class PleasureEngine(BaseExtensionModule):
    """爽点引擎 — 识别爽点、管理节奏、控制疲劳、规划弧线"""

    SUBDIR = "pleasure"

    def __init__(self, book_id: str = ""):
        super().__init__(book_id)
        self._detector = PleasureDetector()
        self._fatigue_tracker = FatigueTracker()
        self._fatigue_detector = PleasureFatigueDetector()
        self._arc_planner: PleasureArcPlanner | None = None
        self._current_plan: PleasureArcPlan | None = None
        self._global_history: list[PleasureEvent] = []
        self._chapter_history: list[dict[str, Any]] = []

    def init_arc(self, total_chapters: int, genre: str = "") -> PleasureArcPlan:
        """初始化爽点弧线规划"""
        if genre:
            self._current_plan = PleasureArcPlanner.plan_for_genre(
                self.book_id, total_chapters, genre
            )
        else:
            self._current_plan = PleasureArcPlanner.plan_default_arc(self.book_id, total_chapters)
        self._arc_planner = PleasureArcPlanner()
        logger.info(
            f"爽点弧线已初始化: {len(self._current_plan.phases)}个阶段, 总{total_chapters}章"
        )
        return self._current_plan

    def get_chapter_guidance(self, chapter_number: int, word_count: int = 3000) -> dict[str, Any]:
        """获取指定章节的爽点写作指导"""
        if not self._current_plan:
            return {"guidance": "未初始化弧线，请先调用 init_arc()"}
        return PleasureArcPlanner.generate_chapter_guidance(
            self._current_plan, chapter_number, word_count
        )

    def check_fatigue(self) -> dict[str, Any]:
        """检查当前全局爽点疲劳状态"""
        return self._fatigue_detector.feed(self._global_history)

    def get_variety_suggestions(self, genre: str = "") -> list[str]:
        """获取爽点多样性建议"""
        return self._fatigue_detector.get_variety_suggestions(genre)

    def analyze_chapter(
        self,
        chapter_text: str,
        chapter_id: str = "",
        global_events: list[PleasureEvent] | None = None,
    ) -> PleasureReport:
        """分析单章爽点

        Args:
            chapter_text: 章节全文
            chapter_id: 章节ID
            global_events: 全局历史爽点事件（用于跨章疲劳追踪）

        Returns:
            PleasureReport: 爽点分析报告
        """
        report = PleasureReport(book_id=self.book_id, chapter_id=chapter_id)

        # 1. 检测爽点
        events = self._detector.detect_events(chapter_text, chapter_id)
        report.events = events
        report.total_events = len(events)

        # 2. 密度计算
        total_chars = len(chapter_text.replace("\n", "").replace(" ", ""))
        report.density_per_1000 = (len(events) / max(total_chars, 1)) * 1000

        # 3. 类型分布
        type_counts: Counter = Counter()
        for e in events:
            type_counts[e.event_type.value] += 1
        report.type_distribution = dict(type_counts.most_common())

        # 4. 疲劳度追踪
        if global_events is not None:
            self._fatigue_tracker.reset()
            self._fatigue_tracker.feed_events(global_events)
        report.fatigue_map = self._fatigue_tracker.feed_events(events)

        # 5. 节奏评分
        report.rhythm_score = self._calculate_rhythm(events, total_chars)

        # 6. 黄金三章检测（前三章爽点密度是否达标）
        report.golden_3_ok = self._check_golden_three(report, global_events)

        # 7. 建议
        report.suggestions = self._generate_suggestions(report)

        # 更新全局历史
        self._global_history.extend(events)
        self._fatigue_detector.feed(events)

        # 记录章节历史
        self._chapter_history.append(
            {
                "chapter_id": chapter_id,
                "total_events": len(events),
                "density": report.density_per_1000,
                "type_distribution": report.type_distribution,
            }
        )

        logger.info(report.summary())
        return report

    def _calculate_rhythm(self, events: list[PleasureEvent], total_chars: int) -> float:
        """计算节奏评分"""
        if not events:
            return 50  # 无爽点：中性分

        score = 60.0

        # 密度评分
        density = (len(events) / max(total_chars, 1)) * 1000
        if 2 <= density <= 5:
            score += 10
        elif density < 0.5:
            score -= 15
        elif density > 8:
            score -= 5  # 过于密集

        # 间隔均匀度
        if len(events) >= 3:
            intervals = [events[i].position - events[i - 1].position for i in range(1, len(events))]
            avg_interval = sum(intervals) / len(intervals)
            if avg_interval > 0:
                cv = sum(abs(i - avg_interval) for i in intervals) / (len(intervals) * avg_interval)
                if cv < 0.5:
                    score += 8  # 非常均匀
                elif cv < 1.0:
                    score += 3
                elif cv > 2.0:
                    score -= 5  # 忽密忽疏

        # 类型多样性
        unique_types = len({e.event_type for e in events})
        if unique_types >= 5:
            score += 8
        elif unique_types >= 3:
            score += 3
        else:
            score -= 3

        return max(0, min(100, score))

    def _check_golden_three(
        self,
        current_report: PleasureReport,
        global_events: list[PleasureEvent] | None,
    ) -> bool:
        """检测黄金三章爽点密度是否达标（每3000字至少1个爽点）"""
        # 简化版：基于当前章密度判断
        if current_report.density_per_1000 >= 0.33:  # ~每3000字1个
            return True

        return bool(global_events and len(global_events) >= 3)

    def _generate_suggestions(self, report: PleasureReport) -> list[str]:
        """生成爽点优化建议"""
        suggestions: list[str] = []

        # 密度建议
        if report.density_per_1000 < 0.5:
            suggestions.append("爽点密度过低（<0.5/千字），建议每2000-3000字安排一个爽点")
        elif report.density_per_1000 > 6:
            suggestions.append("爽点过于密集（>6/千字），读者可能产生审美疲劳")

        # 类型建议
        type_dist = report.type_distribution
        if len(type_dist) <= 2 and report.total_events >= 3:
            suggestions.append("爽点类型单一，建议穿插不同类型（如打脸+升级+揭秘）交替使用")

        # 疲劳建议
        for ptype, fatigue in report.fatigue_map.items():
            if fatigue.fatigue_level in (FatigueLevel.TIRING, FatigueLevel.EXHAUSTED):
                suggestions.append(
                    f"'{ptype}'类爽点已出现{fatigue.total_occurrences}次，"
                    f"当前衰减{fatigue.decay_factor:.0%}，建议替换为其他类型"
                )

        # 新增: 疲劳检测器建议
        fatigue_report = self._fatigue_detector.feed(report.events)
        if fatigue_report.get("fatigue_detected"):
            suggestions.extend(fatigue_report.get("suggestions", [])[:2])

        # 新增: 弧线指导
        if self._current_plan and report.chapter_id:
            try:
                ch_num = int(report.chapter_id) if report.chapter_id.isdigit() else 0
            except (ValueError, TypeError):
                ch_num = 0
            if ch_num > 0:
                guidance = PleasureArcPlanner.generate_chapter_guidance(self._current_plan, ch_num)
                target = guidance.get("target_event_count", 0)
                if report.total_events < target * 0.5:
                    suggestions.append(
                        f"当前弧线阶段「{guidance.get('phase', '')}」"
                        f"需要至少{target}个爽点，"
                        f"目前仅{report.total_events}个，"
                        f"建议补充{guidance.get('recommended_types', [])}"
                    )

        # 黄金三章
        if not report.golden_3_ok:
            suggestions.append("前三章爽点密度不足，建议在开头3000字内安排1-2个强爽点抓住读者")

        # 新增: 类型间隔检查
        for event_type, config in PLEASURE_TYPE_CONFIGS.items():
            type_events = [e for e in report.events if e.event_type == event_type]
            if len(type_events) >= 2:
                for i in range(1, len(type_events)):
                    gap = type_events[i].position - type_events[i - 1].position
                    if gap < config.min_interval:
                        suggestions.append(
                            f"'{config.name_cn}'类爽点间隔仅{gap}字（建议≥{config.min_interval}字），爽感可能打折"
                        )
                        break

        return suggestions

    def get_fatigue_map(self) -> dict[str, TypeFatigue]:
        """获取当前所有类型的疲劳度"""
        return self._fatigue_tracker.feed_events([])

    def reset_fatigue(self) -> None:
        """重置疲劳度追踪"""
        self._fatigue_tracker.reset()
        self._fatigue_detector.reset()
        self._global_history.clear()
        self._chapter_history.clear()

    def get_global_stats(self) -> dict[str, Any]:
        """获取全局爽点统计"""
        type_counts: Counter = Counter()
        for e in self._global_history:
            type_counts[e.event_type.value] += 1

        return {
            "total_events": len(self._global_history),
            "type_distribution": dict(type_counts.most_common()),
            "avg_intensity": (
                sum(e.intensity for e in self._global_history) / max(len(self._global_history), 1)
            ),
            "chapter_count": len(self._chapter_history),
        }

    def get_arc_plan(self) -> dict[str, Any] | None:
        """获取当前弧线规划"""
        if not self._current_plan:
            return None
        return {
            "total_chapters": self._current_plan.total_chapters,
            "chapters_per_act": self._current_plan.chapters_per_act,
            "phases": [
                {
                    "name": p.name,
                    "range": list(p.chapter_range),
                    "density": p.target_density,
                    "primary_types": [get_pleasure_config(t).name_cn for t in p.primary_types],
                }
                for p in self._current_plan.phases
            ],
            "notes": self._current_plan.notes,
        }

    def detect_events(self, text: str, chapter: str = "") -> dict[str, Any]:
        """检测文本中的爽点事件（兼容接口，内部调用 analyze_chapter）"""
        try:
            result = self.analyze_chapter(text, chapter_number=int(chapter) if chapter else 0)
            return {
                "events": getattr(result, "events", []),
                "rhythm": getattr(result, "rhythm_score", 0.0),
                "chapter": chapter,
            }
        except Exception as e:
            logger.debug(f"PleasureEngine.detect_events 跳过: {e}")
            return {"events": [], "rhythm": 0.0, "chapter": chapter}



# ============================================================================
# 工厂函数
# ============================================================================


_engines: dict[str, PleasureEngine] = {}


def get_pleasure_engine(book_id: str = "") -> PleasureEngine:
    """获取爽点引擎实例（按book_id缓存）"""
    if book_id not in _engines:
        _engines[book_id] = PleasureEngine(book_id=book_id)
    return _engines[book_id]
