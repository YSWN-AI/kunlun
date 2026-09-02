"""
arc 引擎核心实现
角色弧光追踪 + 情感线分析

对标多智能体写作工具的角色发展跟踪能力，
纯规则零LLM：10类角色弧 + 情感强度曲线 + 特质快照对比。

Author: 昆仑创作引擎
"""

from kunlun.common.json_store import load_json, save_json

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from loguru import logger

from kunlun.config import settings

# ══════════════════════════════════════════════════════
# 枚举与数据类
# ══════════════════════════════════════════════════════


class ArcDirection(StrEnum):
    """弧光方向"""

    POSITIVE = "positive"  # 正向成长
    NEGATIVE = "negative"  # 堕落/黑化
    FLAT = "flat"  # 扁平（配角常见）
    REDEMPTION = "redemption"  # 救赎
    TRAGIC = "tragic"  # 悲剧
    HEROIC = "heroic"  # 英雄之旅
    COMING_OF_AGE = "coming_of_age"  # 成长
    REVENGE = "revenge"  # 复仇
    MYSTERY = "mystery"  # 身份揭秘
    CYCLE = "cycle"  # 循环/轮回

    @property
    def label(self) -> str:
        labels = {
            "positive": "正向成长",
            "negative": "堕落/黑化",
            "flat": "扁平",
            "redemption": "救赎",
            "tragic": "悲剧",
            "heroic": "英雄之旅",
            "coming_of_age": "成长",
            "revenge": "复仇",
            "mystery": "身份揭秘",
            "cycle": "循环/轮回",
        }
        return labels.get(self.value, self.value)


class EmotionType(StrEnum):
    """情感类型"""

    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    LOVE = "love"
    HATE = "hate"
    HOPE = "hope"
    DESPAIR = "despair"
    DETERMINATION = "determination"
    CONFUSION = "confusion"
    RELIEF = "relief"
    ANXIETY = "anxiety"

    @property
    def label(self) -> str:
        labels = {
            "joy": "喜悦",
            "sadness": "悲伤",
            "anger": "愤怒",
            "fear": "恐惧",
            "surprise": "惊讶",
            "disgust": "厌恶",
            "love": "爱",
            "hate": "恨",
            "hope": "希望",
            "despair": "绝望",
            "determination": "决心",
            "confusion": "困惑",
            "relief": "释然",
            "anxiety": "焦虑",
        }
        return labels.get(self.value, self.value)


class EmotionIntensity(StrEnum):
    """情感强度"""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class CharacterTrait:
    """角色特质"""

    name: str  # 特质名
    strength: float = 0.5  # 当前强度 0-1
    baseline: float = 0.5  # 初始强度
    chapter_recorded: int = 0  # 记录章节


@dataclass
class EmotionPoint:
    """情感点"""

    chapter: int
    emotion_type: EmotionType
    intensity: EmotionIntensity
    trigger: str = ""  # 触发事件简述
    context: str = ""  # 上下文片段


@dataclass
class EmotionLine:
    """角色情感线"""

    character_name: str
    points: list[EmotionPoint] = field(default_factory=list)
    dominant_emotion: EmotionType | None = None

    def add_point(self, point: EmotionPoint):
        self.points.append(point)
        # 更新主导情感
        from collections import Counter

        counts = Counter(p.emotion_type for p in self.points[-20:])  # 最近20章
        if counts:
            self.dominant_emotion = counts.most_common(1)[0][0]

    def get_intensity_curve(self, last_n: int = 20) -> list[dict]:
        """获取情感强度曲线"""
        return [
            {
                "chapter": p.chapter,
                "emotion": p.emotion_type.value,
                "intensity": p.intensity.value,
                "trigger": p.trigger[:50],
            }
            for p in self.points[-last_n:]
        ]


@dataclass
class TraitSnapshot:
    """特质快照"""

    chapter: int
    traits: dict[str, float] = field(default_factory=dict)  # name → strength
    captured_at: str = ""


@dataclass
class CharacterArc:
    """角色弧光"""

    name: str
    direction: ArcDirection
    traits: dict[str, CharacterTrait] = field(default_factory=dict)
    snapshots: list[TraitSnapshot] = field(default_factory=list)
    emotion_line: EmotionLine | None = None
    chapter_introduced: int = 0

    def take_snapshot(self, chapter: int):
        """拍摄当前特质快照"""
        snapshot = TraitSnapshot(
            chapter=chapter,
            traits={name: t.strength for name, t in self.traits.items()},
        )
        self.snapshots.append(snapshot)

    def get_trait_trend(self, trait_name: str) -> list[tuple[int, float]]:
        """获取特质变化趋势"""
        return [(s.chapter, s.traits.get(trait_name, 0)) for s in self.snapshots]


