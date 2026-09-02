"""
昆仑创作引擎 — AIGC 痕迹检测增强系统核心引擎

基于已有 audit/ai_features.py (24+特征) 和 audit/post_write_validator.py (17条规则)，
提供更高层次的综合报告、跨章节统计趋势、批量检测和可操作性建议。
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from loguru import logger

from kunlun.config import settings

# ─── 数据类型 ────────────────────────────────────────


class AIDetectDimension(Enum):
    """AI 检测维度 (8维)"""

    CLICHE_PHRASES = "cliche_phrases"
    SENTENCE_VARIETY = "sentence_variety"
    PARAGRAPH_RHYTHM = "paragraph_rhythm"
    CONJUNCTION_ABUSE = "conjunction_abuse"
    PSYCHOLOGICAL_OVER = "psychological_over"
    EMOTION_RAW = "emotion_raw"
    DIALOGUE_WEAKNESS = "dialogue_weakness"
    STRUCTURAL_TEMPLATE = "structural_template"


@dataclass
class DimensionScore:
    """单维度评分"""

    dimension: AIDetectDimension
    score: float
    level: str
    issues: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIGCDetectReport:
    """AI 痕迹检测完整报告"""

    chapter_number: int
    word_count: int
    human_score: float
    ai_likelihood: float

    dimensions: list[DimensionScore] = field(default_factory=list)

    cliche_density: float = 0.0
    paragraph_cv: float = 0.0
    sentence_variety_index: float = 0.0
    conjunction_ratio: float = 0.0

    top_cliches: list[dict] = field(default_factory=list)
    template_patterns: list[str] = field(default_factory=list)

    is_human_like: bool = True
    is_ai_suspicious: bool = False
    level: str = "good"

    suggestions: list[str] = field(default_factory=list)
    auto_fixable_count: int = 0


# ─── 核心检测引擎 ────────────────────────────────────


class AIGCDetector:
    """AI 痕迹综合检测器 (八维评估)"""

    AI_CLICHES: list[str] = [
        "仿佛",
        "忽然",
        "竟然",
        "不禁",
        "宛如",
        "猛地",
        "似乎",
        "好像",
        "突然",
        "顿时",
        "不由得",
        "心中",
        "莫名",
        "连连",
        "只见",
    ]

    AI_TEMPLATE_PATTERNS: list[tuple[str, str]] = [
        (r"总[而之]的来说", "总结性结尾"),
        (r"通过这[件一].*?事", "说教总结"),
        (r"这[让使].*?意识[到会]", "AI感悟"),
        (r"从此以后", "时间跳转模板"),
        (r"值得[一]提的是", "AI插入语"),
        (r"不仅.*?而且.*?甚至", "过度递进"),
        (r"在这个.*?的.*?中", "模板化定语"),
        (r"显得格外的", "AI修饰词"),
        (r"让人[不]由得", "AI评价句式"),
        (r"一切都.*?了", "空洞总结"),
    ]

    AI_WEAK_VERBS: list[tuple[str, str, str]] = [
        (r"进行([了解送处])", "进行\\1", "动词弱化 → 直接动词"),
        (r"做出([了])", "做\\1", "弱动词 → 强动词"),
        (r"产生([了])", "产生\\1", "弱动词 → 具体动词"),
        (r"表现出", "表现", "弱动词 → 直接描写"),
    ]

    @classmethod
    def detect_cliches(cls, text: str) -> dict:
        word_count = len(text.replace("\n", "").replace(" ", ""))
        cliche_hits: dict[str, int] = {}
        total_hits = 0

        for cliche in cls.AI_CLICHES:
            count = text.count(cliche)
            if count > 0:
                cliche_hits[cliche] = count
                total_hits += count

        density = total_hits / max(word_count / 1000, 1)

        if density < 0.5:
            score, level = 0.95, "good"
        elif density < 1.5:
            score, level = 0.75, "good"
        elif density < 3.0:
            score, level = 0.50, "warning"
        else:
            score, level = 0.20, "bad"

        top_cliches = sorted(cliche_hits.items(), key=lambda x: -x[1])[:8]

        return {
            "total_hits": total_hits,
            "density_per_1k": round(density, 2),
            "score": round(score, 2),
            "level": level,
            "top_cliches": [{"phrase": k, "count": v} for k, v in top_cliches],
        }

    @classmethod
    def detect_sentence_variety(cls, text: str) -> dict:
        import re

        sentences = re.split(r"[。！？\n]", text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]

        if len(sentences) < 5:
            return {"score": 0.8, "level": "good", "sentence_count": len(sentences)}

        first_words: dict[str, int] = defaultdict(int)
        for s in sentences:
            fw = s[:2] if len(s) >= 2 else s
            first_words[fw] += 1

        max_freq = max(first_words.values()) if first_words else 1
        diversity = 1 - max_freq / len(sentences)

        lengths = [len(s) for s in sentences]
        avg_len = sum(lengths) / len(lengths)
        if avg_len > 0:
            length_cv = (
                sum((length - avg_len) ** 2 for length in lengths) / len(lengths)
            ) ** 0.5 / avg_len
        else:
            length_cv = 0

        score = diversity * 0.5 + min(length_cv / 0.8, 1.0) * 0.5
        level = "good" if score > 0.7 else ("warning" if score > 0.4 else "bad")

        return {
            "score": round(score, 2),
            "level": level,
            "sentence_count": len(sentences),
            "first_word_diversity": round(diversity, 2),
            "length_cv": round(length_cv, 2),
            "avg_sentence_length": round(avg_len, 1),
        }

    @classmethod
    def detect_paragraph_rhythm(cls, text: str) -> dict:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if len(paragraphs) < 3:
            return {"score": 0.8, "level": "good", "paragraph_count": len(paragraphs)}

        lengths = [len(p) for p in paragraphs]
        avg_len = sum(lengths) / len(lengths) if lengths else 1
        if avg_len > 0:
            cv = (
                sum((length - avg_len) ** 2 for length in lengths) / len(lengths)
            ) ** 0.5 / avg_len
        else:
            cv = 0

        consecutive_similar = 0
        max_consecutive = 0
        for i in range(1, len(lengths)):
            if abs(lengths[i] - lengths[i - 1]) < 0.2 * max(avg_len, 1):
                consecutive_similar += 1
                max_consecutive = max(max_consecutive, consecutive_similar)
            else:
                consecutive_similar = 0

        if 0.3 < cv < 0.8:
            cv_score = 1.0
        elif 0.15 < cv <= 0.3 or 0.8 <= cv < 1.2:
            cv_score = 0.7
        else:
            cv_score = 0.3

        consecutive_penalty = max(0, max_consecutive - 3) * 0.05
        score = max(0.1, cv_score - consecutive_penalty)
        level = "good" if score > 0.7 else ("warning" if score > 0.4 else "bad")

        return {
            "score": round(score, 2),
            "level": level,
            "paragraph_count": len(paragraphs),
            "length_cv": round(cv, 2),
            "avg_length": round(avg_len),
            "max_consecutive_similar": max_consecutive,
        }

    @classmethod
    def detect_conjunction_abuse(cls, text: str) -> dict:
        word_count = len(text.replace("\n", "").replace(" ", ""))

        conjunctions = [
            "然而",
            "但是",
            "却",
            "不过",
            "可是",
            "因此",
            "所以",
            "于是",
            "因而",
            "此外",
            "另外",
            "还有",
            "而且",
            "况且",
            "虽然",
            "尽管",
            "即便",
        ]

        total = 0
        hits: dict[str, int] = {}
        for conj in conjunctions:
            count = text.count(conj)
            if count > 0:
                hits[conj] = count
                total += count

        density = total / max(word_count / 1000, 1)

        if density < 5:
            score, level = 0.9, "good"
        elif density < 10:
            score, level = 0.65, "good"
        elif density < 20:
            score, level = 0.4, "warning"
        else:
            score, level = 0.15, "bad"

        return {
            "total_hits": total,
            "density_per_1k": round(density, 2),
            "score": round(score, 2),
            "level": level,
            "top": sorted(hits.items(), key=lambda x: -x[1])[:5],
        }

    @classmethod
    def detect_psychological_over(cls, text: str) -> dict:
        patterns = [
            (r"心中.{0,5}(?:想|觉得|知道|明白|清楚|暗想|思索)", "心中体"),
            (r"暗暗.{0,5}(?:想|决定|发誓|记下|佩服)", "暗暗体"),
            (r"(?:意识|认识|察觉|发现|感觉).{0,5}到", "意识到体"),
            (r"心[里中头底].{0,5}(?:涌|浮|升|闪)", "心理描写"),
        ]

        total = 0
        details: dict[str, int] = {}
        for pattern, label in patterns:
            import re

            count = len(re.findall(pattern, text))
            if count > 0:
                details[label] = count
                total += count

        word_count = len(text.replace("\n", "").replace(" ", ""))
        density = total / max(word_count / 1000, 1)

        if density < 1:
            score, level = 0.9, "good"
        elif density < 3:
            score, level = 0.65, "good"
        elif density < 6:
            score, level = 0.4, "warning"
        else:
            score, level = 0.15, "bad"

        return {
            "total_hits": total,
            "density_per_1k": round(density, 2),
            "score": round(score, 2),
            "level": level,
            "details": details,
        }

    @classmethod
    def detect_emotion_raw(cls, text: str) -> dict:
        patterns = [
            r"感到.{0,5}(?:愤怒|悲伤|快乐|恐惧|失望|激动|幸福)",
            r"情绪.{0,5}(?:激动|低落|复杂|失控)",
            r"(?:愤怒|悲伤|快乐|恐惧)的.{0,5}(?:情绪|心情|感觉)",
            r"充满[了的].{0,5}(?:愤怒|悲伤|快乐|希望|绝望)",
        ]

        import re

        total = sum(len(re.findall(p, text)) for p in patterns)
        word_count = len(text.replace("\n", "").replace(" ", ""))
        density = total / max(word_count / 1000, 1)

        if density < 0.5:
            score, level = 0.95, "good"
        elif density < 2:
            score, level = 0.7, "good"
        elif density < 4:
            score, level = 0.4, "warning"
        else:
            score, level = 0.15, "bad"

        return {
            "total_hits": total,
            "density_per_1k": round(density, 2),
            "score": round(score, 2),
            "level": level,
        }

    @classmethod
    def detect_dialogue_weakness(cls, text: str) -> dict:
        import re

        dialogue_matches = re.findall(r'[""]([^""]{10,})[""]', text)

        if not dialogue_matches:
            return {"score": 0.85, "level": "good", "dialogue_count": 0}

        weak_tags = ["说道", "问道", "回答道", "说道:", "问道:", "说道。"]
        tag_count = sum(text.count(t) for t in weak_tags)
        tag_density = tag_count / max(len(dialogue_matches), 1)

        hollow_patterns = [
            r"你说[的得]对",
            r"我知道了",
            r"好的[，。]",
            r"嗯[，。]",
            r"明白了",
        ]
        hollow_count = sum(len(re.findall(p, text)) for p in hollow_patterns)

        tag_score = max(0, 1 - tag_density / 3)
        content_score = max(0, 1 - hollow_count / max(len(dialogue_matches), 1) * 3)
        score = tag_score * 0.5 + content_score * 0.5

        level = "good" if score > 0.7 else ("warning" if score > 0.4 else "bad")

        return {
            "score": round(score, 2),
            "level": level,
            "dialogue_count": len(dialogue_matches),
            "weak_tag_density": round(tag_density, 2),
            "hollow_patterns": hollow_count,
        }

    @classmethod
    def detect_structural_template(cls, text: str) -> dict:
        import re

        hits: list[str] = []
        for pattern, label in cls.AI_TEMPLATE_PATTERNS:
            if re.search(pattern, text):
                hits.append(label)

        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        template_indicators = 0

        if paragraphs:
            first = paragraphs[0][:20]
            if re.search(r"^(?:随着|当|在[这一那天])", first):
                template_indicators += 1

            if len(paragraphs) > 1:
                last = paragraphs[-1][:30]
                if re.search(r"(?:就这样|一切|故事|新的)", last):
                    template_indicators += 1

        score = max(0.1, 1.0 - len(hits) * 0.15 - template_indicators * 0.1)
        level = "good" if score > 0.7 else ("warning" if score > 0.4 else "bad")

        return {
            "score": round(score, 2),
            "level": level,
            "template_patterns": hits,
            "structural_issues": template_indicators,
        }

    @classmethod
    def analyze(cls, text: str, chapter_number: int = 1) -> AIGCDetectReport:
        word_count = len(text.replace("\n", "").replace(" ", ""))

        dims = [
            ("cliche_phrases", cls.detect_cliches(text)),
            ("sentence_variety", cls.detect_sentence_variety(text)),
            ("paragraph_rhythm", cls.detect_paragraph_rhythm(text)),
            ("conjunction_abuse", cls.detect_conjunction_abuse(text)),
            ("psychological_over", cls.detect_psychological_over(text)),
            ("emotion_raw", cls.detect_emotion_raw(text)),
            ("dialogue_weakness", cls.detect_dialogue_weakness(text)),
            ("structural_template", cls.detect_structural_template(text)),
        ]

        dimension_scores: list[DimensionScore] = []
        total_score = 0.0
        weights = {
            "cliche_phrases": 0.20,
            "sentence_variety": 0.15,
            "paragraph_rhythm": 0.15,
            "conjunction_abuse": 0.10,
            "psychological_over": 0.10,
            "emotion_raw": 0.08,
            "dialogue_weakness": 0.12,
            "structural_template": 0.10,
        }

        issues: list[str] = []
        suggestions: list[str] = []
        top_cliches: list[dict] = []
        template_patterns: list[str] = []

        for dim_name, result in dims:
            dim_enum = AIDetectDimension(dim_name)
            score = result["score"]
            weight = weights.get(dim_name, 0.1)
            total_score += score * weight

            dim_issues = []
            if result["level"] == "bad":
                dim_issues.append(
                    f"{dim_name}: {result.get('density_per_1k', result.get('sentence_count', ''))}"
                )
                suggestions.append(cls._get_dim_suggestion(dim_name, result))
            elif result["level"] == "warning":
                dim_issues.append(f"{dim_name}: 需关注")

            if dim_name == "cliche_phrases" and "top_cliches" in result:
                top_cliches = result["top_cliches"]
            if dim_name == "structural_template" and "template_patterns" in result:
                template_patterns = result["template_patterns"]

            dimension_scores.append(
                DimensionScore(
                    dimension=dim_enum,
                    score=round(score, 2),
                    level=result["level"],
                    issues=dim_issues,
                    details=result,
                )
            )

        human_score = round(total_score, 2)
        ai_likelihood = round(1 - human_score, 2)

        if human_score >= 0.75:
            is_human_like, is_ai_suspicious, level = True, False, "good"
        elif human_score >= 0.55:
            is_human_like, is_ai_suspicious, level = True, True, "suspicious"
        else:
            is_human_like, is_ai_suspicious, level = False, True, "likely_ai"

        auto_fixable_count = sum(
            1
            for d in dimension_scores
            if d.dimension == AIDetectDimension.CLICHE_PHRASES and d.level == "bad"
        )

        return AIGCDetectReport(
            chapter_number=chapter_number,
            word_count=word_count,
            human_score=human_score,
            ai_likelihood=ai_likelihood,
            dimensions=dimension_scores,
            cliche_density=dimension_scores[0].details.get("density_per_1k", 0),
            paragraph_cv=dimension_scores[2].details.get("length_cv", 0),
            top_cliches=top_cliches,
            template_patterns=template_patterns,
            is_human_like=is_human_like,
            is_ai_suspicious=is_ai_suspicious,
            level=level,
            suggestions=suggestions,
            auto_fixable_count=auto_fixable_count,
        )

    @classmethod
    def _get_dim_suggestion(cls, dim_name: str, _result: dict) -> str:
        suggestions = {
            "cliche_phrases": "套话过多，建议用 StyleEngineer 批量替换 AI 高频词",
            "sentence_variety": "句式单调，建议变化句首词汇，交替使用长短句",
            "paragraph_rhythm": "段落过于均匀，建议有意制造段落长短变化",
            "conjunction_abuse": "连词过多，建议删除不必要的转折词",
            "psychological_over": "心理描写过度，建议通过动作/对话间接表达内心",
            "emotion_raw": "感情表达直白，建议用场景/细节含蓄表达情感",
            "dialogue_weakness": "对话空洞，建议增加个性化表达和潜台词",
            "structural_template": "结构模板化，建议打破固定开头/结尾模式",
        }
        return suggestions.get(dim_name, "建议优化该维度")


# ─── 趋势分析器 ──────────────────────────────────────


class AIGCTrendTracker:
    """AI 痕迹趋势分析器 — 跨章节监控"""

    def __init__(self, book_id: str = ""):
        self.book_id = book_id
        self._history: list[dict] = []
        self._data_dir: Path | None = None

        if book_id:
            self._data_dir = settings.DATA_DIR / "aigc_detect" / book_id
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    def add_report(self, report: AIGCDetectReport) -> None:
        entry = {
            "chapter": report.chapter_number,
            "human_score": report.human_score,
            "level": report.level,
            "dimensions": {d.dimension.value: d.score for d in report.dimensions},
        }
        self._history.append(entry)
        self._save()

    def get_trend(self, last_n: int = 20) -> dict:
        if not self._history:
            return {"chapters": 0, "trend": "stable"}

        recent = self._history[-last_n:]
        scores = [h["human_score"] for h in recent]

        slope = 0
        if len(scores) >= 3:
            n = len(scores)
            x_mean = (n - 1) / 2
            y_mean = sum(scores) / n
            slope = sum((i - x_mean) * (scores[i] - y_mean) for i in range(n)) / max(
                sum((i - x_mean) ** 2 for i in range(n)), 0.01
            )

            if slope < -0.02:
                trend = "declining"
            elif slope > 0.02:
                trend = "improving"
            else:
                trend = "stable"
        else:
            slope, trend = 0, "stable"

        dim_trends: dict[str, list[float]] = {}
        if recent:
            dims = recent[0]["dimensions"].keys()
            for dim in dims:
                dim_trends[dim] = [h["dimensions"].get(dim, 0) for h in recent]

        return {
            "chapters": len(self._history),
            "trend": trend,
            "slope": round(slope, 4),
            "recent_scores": scores,
            "avg_score": round(sum(scores) / len(scores), 2) if scores else 0,
            "dimension_trends": dim_trends,
            "alert": trend == "declining",
        }

    def get_radar_data(self, chapter: int = -1) -> dict:
        target = (
            self._history[chapter]
            if chapter >= 0 and abs(chapter) < len(self._history)
            else self._history[-1]
            if self._history
            else None
        )

        if not target:
            return {"dimensions": [], "scores": []}

        return {
            "dimensions": list(target["dimensions"].keys()),
            "scores": list(target["dimensions"].values()),
            "human_score": target["human_score"],
            "chapter": target["chapter"],
            "level": target["level"],
        }

    def _save(self) -> None:
        if not self._data_dir:
            return
        path = self._data_dir / "history.json"
        path.write_text(json.dumps(self._history, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not self._data_dir:
            return
        path = self._data_dir / "history.json"
        if path.exists():
            try:
                self._history = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                logger.debug("AIGC 检测历史加载失败")


# ─── 工厂函数 ────────────────────────────────────────

_detector: AIGCDetector | None = None
_trackers: dict[str, AIGCTrendTracker] = {}


def get_detector() -> AIGCDetector:
    global _detector  # noqa: PLW0603
    if _detector is None:
        _detector = AIGCDetector()
    return _detector


def get_tracker(book_id: str) -> AIGCTrendTracker:
    if book_id not in _trackers:
        _trackers[book_id] = AIGCTrendTracker(book_id)
    return _trackers[book_id]
