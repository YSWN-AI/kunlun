"""
昆仑创作引擎 — 质量仪表盘 (QualityDashboard)

为 API 路由和 CLI 提供统一入口，封装 QualityEvaluator。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kunlun.quality.engine import QualityEvaluator


@dataclass
class DashboardReport:
    """仪表盘报告 — 前端友好的质量报告格式"""

    quality_rating: str = "一般"
    overall_score: float = 0.0
    ai_score: float = 0.0
    token_budget_usage: float = 0.0
    warnings: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    @property
    def issues_summary(self) -> list[str]:
        """问题摘要（返回前 N 条问题）"""
        return self.issues
    dimensions: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "quality_rating": self.quality_rating,
            "overall_score": self.overall_score,
            "ai_score": self.ai_score,
            "token_budget_usage": self.token_budget_usage,
            "warnings": self.warnings,
            "issues": self.issues,
            "dimensions": self.dimensions,
        }


class QualityDashboard:
    """质量仪表盘 — 静态方法，供路由和测试直接调用"""

    _evaluator: QualityEvaluator = QualityEvaluator()

    @classmethod
    def analyze_chapter(
        cls, text: str, chapter: int = 0, token_usage: float = 0.0
    ) -> DashboardReport:
        """分析章节质量"""
        report = DashboardReport()

        # 短文本边界
        if len(text) < 50:
            report.quality_rating = "文本过短"
            report.warnings.append("文本过短，无法进行评估")
            return report

        # 调用底层评估器
        raw = cls._evaluator.evaluate(text, chapter_number=chapter)

        report.overall_score = raw.overall_score
        report.quality_rating = _level_to_chinese(raw.overall_level)
        report.dimensions = {
            k: {"score": v.score, "level": v.level, "issues": v.issues}
            for k, v in raw.dimension_scores.items()
        }

        # AI风格检测（高AI特征 → 低分，0=强AI, 1=纯人写作）
        report.ai_score = 1.0 - _detect_ai_style(text)

        # Token预算
        report.token_budget_usage = token_usage
        if token_usage > 0.8:
            report.warnings.append(f"Token预算使用率 {token_usage:.0%}，接近上限")

        # 汇总问题
        for dim_name, dim_score in raw.dimension_scores.items():
            for issue in dim_score.issues:
                report.issues.append(f"[{dim_name}] {issue}")

        # 综合告警
        if raw.overall_score < 0.4:
            report.warnings.append("综合质量偏低，建议优化后发布")
        if raw.auto_fixable > 0:
            report.warnings.append(f"检测到 {raw.auto_fixable} 个可自动修复的问题")

        return report

    @classmethod
    def compare_chapters(cls, drafts: dict[int, str]) -> dict[int, DashboardReport]:
        """批量比较章节质量"""
        return {ch: cls.analyze_chapter(text, chapter=ch) for ch, text in drafts.items()}


def _level_to_chinese(level: str) -> str:
    """将英文评级映射为中文"""
    mapping = {
        "excellent": "优秀",
        "good": "良好",
        "fair": "一般",
        "poor": "较差",
    }
    return mapping.get(level, "一般")


def _detect_ai_style(text: str) -> float:
    """检测AI风格特征（0=无AI特征, 1=强AI特征）

    基于常见AI文本特征：
    - 过度使用连接词（首先/其次/最后/然而/因此）
    - 刻板的论证结构
    - 缺乏个人化表达
    """
    ai_markers = [
        "首先",
        "其次",
        "再次",
        "最后",
        "总而言之",
        "综上所述",
        "值得注意的是",
        "需要指出的是",
        "不可否认",
        "毋庸置疑",
        "从这个角度来看",
        "从某种意义上说",
        "换句话说",
    ]
    total_chars = max(len(text), 1)
    marker_count = sum(text.count(m) for m in ai_markers)
    # 归一化：每100字中的AI标记数
    score = min(marker_count * 100 / total_chars * 10, 1.0)
    return round(score, 2)


# 模块级单例，供路由直接 import 使用
quality_dashboard = QualityDashboard()