@dataclass
class ArcReport:
    """弧光分析报告"""

    book_id: str
    character_name: str
    direction: ArcDirection
    current_chapter: int
    trait_changes: list[dict]  # 特质变化列表
    emotion_summary: dict[str, int]  # 情感分布统计
    arc_progress: float = 0.0  # 弧光进度 0-1
    arc_health: str = "normal"  # 弧光健康度: normal/stalled/rushed/reversed
    suggestions: list[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════
# 情感分析器
# ══════════════════════════════════════════════════════


class EmotionAnalyzer:
    """情感分析器 — 基于关键词+上下文的纯规则分析"""

    # 情感关键词库（中文网文高频情感词汇）
    EMOTION_KEYWORDS: dict[EmotionType, list[str]] = {
        EmotionType.JOY: ["笑", "喜", "乐", "开心", "高兴", "欢喜", "欣慰", "畅快", "兴奋", "激动"],
        EmotionType.SADNESS: [
            "哭",
            "泪",
            "悲伤",
            "难过",
            "伤心",
            "哀",
            "痛",
            "凄凉",
            "黯然",
            "失落",
        ],
        EmotionType.ANGER: [
            "怒",
            "恨",
            "愤",
            "气",
            "恼",
            "暴",
            "恼火",
            "咬牙切齿",
            "火冒三丈",
            "勃然大怒",
        ],
        EmotionType.FEAR: [
            "怕",
            "恐惧",
            "惊恐",
            "畏惧",
            "胆寒",
            "战栗",
            "瑟瑟发抖",
            "毛骨悚然",
            "惊慌",
            "骇然",
        ],
        EmotionType.SURPRISE: [
            "惊",
            "讶",
            "诧异",
            "愕然",
            "震惊",
            "意外",
            "没想到",
            "出乎意料",
            "目瞪口呆",
            "难以置信",
        ],
        EmotionType.LOVE: [
            "爱",
            "情",
            "恋",
            "倾心",
            "心动",
            "痴迷",
            "温柔",
            "宠溺",
            "深情",
            "缠绵",
        ],
        EmotionType.HATE: ["恨", "仇", "怨", "憎", "厌恶", "痛恨", "仇视", "不共戴天", "咬牙切齿"],
        EmotionType.HOPE: [
            "希望",
            "期盼",
            "期待",
            "憧憬",
            "盼望",
            "信念",
            "坚信",
            "相信",
            "曙光",
            "未来",
        ],
        EmotionType.DESPAIR: [
            "绝望",
            "死心",
            "万念俱灰",
            "心如死灰",
            "放弃",
            "无力",
            "崩溃",
            "深渊",
            "黑暗",
            "毁灭",
        ],
        EmotionType.DETERMINATION: [
            "决心",
            "坚定",
            "执著",
            "坚持",
            "毅然",
            "誓",
            "必定",
            "一定要",
            "绝不",
            "定要",
        ],
        EmotionType.CONFUSION: [
            "困惑",
            "不解",
            "迷茫",
            "疑惑",
            "犹豫",
            "迟疑",
            "踌躇",
            "茫然",
            "不知所措",
            "疑惑不解",
        ],
        EmotionType.RELIEF: [
            "释然",
            "松口气",
            "放下",
            "解脱",
            "轻松",
            "如释重负",
            "安心",
            "踏实",
            "宽慰",
            "释怀",
        ],
        EmotionType.ANXIETY: [
            "焦虑",
            "不安",
            "担忧",
            "忐忑",
            "紧张",
            "心神不宁",
            "坐立不安",
            "忧虑",
            "烦躁",
            "焦急",
        ],
    }

    # 强度增强词
    INTENSITY_MODIFIERS: dict[str, float] = {
        "非常": 1.5,
        "极其": 1.8,
        "无比": 1.8,
        "极度": 2.0,
        "万分": 1.6,
        "十分": 1.3,
        "格外": 1.4,
        "略": 0.5,
        "稍微": 0.5,
        "有点": 0.6,
        "些许": 0.6,
    }

    @classmethod
    def analyze(cls, text: str, chapter: int, _character_name: str = "") -> list[EmotionPoint]:
        """分析文本中的情感点"""
        points: list[EmotionPoint] = []

        for emotion_type, keywords in cls.EMOTION_KEYWORDS.items():
            for kw in keywords:
                for match in re.finditer(kw, text):
                    # 获取上下文（前后各20字符）
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 20)
                    context = text[start:end]

                    # 计算强度
                    intensity = cls._calculate_intensity(context, emotion_type)

                    points.append(
                        EmotionPoint(
                            chapter=chapter,
                            emotion_type=emotion_type,
                            intensity=intensity,
                            trigger=f"关键词触发: {kw}",
                            context=context.strip(),
                        )
                    )

        return points

    @classmethod
    def _calculate_intensity(cls, context: str, emotion_type: EmotionType) -> EmotionIntensity:
        """根据上下文计算情感强度"""
        score = 1.0

        # 检查修饰词
        for modifier, multiplier in cls.INTENSITY_MODIFIERS.items():
            if modifier in context:
                score *= multiplier

        # 检查感叹号
        score += context.count("！") * 0.2
        score += context.count("!") * 0.1

        # 多关键词叠加
        keywords = cls.EMOTION_KEYWORDS.get(emotion_type, [])
        kw_count = sum(1 for kw in keywords if kw in context)
        score *= 1 + (kw_count - 1) * 0.3

        if score < 0.5:
            return EmotionIntensity.LOW
        if score < 1.2:
            return EmotionIntensity.MEDIUM
        if score < 2.0:
            return EmotionIntensity.HIGH
        return EmotionIntensity.EXTREME


