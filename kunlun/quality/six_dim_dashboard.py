"""
昆仑创作引擎 — 六维质量仪表盘 (SixDimensionDashboard)

将8维底层审计聚合为6维高层可视化指标：
  1. 节奏 (pacing)     — 情节推进速度、场景切换、段落结构
  2. 爽感 (pleasure)   — 动作密度、冲突强度、对话张力
  3. 人物 (character)  — 角色塑造、对话质量、描写丰富度
  4. 逻辑 (logic)      — 信息密度、结构完整性、因果关系
  5. 文笔 (style)      — 句式变化、描写质量、字数控制
  6. 创新 (innovation) — 信息新颖度、节奏变化、非套路化

85分目标: 每维 >= 0.80，综合 >= 0.85
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kunlun.quality.engine import QualityEvaluator


@dataclass
class DimensionScore:
    """单维度评分"""
    name: str
    name_cn: str
    score: float
    level: str
    weight: float
    sub_dimensions: dict[str, float] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "name_cn": self.name_cn,
            "score": round(self.score, 3),
            "level": self.level,
            "weight": self.weight,
            "sub_dimensions": {k: round(v, 3) for k, v in self.sub_dimensions.items()},
            "issues": self.issues,
            "suggestions": self.suggestions,
        }


@dataclass
class SixDimensionReport:
    """六维质量报告"""
    overall_score: float = 0.0
    overall_level: str = "fair"
    dimensions: dict[str, DimensionScore] = field(default_factory=dict)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    improvement_priority: list[str] = field(default_factory=list)
    target_85: bool = False

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 3),
            "overall_level": self.overall_level,
            "target_85": self.target_85,
            "dimensions": {k: v.to_dict() for k, v in self.dimensions.items()},
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "improvement_priority": self.improvement_priority,
        }

    def radar_data(self) -> dict:
        """雷达图数据（前端可视化用）"""
        return {
            "labels": [v.name_cn for v in self.dimensions.values()],
            "scores": [round(v.score * 100, 1) for v in self.dimensions.values()],
            "target": [85] * len(self.dimensions),
        }


SIX_DIM_WEIGHTS = {
    "pacing": 0.20,
    "pleasure": 0.20,
    "character": 0.15,
    "logic": 0.15,
    "style": 0.15,
    "innovation": 0.15,
}

DIMENSION_MAPPING = {
    "pacing": {
        "name_cn": "节奏",
        "subs": {"pacing": 0.50, "sentence_variety": 0.30, "chapter_structure": 0.20},
    },
    "pleasure": {
        "name_cn": "爽感",
        "subs": {"action_density": 0.60, "dialogue_density": 0.40},
    },
    "character": {
        "name_cn": "人物",
        "subs": {"dialogue_density": 0.50, "description_richness": 0.50},
    },
    "logic": {
        "name_cn": "逻辑",
        "subs": {"info_density": 0.60, "chapter_structure": 0.40},
    },
    "style": {
        "name_cn": "文笔",
        "subs": {"sentence_variety": 0.40, "description_richness": 0.30, "word_count": 0.30},
    },
    "innovation": {
        "name_cn": "创新",
        "subs": {"info_density": 0.50, "pacing": 0.50},
    },
}


def _score_to_level(score: float) -> str:
    if score >= 0.85:
        return "excellent"
    if score >= 0.70:
        return "good"
    if score >= 0.50:
        return "fair"
    return "poor"


class SixDimensionDashboard:
    """六维质量仪表盘 — 将8维审计聚合为6维可视化"""

    _evaluator: QualityEvaluator = QualityEvaluator()

    @classmethod
    def analyze(cls, text: str, chapter: int = 0) -> SixDimensionReport:
        report = SixDimensionReport()
        if len(text) < 50:
            report.overall_level = "文本过短"
            return report

        raw = cls._evaluator.evaluate(text, chapter_number=chapter)
        raw_scores = {k: v.score for k, v in raw.dimension_scores.items()}
        raw_issues = {k: v.issues for k, v in raw.dimension_scores.items()}

        for dim_key, mapping in DIMENSION_MAPPING.items():
            sub_scores = {}
            issues = []
            weighted_score = 0.0
            for sub_key, sub_weight in mapping["subs"].items():
                sub_score = raw_scores.get(sub_key, 0.5)
                sub_scores[sub_key] = sub_score
                weighted_score += sub_score * sub_weight
                if sub_key in raw_issues:
                    issues.extend(raw_issues[sub_key])

            # 创新维度额外惩罚：套路词检测
            if dim_key == "innovation":
                cliche_penalty = _detect_cliche_penalty(text)
                weighted_score = max(0.0, weighted_score - cliche_penalty)
                if cliche_penalty > 0.1:
                    issues.append(f"套路词密度偏高，惩罚{cliche_penalty*100:.0f}分")

            level = _score_to_level(weighted_score)
            dim = DimensionScore(
                name=dim_key,
                name_cn=mapping["name_cn"],
                score=round(weighted_score, 3),
                level=level,
                weight=SIX_DIM_WEIGHTS[dim_key],
                sub_dimensions=sub_scores,
                issues=issues[:5],
                suggestions=_generate_suggestions(dim_key, weighted_score, issues),
            )
            report.dimensions[dim_key] = dim

        report.overall_score = sum(d.score * d.weight for d in report.dimensions.values())
        report.overall_level = _score_to_level(report.overall_score)
        report.target_85 = report.overall_score >= 0.85

        sorted_dims = sorted(report.dimensions.values(), key=lambda d: d.score, reverse=True)
        report.strengths = [
            f"{d.name_cn}({d.score*100:.0f}分): {_strength_comment(d.name)}"
            for d in sorted_dims[:3] if d.score >= 0.70
        ]
        report.weaknesses = [
            f"{d.name_cn}({d.score*100:.0f}分): {_weakness_comment(d.name)}"
            for d in sorted_dims[-3:] if d.score < 0.70
        ]
        report.improvement_priority = [
            d.name_cn for d in sorted(
                report.dimensions.values(), key=lambda d: 0.85 - d.score, reverse=True
            ) if d.score < 0.85
        ][:3]

        return report


CLICHE_WORDS = [
    "微微一怔", "眼中闪过", "缓缓开口", "淡淡说道", "仿佛时间",
    "不由自主", "心中暗道", "嘴角微微", "轻轻摇头", "深深看了",
    "赫然发现", "气势暴涨", "天地变色", "风云际会", "雷霆万钧",
    "不可思议", "难以置信", "原来如此", "恍然大悟", "不出所料",
]


def _detect_cliche_penalty(text: str) -> float:
    """检测套路词密度，返回惩罚分(0-0.3)"""
    if not text:
        return 0.0
    cliche_count = sum(text.count(w) for w in CLICHE_WORDS)
    density = cliche_count / max(len(text) / 100, 1)
    return min(0.3, density * 0.1)


def _generate_suggestions(dim: str, score: float, issues: list[str]) -> list[str]:
    if score >= 0.85:
        return ["表现优秀，保持当前风格"]
    tips = {
        "pacing": ["增加场景切换频率", "使用短句加快节奏", "每500字至少一个情节推进点"],
        "pleasure": ["增加动作描写和冲突场景", "提升对话张力", "每3章一个小爽点"],
        "character": ["增加角色个性化对话", "通过动作展现性格", "给配角设置独立目标"],
        "logic": ["增加世界观设定说明", "确保因果关系清晰", "检查前后设定一致性"],
        "style": ["变化句式长度", "增加感官描写", "控制章节字数2000-4000字"],
        "innovation": ["避免常见套路", "尝试非传统情节展开", "增加独特世界观设定"],
    }
    count = 1 if score >= 0.70 else 2 if score >= 0.50 else 3
    return tips.get(dim, [])[:count]


def _strength_comment(dim: str) -> str:
    comments = {
        "pacing": "节奏把控出色，情节推进流畅",
        "pleasure": "爽感充足，读者体验佳",
        "character": "人物塑造生动，角色鲜明",
        "logic": "逻辑严密，设定自洽",
        "style": "文笔流畅，句式多变",
        "innovation": "富有创意，不落俗套",
    }
    return comments.get(dim, "表现优秀")


def _weakness_comment(dim: str) -> str:
    comments = {
        "pacing": "节奏偏慢或不均匀",
        "pleasure": "爽感不足，冲突偏少",
        "character": "人物塑造单薄",
        "logic": "逻辑有漏洞",
        "style": "文笔单调",
        "innovation": "套路化明显",
    }
    return comments.get(dim, "需要改进")


six_dim_dashboard = SixDimensionDashboard()
