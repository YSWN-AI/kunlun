"""
昆仑创作引擎 — 质量评估引擎 (真实实现)

替代占位实现，提供零 LLM 成本的多维质量评分。

核心能力:
  1. 章节级质量评分 — 8 维度独立评分
  2. 全书质量趋势 — 跨章节质量变化追踪
  3. 质量仪表盘数据 — 供 Dashboard 模块消费
  4. 可执行建议 — 每个扣分项附带具体改进方案

8 个质量维度:
  1. 字数合规 — 字数是否在目标范围内
  2. 对话密度 — 对话占比是否合理
  3. 动作密度 — 动作描写是否充足
  4. 描写丰富度 — 环境/外貌/心理描写比例
  5. 句式多样性 — 长短句交替变化
  6. 节奏控制 — 段落长度变化是否合理
  7. 信息密度 — 是否有填充/水字数
  8. 章节完整性 — 是否有引入/发展/高潮/收尾
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from kunlun.config import settings

# ══════════════════════════════════════════════════════
# 数据类型
# ══════════════════════════════════════════════════════


class QualityDimension(Enum):
    """质量维度"""

    WORD_COUNT = "word_count"  # 字数合规
    DIALOGUE_DENSITY = "dialogue_density"  # 对话密度
    ACTION_DENSITY = "action_density"  # 动作密度
    DESCRIPTION_RICHNESS = "description_richness"  # 描写丰富度
    SENTENCE_VARIETY = "sentence_variety"  # 句式多样性
    PACING = "pacing"  # 节奏控制
    INFO_DENSITY = "info_density"  # 信息密度
    CHAPTER_STRUCTURE = "chapter_structure"  # 章节完整性


@dataclass
class QualityScore:
    """单维度质量评分"""

    dimension: QualityDimension
    score: float  # 0.0~1.0
    level: str  # "excellent" | "good" | "fair" | "poor"
    raw_value: Any = None  # 原始计算值
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class ChapterQualityReport:
    """章节质量报告"""

    chapter_number: int
    word_count: int
    overall_score: float  # 0.0~1.0
    overall_level: str  # 综合评级
    dimension_scores: dict[str, QualityScore] = field(default_factory=dict)
    summary: str = ""
    auto_fixable: int = 0  # 可自动修复的问题数

    def to_dict(self) -> dict:
        return {
            "chapter_number": self.chapter_number,
            "word_count": self.word_count,
            "overall_score": self.overall_score,
            "overall_level": self.overall_level,
            "dimension_scores": {
                k: {"score": v.score, "level": v.level, "issues": v.issues}
                for k, v in self.dimension_scores.items()
            },
            "summary": self.summary,
            "auto_fixable": self.auto_fixable,
        }


# ══════════════════════════════════════════════════════
# 质量评估器
# ══════════════════════════════════════════════════════


class QualityEvaluator:
    """质量评估器 — 8 维度纯规则评分

    零 LLM 成本，所有评分基于正则/统计
    """

    # 网文特征关键词
    _ACTION_KEYWORDS: list[str] = [
        "打",
        "杀",
        "砍",
        "刺",
        "劈",
        "斩",
        "轰",
        "冲",
        "跳",
        "飞",
        "跑",
        "逃",
        "追",
        "闪",
        "躲",
        "挡",
        "拍",
        "踢",
        "拳",
        "剑",
        "刀",
        "枪",
        "掌",
        "腿",
        "指",
        "气",
        "灵",
        "法",
        "术",
        "咒",
        "施",
        "放",
        "召",
        "唤",
        "运",
        "催",
        "祭",
        "凝",
        "聚",
        "爆",
    ]

    _DIALOGUE_MARKERS: list[str] = ["“", '"', "「", "『", "：", "说", "道", "问", "答", "讲"]

    _DESCRIPTION_KEYWORDS: list[str] = [
        "色",
        "光",
        "风",
        "云",
        "月",
        "星",
        "日",
        "夜",
        "晨",
        "暮",
        "山",
        "水",
        "林",
        "城",
        "殿",
        "楼",
        "街",
        "巷",
        "院",
        "室",
        "红",
        "蓝",
        "绿",
        "白",
        "黑",
        "金",
        "银",
        "紫",
        "青",
        "黄",
        "美",
        "俊",
        "冷",
        "俏",
        "艳",
        "素",
        "雅",
        "华",
        "古",
        "新",
        "眼",
        "眉",
        "唇",
        "发",
        "手",
        "脸",
        "身",
        "影",
        "姿",
        "态",
    ]

    _FILLER_PATTERNS: list[str] = [
        r"([^。]{5,})\1",  # 重复短语
        r"([\u4e00-\u9fff])\1{4,}",  # 单字重复5次以上
        r"(?:也就是说|换句话说|总而言之|简单来说|总的来说)",  # 填充套话
    ]

    _STRUCTURE_KEYWORDS: dict[str, list[str]] = {
        "intro": ["刚", "开始", "清晨", "早上", "一早", "今日", "今天"],
        "development": ["路上", "途中", "来到", "见到", "发现", "突然"],
        "climax": ["战斗", "冲突", "决战", "交锋", "爆发", "终于"],
        "ending": ["结束", "回到", "离开", "之后", "明天", "夜里", "晚上"],
    }

    def evaluate(
        self, text: str, chapter_number: int = 0, target_word_count: int = 4000
    ) -> ChapterQualityReport:
        """评估章节质量"""
        word_count = len(text)
        report = ChapterQualityReport(
            chapter_number=chapter_number,
            word_count=word_count,
            overall_score=0.0,
            overall_level="fair",
        )

        # 1. 字数合规
        report.dimension_scores["word_count"] = self._score_word_count(
            word_count, target_word_count
        )

        # 2. 对话密度
        report.dimension_scores["dialogue_density"] = self._score_dialogue(text)

        # 3. 动作密度
        report.dimension_scores["action_density"] = self._score_action(text)

        # 4. 描写丰富度
        report.dimension_scores["description_richness"] = self._score_description(text)

        # 5. 句式多样性
        report.dimension_scores["sentence_variety"] = self._score_sentence_variety(text)

        # 6. 节奏控制
        report.dimension_scores["pacing"] = self._score_pacing(text)

        # 7. 信息密度
        report.dimension_scores["info_density"] = self._score_info_density(text, word_count)

        # 8. 章节完整性
        report.dimension_scores["chapter_structure"] = self._score_structure(text)

        # 综合评分
        weights = {
            "word_count": 0.10,
            "dialogue_density": 0.15,
            "action_density": 0.20,
            "description_richness": 0.15,
            "sentence_variety": 0.10,
            "pacing": 0.10,
            "info_density": 0.10,
            "chapter_structure": 0.10,
        }

        weighted_sum = sum(
            report.dimension_scores[k].score * weights.get(k, 0.125)
            for k in report.dimension_scores
        )
        report.overall_score = round(weighted_sum, 2)

        # 评级
        if report.overall_score >= 0.85:
            report.overall_level = "excellent"
        elif report.overall_score >= 0.70:
            report.overall_level = "good"
        elif report.overall_score >= 0.50:
            report.overall_level = "fair"
        else:
            report.overall_level = "poor"

        # 可自动修复计数
        report.auto_fixable = sum(
            1
            for ds in report.dimension_scores.values()
            if ds.level in ("fair", "poor") and ds.suggestions
        )

        # 摘要
        issues = []
        for dim_name, ds in report.dimension_scores.items():
            if ds.level in ("fair", "poor"):
                issues.append(f"{dim_name}: {ds.score:.2f}({ds.level})")
        report.summary = f"综合 {report.overall_score:.2f} ({report.overall_level}), " + (
            f"问题: {'; '.join(issues)}" if issues else "全部通过"
        )

        return report

    # ── 各维度评分方法 ────────────────────────────────

    def _score_word_count(self, actual: int, target: int) -> QualityScore:
        """评分字数合规度"""
        ratio = actual / max(target, 1)
        if 0.85 <= ratio <= 1.15:
            return QualityScore(QualityDimension.WORD_COUNT, 1.0, "excellent", ratio)
        if 0.70 <= ratio <= 1.30:
            return QualityScore(QualityDimension.WORD_COUNT, 0.8, "good", ratio)
        if 0.50 <= ratio <= 1.50:
            return QualityScore(
                QualityDimension.WORD_COUNT,
                0.5,
                "fair",
                ratio,
                issues=[f"字数偏差较大: {actual}/{target}"],
                suggestions=["扩充到目标字数" if ratio < 1 else "精简到目标字数"],
            )
        return QualityScore(
            QualityDimension.WORD_COUNT,
            0.2,
            "poor",
            ratio,
            issues=[f"字数严重偏差: {actual}/{target}"],
            suggestions=["重新规划篇幅"],
        )

    def _score_dialogue(self, text: str) -> QualityScore:
        """评分对话密度"""
        # 计算引号内容占比
        quote_chars = 0
        in_quote = False
        for ch in text:
            if ch in ('"', '"', "「", "『"):
                in_quote = not in_quote
            if in_quote:
                quote_chars += 1

        dialogue_ratio = quote_chars / max(len(text), 1)

        # 网文理想对话比例: 25%~45%
        if 0.25 <= dialogue_ratio <= 0.45:
            return QualityScore(QualityDimension.DIALOGUE_DENSITY, 1.0, "excellent", dialogue_ratio)
        if 0.15 <= dialogue_ratio <= 0.55:
            return QualityScore(QualityDimension.DIALOGUE_DENSITY, 0.8, "good", dialogue_ratio)
        if dialogue_ratio < 0.15:
            return QualityScore(
                QualityDimension.DIALOGUE_DENSITY,
                0.5,
                "fair",
                dialogue_ratio,
                issues=[f"对话过少: {dialogue_ratio:.1%}"],
                suggestions=["增加对话场景，提升读者代入感"],
            )
        return QualityScore(
            QualityDimension.DIALOGUE_DENSITY,
            0.5,
            "fair",
            dialogue_ratio,
            issues=[f"对话过多: {dialogue_ratio:.1%}"],
            suggestions=["增加叙述/描写，避免纯对话章"],
        )

    def _score_action(self, text: str) -> QualityScore:
        """评分动作密度"""
        action_count = sum(text.count(kw) for kw in self._ACTION_KEYWORDS)
        density = action_count / max(len(text), 1) * 100  # 每百字动作词

        if 3 <= density <= 8:
            return QualityScore(QualityDimension.ACTION_DENSITY, 1.0, "excellent", density)
        if 2 <= density <= 10:
            return QualityScore(QualityDimension.ACTION_DENSITY, 0.8, "good", density)
        if density < 2:
            return QualityScore(
                QualityDimension.ACTION_DENSITY,
                0.5,
                "fair",
                density,
                issues=[f"动作描写偏少: {density:.1f}/百字"],
                suggestions=["增加动作/战斗/冲突场景"],
            )
        return QualityScore(
            QualityDimension.ACTION_DENSITY,
            0.6,
            "fair",
            density,
            issues=[f"动作词过多: {density:.1f}/百字 (可能纯打斗无情节)"],
            suggestions=["平衡动作与情节推进"],
        )

    def _score_description(self, text: str) -> QualityScore:
        """评分描写丰富度"""
        desc_count = sum(text.count(kw) for kw in self._DESCRIPTION_KEYWORDS)
        density = desc_count / max(len(text), 1) * 100

        if 4 <= density <= 12:
            return QualityScore(QualityDimension.DESCRIPTION_RICHNESS, 1.0, "excellent", density)
        if 2 <= density <= 15:
            return QualityScore(QualityDimension.DESCRIPTION_RICHNESS, 0.8, "good", density)
        if density < 2:
            return QualityScore(
                QualityDimension.DESCRIPTION_RICHNESS,
                0.4,
                "fair",
                density,
                issues=[f"描写过于匮乏: {density:.1f}/百字"],
                suggestions=["增加环境描写、人物外貌、心理活动"],
            )
        return QualityScore(
            QualityDimension.DESCRIPTION_RICHNESS,
            0.6,
            "fair",
            density,
            issues=[f"描写过多: {density:.1f}/百字 (可能拖慢节奏)"],
            suggestions=["精简环境描写或心理描写"],
        )

    def _score_sentence_variety(self, text: str) -> QualityScore:
        """评分句式多样性"""
        # 分割句子
        sentences = re.split(r"[。！？\.!\?]", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) < 5:
            return QualityScore(
                QualityDimension.SENTENCE_VARIETY, 0.5, "fair", 0, issues=["句子太少无法评估"]
            )

        lengths = [len(s) for s in sentences]
        avg_len = sum(lengths) / len(lengths)
        std_len = (sum((length - avg_len) ** 2 for length in lengths) / len(lengths)) ** 0.5

        # 变异系数 (标准差/平均值) — 反映句式多样性
        cv = std_len / max(avg_len, 1)

        if cv > 0.6:
            return QualityScore(
                QualityDimension.SENTENCE_VARIETY, 1.0, "excellent", cv, suggestions=[]
            )
        if cv > 0.4:
            return QualityScore(QualityDimension.SENTENCE_VARIETY, 0.8, "good", cv)
        if cv > 0.25:
            return QualityScore(
                QualityDimension.SENTENCE_VARIETY,
                0.5,
                "fair",
                cv,
                issues=[f"句式较单一 (cv={cv:.2f})"],
                suggestions=["增加长短句交替，避免句式重复"],
            )
        return QualityScore(
            QualityDimension.SENTENCE_VARIETY,
            0.3,
            "poor",
            cv,
            issues=[f"句式极其单一 (cv={cv:.2f})，典型 AI 特征"],
            suggestions=["大幅改善句式变化，增加口语化短句 + 描写长句的交替"],
        )

    def _score_pacing(self, text: str) -> QualityScore:
        """评分段落节奏"""
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if len(paragraphs) < 3:
            return QualityScore(QualityDimension.PACING, 0.5, "fair", 0, issues=["段落太少"])

        para_lens = [len(p) for p in paragraphs]
        avg_para_len = sum(para_lens) / len(para_lens)

        # 检查段落长度变化
        long_paras = sum(1 for length in para_lens if length > 200)
        short_paras = sum(1 for length in para_lens if length < 50)
        total = len(para_lens)

        long_ratio = long_paras / total
        short_ratio = short_paras / total

        # 理想节奏: 20%短段落(打斗/对话) + 50%中等段 + 30%长段落(描写)
        score = 1.0
        issues: list[str] = []

        if long_ratio > 0.5:
            score -= 0.3
            issues.append("长段落过多，节奏拖沓")
        if short_ratio > 0.5:
            score -= 0.2
            issues.append("短段落过多，碎片化严重")
        if short_ratio < 0.1:
            score -= 0.15
            issues.append("缺少短段落作为节奏变化")

        if score >= 0.9:
            level = "excellent"
        elif score >= 0.7:
            level = "good"
        elif score >= 0.5:
            level = "fair"
        else:
            level = "poor"

        suggestions: list[str] = []
        if "长段落过多" in " ".join(issues):
            suggestions.append("将长段落拆分为多个中等段落")
        if "短段落过多" in " ".join(issues):
            suggestions.append("合并相邻短段落形成节奏起伏")

        return QualityScore(
            QualityDimension.PACING,
            round(score, 2),
            level,
            {
                "avg_para_len": int(avg_para_len),
                "long_ratio": round(long_ratio, 2),
                "short_ratio": round(short_ratio, 2),
            },
            issues=issues,
            suggestions=suggestions,
        )

    def _score_info_density(self, text: str, word_count: int) -> QualityScore:
        """评分信息密度 (反水源)"""
        # 检查填充词
        filler_count = 0
        for pattern in self._FILLER_PATTERNS:
            filler_count += len(re.findall(pattern, text))

        # 检查"的"字密度 (网络水文特征)
        de_count = text.count("的")
        de_density = de_count / max(word_count, 1)

        # 检查段落重复
        unique_para_ratio = len({text[i : i + 50] for i in range(0, len(text) - 50, 50)}) / max(
            len(text) // 50, 1
        )

        score = 1.0
        issues: list[str] = []
        suggestions: list[str] = []

        if filler_count > 3:
            score -= 0.15 * filler_count
            issues.append(f"发现 {filler_count} 处填充/套话")
            suggestions.append("删除重复和填充内容")

        if de_density > 0.08:
            score -= 0.1
            issues.append(f"'的'字过多: {de_density:.3f}")
            suggestions.append("减少'的'字使用")

        if unique_para_ratio < 0.6 and word_count > 500:
            score -= 0.2
            issues.append("文本重复度高")
            suggestions.append("丰富情节内容")

        score = max(0.0, round(score, 2))

        if score >= 0.9:
            level = "excellent"
        elif score >= 0.7:
            level = "good"
        elif score >= 0.4:
            level = "fair"
        else:
            level = "poor"

        return QualityScore(
            QualityDimension.INFO_DENSITY,
            score,
            level,
            {"filler_count": filler_count, "de_density": de_density},
            issues=issues,
            suggestions=suggestions,
        )

    def _score_structure(self, text: str) -> QualityScore:
        """评分章节结构完整性"""
        if len(text) < 500:
            return QualityScore(
                QualityDimension.CHAPTER_STRUCTURE,
                0.3,
                "poor",
                {},
                issues=["章节过短，无法评估结构"],
            )

        # 按文本位置粗略分段: 头25% / 中50% / 尾25%
        third = len(text) // 4
        head = text[:third]
        mid = text[third:-third]
        tail = text[-third:]

        structure_score = 0
        issues: list[str] = []
        suggestions: list[str] = []

        # 引入部分检查
        intro_kw = sum(head.count(kw) for kw in self._STRUCTURE_KEYWORDS["intro"])
        if intro_kw >= 1:
            structure_score += 1
        else:
            issues.append("缺少引入/铺垫")
            suggestions.append("章节开头添加场景引入或承接上文")

        # 发展部分检查
        dev_kw = sum(mid.count(kw) for kw in self._STRUCTURE_KEYWORDS["development"])
        if dev_kw >= 2:
            structure_score += 1
        else:
            issues.append("缺少情节发展")

        # 高潮部分检查
        climax_kw = sum(text.count(kw) for kw in self._STRUCTURE_KEYWORDS["climax"])
        if climax_kw >= 2:
            structure_score += 1
        else:
            issues.append("缺少高潮/冲突")
            suggestions.append("确保每章有一个小高潮或冲突点")

        # 收尾部分检查
        ending_kw = sum(tail.count(kw) for kw in self._STRUCTURE_KEYWORDS["ending"])
        if ending_kw >= 1:
            structure_score += 1
        else:
            issues.append("缺少收尾/悬念")
            suggestions.append("章节末尾添加悬念或情绪收尾")

        score = structure_score / 4.0
        level = (
            "excellent"
            if score >= 0.9
            else ("good" if score >= 0.7 else ("fair" if score >= 0.5 else "poor"))
        )

        return QualityScore(
            QualityDimension.CHAPTER_STRUCTURE,
            score,
            level,
            int(structure_score),
            issues=issues,
            suggestions=suggestions,
        )


# ══════════════════════════════════════════════════════
# 质量趋势追踪器
# ══════════════════════════════════════════════════════


class QualityTrendTracker:
    """全书质量趋势追踪"""

    def __init__(self, book_id: str):
        self.book_id = book_id
        self.trend_dir = settings.DATA_DIR / "quality" / book_id
        self.trend_dir.mkdir(parents=True, exist_ok=True)
        self._history: dict[int, ChapterQualityReport] = {}
        self._load()

    def _load(self):
        path = self.trend_dir / "history.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                for ch_str, report_data in data.items():
                    ch = int(ch_str)
                    self._history[ch] = ChapterQualityReport(
                        chapter_number=ch,
                        word_count=report_data.get("word_count", 0),
                        overall_score=report_data.get("overall_score", 0),
                        overall_level=report_data.get("overall_level", "fair"),
                    )
            except Exception as e:
                logger.warning(f"加载质量历史失败: {e}")

    def save_report(self, report: ChapterQualityReport):
        """保存章节质量报告"""
        self._history[report.chapter_number] = report
        data = {}
        for ch, r in self._history.items():
            data[str(ch)] = {
                "chapter_number": r.chapter_number,
                "word_count": r.word_count,
                "overall_score": r.overall_score,
                "overall_level": r.overall_level,
                "summary": r.summary,
            }
        path = self.trend_dir / "history.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_trend(self, last_n: int = 20) -> dict[str, Any]:
        """获取质量趋势"""
        sorted_chapters = sorted(self._history.keys())[-last_n:]

        if not sorted_chapters:
            return {"trend": "no_data", "chapters": []}

        scores = [self._history[ch].overall_score for ch in sorted_chapters]

        # 线性回归
        n = len(scores)
        x_mean = (n - 1) / 2
        y_mean = sum(scores) / n

        numerator = sum((i - x_mean) * (scores[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / max(denominator, 0.001)

        trend = "stable"
        if slope > 0.01:
            trend = "improving"
        elif slope < -0.01:
            trend = "declining"

        return {
            "trend": trend,
            "slope": round(slope, 4),
            "avg_score": round(y_mean, 2),
            "min_score": round(min(scores), 2),
            "max_score": round(max(scores), 2),
            "chapters": [
                {
                    "chapter": ch,
                    "score": self._history[ch].overall_score,
                    "level": self._history[ch].overall_level,
                }
                for ch in sorted_chapters
            ],
        }

    def get_dimension_trend(self, dimension: QualityDimension, last_n: int = 20) -> list[dict]:
        """获取单维度趋势"""
        sorted_chapters = sorted(self._history.keys())[-last_n:]
        result: list[dict] = []
        for ch in sorted_chapters:
            report = self._history[ch]
            ds = report.dimension_scores.get(dimension.value)
            if ds:
                result.append(
                    {
                        "chapter": ch,
                        "score": ds.score,
                        "level": ds.level,
                    }
                )
        return result

    def get_statistics(self) -> dict[str, Any]:
        """获取全书统计"""
        if not self._history:
            return {"total_chapters": 0}

        chapters = self._history.keys()
        scores = [self._history[ch].overall_score for ch in chapters]
        word_counts = [self._history[ch].word_count for ch in chapters]

        return {
            "total_chapters": len(chapters),
            "avg_score": round(sum(scores) / len(scores), 2),
            "max_score": round(max(scores), 2),
            "min_score": round(min(scores), 2),
            "excellent_chapters": sum(1 for s in scores if s >= 0.85),
            "good_chapters": sum(1 for s in scores if 0.70 <= s < 0.85),
            "fair_chapters": sum(1 for s in scores if 0.50 <= s < 0.70),
            "poor_chapters": sum(1 for s in scores if s < 0.50),
            "total_words": sum(word_counts),
            "avg_word_count": int(sum(word_counts) / len(word_counts)),
        }


# ══════════════════════════════════════════════════════
# 工厂函数
# ══════════════════════════════════════════════════════

_evaluator: QualityEvaluator | None = None
_trackers: dict[str, QualityTrendTracker] = {}


def get_quality_evaluator() -> QualityEvaluator:
    global _evaluator  # noqa: PLW0603
    if _evaluator is None:
        _evaluator = QualityEvaluator()
    return _evaluator


def get_quality_tracker(book_id: str) -> QualityTrendTracker:
    if book_id not in _trackers:
        _trackers[book_id] = QualityTrendTracker(book_id)
    return _trackers[book_id]


__all__ = [
    "ChapterQualityReport",
    "QualityDimension",
    "QualityEvaluator",
    "QualityScore",
    "QualityTrendTracker",
    "get_quality_evaluator",
    "get_quality_tracker",
]