# ══════════════════════════════════════════════════════
# 弧光追踪器
# ══════════════════════════════════════════════════════


class ArcTracker:
    """角色弧光追踪器"""

    # 特质变化关键词
    TRAIT_CHANGE_PATTERNS: dict[str, re.Pattern] = {
        "力量增强": re.compile(r"(突破|晋升|提升|增强|变强|进阶)"),
        "力量削弱": re.compile(r"(受伤|虚弱|损耗|跌落|退化|变弱)"),
        "自信增强": re.compile(r"(自信|坚定|笃定|相信自己|不再犹豫)"),
        "自信削弱": re.compile(r"(怀疑|动摇|犹豫|不确定|自我否定)"),
        "善良增强": re.compile(r"(善|仁慈|怜悯|不忍|恻隐|帮助)"),
        "冷酷增强": re.compile(r"(冷漠|无情|狠|杀|果断|决绝)"),
        "智慧增强": re.compile(r"(领悟|明悟|洞察|看透|理解|智慧)"),
    }

    DEFAULT_TRAITS: dict[str, dict[str, float]] = {
        "力量": {"baseline": 0.3, "arc": ArcDirection.POSITIVE.value},
        "自信": {"baseline": 0.5, "arc": ArcDirection.POSITIVE.value},
        "善良": {"baseline": 0.6, "arc": ArcDirection.FLAT.value},
        "智慧": {"baseline": 0.4, "arc": ArcDirection.POSITIVE.value},
        "冷酷": {"baseline": 0.2, "arc": ArcDirection.FLAT.value},
    }

    def __init__(self, book_id: str = ""):
        self.book_id = book_id
        self.arcs: dict[str, CharacterArc] = {}
        self._data_dir: Path | None = None
        if book_id:
            self._data_dir = settings.DATA_DIR / "arc" / book_id
            self._data_dir.mkdir(parents=True, exist_ok=True)

    def register_character(
        self,
        name: str,
        direction: ArcDirection = ArcDirection.POSITIVE,
        traits: dict[str, float] | None = None,
        chapter_introduced: int = 0,
    ) -> CharacterArc:
        """注册角色弧光"""
        trait_dict: dict[str, CharacterTrait] = {}
        if traits:
            for trait_name, strength in traits.items():
                trait_dict[trait_name] = CharacterTrait(
                    name=trait_name,
                    strength=strength,
                    baseline=strength,
                    chapter_recorded=chapter_introduced,
                )
        else:
            for trait_name, config in self.DEFAULT_TRAITS.items():
                trait_dict[trait_name] = CharacterTrait(
                    name=trait_name,
                    strength=config["baseline"],
                    baseline=config["baseline"],
                    chapter_recorded=chapter_introduced,
                )

        arc = CharacterArc(
            name=name,
            direction=direction,
            traits=trait_dict,
            emotion_line=EmotionLine(character_name=name),
            chapter_introduced=chapter_introduced,
        )
        arc.take_snapshot(chapter_introduced)
        self.arcs[name] = arc
        return arc

    def analyze_chapter(
        self, text: str, chapter: int, character_names: list[str] | None = None
    ) -> dict[str, ArcReport]:
        """分析章节中的角色弧光变化"""
        reports: dict[str, ArcReport] = {}

        targets = character_names or self.arcs.keys()
        for name in targets:
            if name not in self.arcs:
                continue

            arc = self.arcs[name]
            # 检查文本中是否出现该角色
            if name not in text:
                continue

            # 情感分析
            emotion_points = EmotionAnalyzer.analyze(text, chapter, name)
            for ep in emotion_points:
                if arc.emotion_line:
                    arc.emotion_line.add_point(ep)

            # 特质变化检测
            trait_changes = self._detect_trait_changes(text, arc, chapter)

            # 拍摄快照
            arc.take_snapshot(chapter)

            # 生成报告
            report = self._generate_report(arc, chapter, trait_changes)
            reports[name] = report

        self._save()
        return reports

    def _detect_trait_changes(self, text: str, arc: CharacterArc, chapter: int) -> list[dict]:
        """检测特质变化"""
        changes: list[dict] = []

        for change_name, pattern in self.TRAIT_CHANGE_PATTERNS.items():
            matches = list(pattern.finditer(text))
            if not matches:
                continue

            # 映射到特质
            if "力量" in change_name and "力量" in arc.traits:
                delta = 0.03 * len(matches) if "增强" in change_name else -0.03 * len(matches)
                arc.traits["力量"].strength = max(0, min(1, arc.traits["力量"].strength + delta))
                arc.traits["力量"].chapter_recorded = chapter
                changes.append(
                    {
                        "trait": "力量",
                        "change": round(delta, 2),
                        "new_value": round(arc.traits["力量"].strength, 2),
                        "trigger": change_name,
                    }
                )
            if "自信" in change_name and "自信" in arc.traits:
                delta = 0.02 * len(matches) if "增强" in change_name else -0.02 * len(matches)
                arc.traits["自信"].strength = max(0, min(1, arc.traits["自信"].strength + delta))
                arc.traits["自信"].chapter_recorded = chapter
                changes.append(
                    {
                        "trait": "自信",
                        "change": round(delta, 2),
                        "new_value": round(arc.traits["自信"].strength, 2),
                        "trigger": change_name,
                    }
                )
            if "善良" in change_name and "善良" in arc.traits:
                delta = 0.02 * len(matches) if "增强" in change_name else -0.02 * len(matches)
                arc.traits["善良"].strength = max(0, min(1, arc.traits["善良"].strength + delta))
                arc.traits["善良"].chapter_recorded = chapter
                changes.append(
                    {
                        "trait": "善良",
                        "change": round(delta, 2),
                        "new_value": round(arc.traits["善良"].strength, 2),
                        "trigger": change_name,
                    }
                )
            if "智慧" in change_name and "智慧" in arc.traits:
                delta = 0.02 * len(matches) if "增强" in change_name else -0.02 * len(matches)
                arc.traits["智慧"].strength = max(0, min(1, arc.traits["智慧"].strength + delta))
                arc.traits["智慧"].chapter_recorded = chapter
                changes.append(
                    {
                        "trait": "智慧",
                        "change": round(delta, 2),
                        "new_value": round(arc.traits["智慧"].strength, 2),
                        "trigger": change_name,
                    }
                )
            if "冷酷" in change_name and "冷酷" in arc.traits:
                delta = 0.02 * len(matches) if "增强" in change_name else -0.02 * len(matches)
                arc.traits["冷酷"].strength = max(0, min(1, arc.traits["冷酷"].strength + delta))
                arc.traits["冷酷"].chapter_recorded = chapter
                changes.append(
                    {
                        "trait": "冷酷",
                        "change": round(delta, 2),
                        "new_value": round(arc.traits["冷酷"].strength, 2),
                        "trigger": change_name,
                    }
                )

        return changes

    def _generate_report(
        self, arc: CharacterArc, chapter: int, trait_changes: list[dict]
    ) -> ArcReport:
        """生成弧光分析报告"""
        # 弧光进度（基于特质变化总量）
        total_delta = sum(abs(c["change"]) for c in trait_changes)
        if total_delta > 0.1:
            arc_progress = min(1.0, total_delta * 5)
        elif total_delta > 0.03:
            arc_progress = 0.3
        else:
            arc_progress = 0.1

        # 情感分布统计
        emotion_summary: dict[str, int] = {}
        if arc.emotion_line:
            from collections import Counter

            counts = Counter(p.emotion_type.value for p in arc.emotion_line.points[-20:])
            emotion_summary = dict(counts)

        # 弧光健康度
        arc_health = "normal"
        if not trait_changes and chapter - (arc.snapshots[-1].chapter if arc.snapshots else 0) > 10:
            arc_health = "stalled"
        elif total_delta > 0.3:
            arc_health = "rushed"

        # 建议
        suggestions: list[str] = []
        if arc_health == "stalled":
            suggestions.append(f"角色 {arc.name} 已超过10章无明显特质变化，考虑加入成长/冲突事件")
        if arc_health == "rushed":
            suggestions.append(f"角色 {arc.name} 本章特质变化过大，考虑分散到多章体现")
        if arc.direction in (ArcDirection.POSITIVE, ArcDirection.HEROIC):
            positive_traits = sum(1 for t in arc.traits.values() if t.strength > t.baseline)
            if positive_traits == 0 and chapter > arc.chapter_introduced + 5:
                suggestions.append(f"正向弧光角色 {arc.name} 尚未展现成长，考虑加入正向转折")

        return ArcReport(
            book_id=self.book_id,
            character_name=arc.name,
            direction=arc.direction,
            current_chapter=chapter,
            trait_changes=trait_changes,
            emotion_summary=emotion_summary,
            arc_progress=round(arc_progress, 2),
            arc_health=arc_health,
            suggestions=suggestions,
        )

    def get_emotion_curve(self, character_name: str, last_n: int = 20) -> list[dict]:
        """获取情感曲线"""
        arc = self.arcs.get(character_name)
        if not arc or not arc.emotion_line:
            return []
        return arc.emotion_line.get_intensity_curve(last_n)

    def get_trait_trend(self, character_name: str, trait_name: str) -> list[dict]:
        """获取特质趋势"""
        arc = self.arcs.get(character_name)
        if not arc:
            return []
        trend = arc.get_trait_trend(trait_name)
        return [{"chapter": ch, "value": val} for ch, val in trend]

    def _save(self):
        if not self._data_dir:
            return
        import json

        data: dict[str, Any] = {}
        for name, arc in self.arcs.items():
            data[name] = {
                "name": name,
                "direction": arc.direction.value,
                "traits": {
                    tn: {
                        "strength": t.strength,
                        "baseline": t.baseline,
                        "chapter_recorded": t.chapter_recorded,
                    }
                    for tn, t in arc.traits.items()
                },
                "snapshots": [
                    {"chapter": s.chapter, "traits": s.traits}
                    for s in arc.snapshots[-50:]  # 只保留最近50个快照
                ],
                "emotion_points": [
                    {
                        "chapter": ep.chapter,
                        "type": ep.emotion_type.value,
                        "intensity": ep.intensity.value,
                        "trigger": ep.trigger,
                    }
                    for ep in (arc.emotion_line.points[-100:] if arc.emotion_line else [])
                ],
                "chapter_introduced": arc.chapter_introduced,
            }
        save_json(self._data_dir / "arcs.json", data, pretty=True)

    def _load(self):
        if not self._data_dir:
            return
        data = load_json(self._data_dir / "arcs.json", default={})
        if not data:
            return
        try:
            for name, arc_data in data.items():
                direction = ArcDirection(arc_data["direction"])
                traits = {
                    tn: CharacterTrait(
                        name=tn,
                        strength=td["strength"],
                        baseline=td.get("baseline", 0.5),
                        chapter_recorded=td.get("chapter_recorded", 0),
                    )
                    for tn, td in arc_data["traits"].items()
                }
                arc = CharacterArc(
                    name=name,
                    direction=direction,
                    traits=traits,
                    chapter_introduced=arc_data.get("chapter_introduced", 0),
                )
                for snap in arc_data.get("snapshots", []):
                    arc.snapshots.append(
                        TraitSnapshot(
                            chapter=snap["chapter"],
                            traits=snap["traits"],
                        )
                    )
                arc.emotion_line = EmotionLine(character_name=name)
                for ep_data in arc_data.get("emotion_points", []):
                    arc.emotion_line.add_point(
                        EmotionPoint(
                            chapter=ep_data["chapter"],
                            emotion_type=EmotionType(ep_data["type"]),
                            intensity=EmotionIntensity(ep_data["intensity"]),
                            trigger=ep_data.get("trigger", ""),
                        )
                    )
                self.arcs[name] = arc
        except (KeyError, ValueError) as e:
            logger.warning(f"弧光数据加载失败: {e}")


# ══════════════════════════════════════════════════════
# 工厂函数
# ══════════════════════════════════════════════════════

_arc_trackers: dict[str, ArcTracker] = {}


def get_arc_tracker(book_id: str) -> ArcTracker:
    """获取弧光追踪器（单例）"""
    if book_id not in _arc_trackers:
        tracker = ArcTracker(book_id)
        tracker._load()
        _arc_trackers[book_id] = tracker
    return _arc_trackers[book_id]
