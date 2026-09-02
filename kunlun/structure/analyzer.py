"""
昆仑创作引擎 — 故事结构分析器

深度融合 Dramatica 理论 + Save the Cat 15节拍 + Hero's Journey 12阶段。
纯规则+简单NLP（jieba分词），零LLM成本基础分析；可选LLM增强。

与 architect.py 的 arc_stage 枚举完全对齐（英雄之旅12阶段）。

Author: 昆仑创作引擎
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar

# ══════════════════════════════════════════════════════════════════════
# 枚举定义 — 与 architect.py 对齐
# ══════════════════════════════════════════════════════════════════════


class SaveTheCatBeat(StrEnum):
    """Save the Cat 15节拍（Blake Snyder）"""

    OPENING_IMAGE = "opening_image"
    THEME_STATED = "theme_stated"
    SET_UP = "set_up"
    CATALYST = "catalyst"
    DEBATE = "debate"
    BREAK_INTO_TWO = "break_into_two"
    B_STORY = "b_story"
    FUN_AND_GAMES = "fun_and_games"
    MIDPOINT = "midpoint"
    BAD_GUYS_CLOSE_IN = "bad_guys_close_in"
    ALL_IS_LOST = "all_is_lost"
    DARK_NIGHT_OF_SOUL = "dark_night_of_soul"
    BREAK_INTO_THREE = "break_into_three"
    FINALE = "finale"
    FINAL_IMAGE = "final_image"

    @property
    def label(self) -> str:
        _labels = {
            "opening_image": "开场画面",
            "theme_stated": "主题陈述",
            "set_up": "铺垫",
            "catalyst": "催化剂",
            "debate": "辩论",
            "break_into_two": "进入第二幕",
            "b_story": "B故事",
            "fun_and_games": "玩乐时间",
            "midpoint": "中点",
            "bad_guys_close_in": "反派逼近",
            "all_is_lost": "失去一切",
            "dark_night_of_soul": "灵魂黑夜",
            "break_into_three": "进入第三幕",
            "finale": "终场",
            "final_image": "终场画面",
        }
        return _labels.get(self.value, self.value)


class HeroJourneyStage(StrEnum):
    """Hero's Journey 12阶段 — 与 architect.py arc_stage 完全对齐"""

    ORDINARY_WORLD = "ordinary_world"
    CALL_TO_ADVENTURE = "call_to_adventure"
    REFUSAL = "refusal"
    MENTOR = "mentor"
    CROSSING = "crossing"
    TESTS = "tests"
    APPROACH = "approach"
    ORDEAL = "ordeal"
    REWARD = "reward"
    ROAD_BACK = "road_back"
    RESURRECTION = "resurrection"
    RETURN = "return"

    @property
    def label(self) -> str:
        _labels = {
            "ordinary_world": "平凡世界",
            "call_to_adventure": "冒险召唤",
            "refusal": "拒绝召唤",
            "mentor": "遇见导师",
            "crossing": "跨越阈值",
            "tests": "考验之路",
            "approach": "接近核心",
            "ordeal": "磨难",
            "reward": "奖赏",
            "road_back": "归途",
            "resurrection": "复活",
            "return": "携宝归来",
        }
        return _labels.get(self.value, self.value)


class DramaticaPoint(StrEnum):
    """Dramatica 12个故事要点 — 网文适配版"""

    SETUP = "setup"
    INCITING_INCIDENT = "inciting_incident"
    FIRST_TURNING = "first_turning"
    RISING_ACTION = "rising_action"
    MIDPOINT = "midpoint"
    CRISIS = "crisis"
    CLIMAX = "climax"
    REVELATION = "revelation"
    DECISION = "decision"
    CONSEQUENCE = "consequence"
    RESOLUTION = "resolution"
    DENOUEMENT = "denouement"

    @property
    def label(self) -> str:
        _labels = {
            "setup": "建立",
            "inciting_incident": "激励事件",
            "first_turning": "第一转折",
            "rising_action": "上升行动",
            "midpoint": "中点",
            "crisis": "危机",
            "climax": "高潮",
            "revelation": "揭示",
            "decision": "决策",
            "consequence": "后果",
            "resolution": "解决",
            "denouement": "尾声",
        }
        return _labels.get(self.value, self.value)


# ══════════════════════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════════════════════


@dataclass
class BeatInfo:
    """单个节拍信息"""

    beat: SaveTheCatBeat
    name_cn: str
    position_pct: float  # 在故事中的预期位置（0-100%）
    description: str
    keywords: list[str] = field(default_factory=list)  # 特征关键词
    webnovel_note: str = ""  # 网文适配提示

    def match_score(self, text: str) -> float:
        """计算文本与该节拍的匹配度（0-1）"""
        if not self.keywords:
            return 0.0
        text_lower = text.lower()
        hits = sum(1 for kw in self.keywords if kw.lower() in text_lower)
        return min(hits / len(self.keywords), 1.0)


@dataclass
class TensionReport:
    """张力分析报告"""

    chapter_num: int
    tension_score: float  # 0-1
    is_flat: bool  # 是否平淡
    signals: dict[str, float]  # 各维度信号值
    summary: str


@dataclass
class StructureReport:
    """结构分析报告"""

    chapter_num: int
    total_chapters: int
    position_pct: float
    detected_beat_stc: SaveTheCatBeat | None = None
    detected_beat_dramatica: DramaticaPoint | None = None
    detected_stage_hero: HeroJourneyStage | None = None
    expected_beat_stc: SaveTheCatBeat | None = None
    expected_beat_dramatica: DramaticaPoint | None = None
    expected_stage_hero: HeroJourneyStage | None = None
    on_track: bool = True
    notes: list[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════
# BeatLibrary — 节拍库（三种理论体系）
# ══════════════════════════════════════════════════════════════════════


class BeatLibrary:
    """节拍库：Save the Cat + Hero's Journey + Dramatica 三种理论体系

    所有节拍数据均为静态类属性，零运行时开销。
    """

    # ── Save the Cat 15节拍 ──
    STC_BEATS: ClassVar[list[BeatInfo]] = [
        BeatInfo(
            SaveTheCatBeat.OPENING_IMAGE,
            "开场画面",
            0,
            "展示主角的平凡世界，定调整个故事",
            ["日常", "平凡", "正常生活", "日复一日"],
            "网文中通常是穿越前/重生前的日常生活",
        ),
        BeatInfo(
            SaveTheCatBeat.THEME_STATED,
            "主题陈述",
            5,
            "有人（通常不是主角）说出故事的主题",
            ["你知道", "真正的", "意义", "不是"],
            "常见形式：旁白/路人/配角的一句点题话",
        ),
        BeatInfo(
            SaveTheCatBeat.SET_UP,
            "铺垫",
            8,
            "主角的缺陷、缺失和需要改变的地方",
            ["缺点", "不足", "想要", "渴望"],
            "展示主角当前的问题和局限",
        ),
        BeatInfo(
            SaveTheCatBeat.CATALYST,
            "催化剂",
            10,
            "改变一切的事件发生，故事真正开始",
            ["突然", "变故", "穿越", "重生", "系统", "退婚", "觉醒"],
            "网文中典型：穿越/重生/系统激活/退婚/家族被灭",
        ),
        BeatInfo(
            SaveTheCatBeat.DEBATE,
            "辩论",
            15,
            "主角犹豫、挣扎，问自己'我能行吗？'",
            ["犹豫", "不确定", "害怕", "能不能"],
            "主角面对新环境的适应期",
        ),
        BeatInfo(
            SaveTheCatBeat.BREAK_INTO_TWO,
            "进入第二幕",
            20,
            "主角主动进入新世界，开始冒险",
            ["出发", "进入", "踏上", "前往", "离开"],
            "主角离开安全区，进入新地图",
        ),
        BeatInfo(
            SaveTheCatBeat.B_STORY,
            "B故事",
            22,
            "副线开始（通常是感情线或友情线）",
            ["遇见", "邂逅", "结识", "认识"],
            "重要配角的深度互动",
        ),
        BeatInfo(
            SaveTheCatBeat.FUN_AND_GAMES,
            "玩乐时间",
            35,
            "故事核心承诺的兑现，最有趣的部分",
            ["修炼", "战斗", "升级", "比试", "打脸"],
            "网文的'爽'主要集中在这一段",
        ),
        BeatInfo(
            SaveTheCatBeat.MIDPOINT,
            "中点",
            50,
            "假胜利或假失败，赌注升高",
            ["突破", "失败", "转折", "真相"],
            "看似赢了实则埋下更大隐患，或看似输了实则获得关键线索",
        ),
        BeatInfo(
            SaveTheCatBeat.BAD_GUYS_CLOSE_IN,
            "反派逼近",
            62,
            "反派力量增强，主角内部团队出现裂痕",
            ["背叛", "内奸", "压力", "困境"],
            "来自外部和内部的双重压力",
        ),
        BeatInfo(
            SaveTheCatBeat.ALL_IS_LOST,
            "失去一切",
            75,
            "主角跌入谷底，一切似乎都完了",
            ["失去", "绝望", "崩溃", "死亡"],
            "网文中常见的'绝境'描写",
        ),
        BeatInfo(
            SaveTheCatBeat.DARK_NIGHT_OF_SOUL,
            "灵魂黑夜",
            80,
            "主角在黑暗中反思，找到真正的力量",
            ["反思", "顿悟", "明白", "原来", "真相是"],
            "主角获得关键领悟/觉醒/突破",
        ),
        BeatInfo(
            SaveTheCatBeat.BREAK_INTO_THREE,
            "进入第三幕",
            85,
            "主角找到解决方案，重新出发",
            ["计划", "准备", "集结", "反攻"],
            "集结力量，准备最终决战",
        ),
        BeatInfo(
            SaveTheCatBeat.FINALE,
            "终场",
            92,
            "最终决战，解决问题",
            ["决战", "最终", "击败", "消灭"],
            "高潮决战",
        ),
        BeatInfo(
            SaveTheCatBeat.FINAL_IMAGE,
            "终场画面",
            100,
            "与开场画面呼应，展示主角的改变",
            ["结束", "新的", "未来", "开始"],
            "对比开场画面的改变",
        ),
    ]

    # ── Hero's Journey 12阶段 ──
    HERO_STAGES: ClassVar[dict[HeroJourneyStage, dict]] = {
        HeroJourneyStage.ORDINARY_WORLD: {
            "pct": 5,
            "label": "平凡世界",
            "keywords": ["日常", "平凡", "普通"],
        },
        HeroJourneyStage.CALL_TO_ADVENTURE: {
            "pct": 10,
            "label": "冒险召唤",
            "keywords": ["召唤", "使命", "改变"],
        },
        HeroJourneyStage.REFUSAL: {
            "pct": 15,
            "label": "拒绝召唤",
            "keywords": ["拒绝", "犹豫", "不"],
        },
        HeroJourneyStage.MENTOR: {
            "pct": 20,
            "label": "遇见导师",
            "keywords": ["师父", "老师", "教导"],
        },
        HeroJourneyStage.CROSSING: {
            "pct": 25,
            "label": "跨越阈值",
            "keywords": ["离开", "出发", "进入"],
        },
        HeroJourneyStage.TESTS: {
            "pct": 40,
            "label": "考验之路",
            "keywords": ["试炼", "考验", "挑战"],
        },
        HeroJourneyStage.APPROACH: {
            "pct": 55,
            "label": "接近核心",
            "keywords": ["深入", "接近", "核心"],
        },
        HeroJourneyStage.ORDEAL: {"pct": 65, "label": "磨难", "keywords": ["生死", "磨难", "绝境"]},
        HeroJourneyStage.REWARD: {"pct": 72, "label": "奖赏", "keywords": ["获得", "突破", "收获"]},
        HeroJourneyStage.ROAD_BACK: {
            "pct": 80,
            "label": "归途",
            "keywords": ["返回", "追杀", "归途"],
        },
        HeroJourneyStage.RESURRECTION: {
            "pct": 90,
            "label": "复活",
            "keywords": ["重生", "蜕变", "新生"],
        },
        HeroJourneyStage.RETURN: {
            "pct": 98,
            "label": "携宝归来",
            "keywords": ["归来", "结局", "圆满"],
        },
    }

    # ── Dramatica 12要点 ──
    DRAMATICA_POINTS: ClassVar[dict[DramaticaPoint, dict]] = {
        DramaticaPoint.SETUP: {"pct": 5, "label": "建立", "keywords": ["介绍", "背景", "世界"]},
        DramaticaPoint.INCITING_INCIDENT: {
            "pct": 12,
            "label": "激励事件",
            "keywords": ["变故", "触发", "开始"],
        },
        DramaticaPoint.FIRST_TURNING: {
            "pct": 25,
            "label": "第一转折",
            "keywords": ["转折", "改变", "方向"],
        },
        DramaticaPoint.RISING_ACTION: {
            "pct": 40,
            "label": "上升行动",
            "keywords": ["升级", "成长", "变强"],
        },
        DramaticaPoint.MIDPOINT: {"pct": 50, "label": "中点", "keywords": ["中点", "关键", "赌注"]},
        DramaticaPoint.CRISIS: {"pct": 70, "label": "危机", "keywords": ["危机", "困境", "两难"]},
        DramaticaPoint.CLIMAX: {"pct": 85, "label": "高潮", "keywords": ["决战", "巅峰", "对决"]},
        DramaticaPoint.REVELATION: {
            "pct": 90,
            "label": "揭示",
            "keywords": ["真相", "揭示", "原来"],
        },
        DramaticaPoint.DECISION: {"pct": 93, "label": "决策", "keywords": ["选择", "决定", "最终"]},
        DramaticaPoint.CONSEQUENCE: {
            "pct": 95,
            "label": "后果",
            "keywords": ["结果", "代价", "结局"],
        },
        DramaticaPoint.RESOLUTION: {
            "pct": 98,
            "label": "解决",
            "keywords": ["解决", "收尾", "了结"],
        },
        DramaticaPoint.DENOUEMENT: {
            "pct": 100,
            "label": "尾声",
            "keywords": ["尾声", "后记", "新的开始"],
        },
    }

    @classmethod
    def get_expected_beat(
        cls, position_pct: float
    ) -> tuple[SaveTheCatBeat, HeroJourneyStage, DramaticaPoint]:
        """根据位置百分比返回三种理论体系的预期节拍"""
        best_stc = cls.STC_BEATS[0].beat
        best_hero = HeroJourneyStage.ORDINARY_WORLD
        best_dramatica = DramaticaPoint.SETUP

        min_stc_dist = float("inf")
        for beat_info in cls.STC_BEATS:
            dist = abs(beat_info.position_pct - position_pct)
            if dist < min_stc_dist:
                min_stc_dist = dist
                best_stc = beat_info.beat

        min_hero_dist = float("inf")
        for stage, data in cls.HERO_STAGES.items():
            dist = abs(data["pct"] - position_pct)
            if dist < min_hero_dist:
                min_hero_dist = dist
                best_hero = stage

        min_dramatica_dist = float("inf")
        for point, data in cls.DRAMATICA_POINTS.items():
            dist = abs(data["pct"] - position_pct)
            if dist < min_dramatica_dist:
                min_dramatica_dist = dist
                best_dramatica = point

        return best_stc, best_hero, best_dramatica


# ══════════════════════════════════════════════════════════════════════
# TensionCurve — 张力曲线分析器
# ══════════════════════════════════════════════════════════════════════


class TensionCurve:
    """张力曲线分析器 — 基于多信号加权计算文本张力值

    信号维度（6维）：
      1. 冲突关键词密度
      2. 感叹号/问号密度（情绪强度）
      3. 短句比例（<10字，表示节奏加快）
      4. 动作动词密度
      5. 情感词强度
      6. 对话比例
    """

    CONFLICT_KEYWORDS: ClassVar[list[str]] = [
        "杀",
        "死",
        "战",
        "敌",
        "血",
        "怒",
        "恨",
        "仇",
        "危",
        "险",
        "偷袭",
        "攻击",
        "击败",
        "毁灭",
        "崩溃",
        "绝境",
        "背叛",
        "阴谋",
        "敌人",
        "对手",
        "威胁",
        "恐惧",
        "绝望",
        "搏斗",
        "厮杀",
        "拼命",
    ]

    ACTION_VERBS: ClassVar[list[str]] = [
        "冲",
        "飞",
        "斩",
        "砍",
        "刺",
        "劈",
        "轰",
        "爆",
        "闪",
        "跃",
        "释放",
        "凝聚",
        "爆发",
        "施展",
        "催动",
        "运转",
        "祭出",
        "一拳",
        "一剑",
        "一掌",
        "一击",
    ]

    EMOTION_WORDS: ClassVar[list[str]] = [
        "震惊",
        "骇然",
        "恐惧",
        "狂喜",
        "愤怒",
        "悲伤",
        "绝望",
        "激动",
        "紧张",
        "兴奋",
        "不安",
        "恐慌",
        "惊喜",
        "惊恐",
    ]

    def __init__(self) -> None:
        self._sentence_splitter = re.compile(r"[。！？!?…\n]+")
        self._short_sentence_len = 10

    def calculate_tension(self, text: str) -> TensionReport:
        """计算单段文本的张力值（0-1）"""
        if not text or len(text) < 10:
            return TensionReport(
                chapter_num=0, tension_score=0.0, is_flat=True, signals={}, summary="文本过短"
            )

        sentences = [s.strip() for s in self._sentence_splitter.split(text) if s.strip()]
        if not sentences:
            return TensionReport(
                chapter_num=0, tension_score=0.0, is_flat=True, signals={}, summary="无有效句子"
            )

        total_chars = len(text)
        total_sentences = len(sentences)

        # 1. 冲突关键词密度
        conflict_count = sum(1 for kw in self.CONFLICT_KEYWORDS if kw in text)
        conflict_density = min(conflict_count / max(total_sentences, 1) * 3, 1.0)

        # 2. 感叹号/问号密度
        exclam_question = len(re.findall(r"[！？!?]", text))
        emotion_punct_density = min(exclam_question / max(total_sentences, 1) * 2, 1.0)

        # 3. 短句比例
        short_count = sum(1 for s in sentences if len(s) < self._short_sentence_len)
        short_ratio = short_count / max(total_sentences, 1)

        # 4. 动作动词密度
        action_count = sum(1 for v in self.ACTION_VERBS if v in text)
        action_density = min(action_count / max(total_sentences, 1) * 2, 1.0)

        # 5. 情感词强度
        emotion_count = sum(1 for w in self.EMOTION_WORDS if w in text)
        emotion_density = min(emotion_count / max(total_sentences, 1) * 2, 1.0)

        # 6. 对话比例
        dialogue_chars = len(re.findall(r'[""][^""]*[""]', text)) + len(
            re.findall(r"「[^」]*」", text)
        )
        dialogue_ratio = min(dialogue_chars / max(total_chars, 1) * 3, 1.0)

        # 加权综合（冲突和动作权重更高）
        tension = (
            conflict_density * 0.25
            + emotion_punct_density * 0.15
            + short_ratio * 0.15
            + action_density * 0.20
            + emotion_density * 0.15
            + dialogue_ratio * 0.10
        )

        signals = {
            "conflict_density": round(conflict_density, 3),
            "emotion_punct_density": round(emotion_punct_density, 3),
            "short_sentence_ratio": round(short_ratio, 3),
            "action_density": round(action_density, 3),
            "emotion_density": round(emotion_density, 3),
            "dialogue_ratio": round(dialogue_ratio, 3),
        }

        is_flat = tension < 0.15
        summary = "平淡" if is_flat else ("紧张" if tension > 0.6 else "正常")

        return TensionReport(
            chapter_num=0,
            tension_score=round(tension, 3),
            is_flat=is_flat,
            signals=signals,
            summary=summary,
        )

    def analyze_curve(self, chapters: list[dict]) -> list[TensionReport]:
        """分析多章节的张力曲线"""
        reports = []
        for ch in chapters:
            report = self.calculate_tension(ch.get("text", ""))
            report.chapter_num = ch.get("num", 0)
            reports.append(report)
        return reports

    def detect_flat_spots(
        self, curve: list[TensionReport], threshold: float = 0.15, min_consecutive: int = 2
    ) -> list[tuple[int, int]]:
        """检测连续平淡段落 — 返回 [(start_ch, end_ch), ...]"""
        flat_ranges = []
        in_flat = False
        start = 0

        for _i, report in enumerate(curve):
            if report.is_flat or report.tension_score < threshold:
                if not in_flat:
                    in_flat = True
                    start = report.chapter_num
            elif in_flat:
                length = report.chapter_num - start
                if length >= min_consecutive:
                    flat_ranges.append((start, report.chapter_num - 1))
                in_flat = False

        if in_flat:
            length = curve[-1].chapter_num - start + 1
            if length >= min_consecutive:
                flat_ranges.append((start, curve[-1].chapter_num))

        return flat_ranges

    def suggest_boost(self, tension_report: TensionReport) -> str:
        """为低张力章节建议增强方案"""
        signals = tension_report.signals
        suggestions = []

        if signals.get("conflict_density", 0) < 0.2:
            suggestions.append("增加冲突场景或反派压力")
        if signals.get("action_density", 0) < 0.15:
            suggestions.append("添加动作/战斗场景")
        if signals.get("emotion_density", 0) < 0.1:
            suggestions.append("增强情感描写，加入角色内心波动")
        if signals.get("dialogue_ratio", 0) > 0.5:
            suggestions.append("对话过多，考虑加入叙事推进")
        if signals.get("short_sentence_ratio", 0) < 0.2:
            suggestions.append("增加短句比例，提升节奏感")

        if not suggestions:
            suggestions.append("整体张力尚可，可微调细节")
        return "；".join(suggestions)


# ══════════════════════════════════════════════════════════════════════
# PlotPointDetector — 情节点检测器
# ══════════════════════════════════════════════════════════════════════


class PlotPointDetector:
    """情节点检测器 — 检测转折点/高潮/伏笔-回收配对/场景类型"""

    TURNING_POINT_MARKERS: ClassVar[list[str]] = [
        "突然",
        "就在这时",
        "然而",
        "不料",
        "没想到",
        "谁知",
        "忽然",
        "意外地",
        "竟然",
        "居然",
        "怎么会",
    ]

    CLIMAX_MARKERS: ClassVar[list[str]] = [
        "决战",
        "最终",
        "最后一击",
        "生死",
        "巅峰",
        "终极",
        "全力",
        "最强",
        "底牌",
        "绝招",
    ]

    FORESHADOW_MARKERS: ClassVar[list[str]] = [
        "日后",
        "后来才知道",
        "当时并不知道",
        "命运的齿轮",
        "多年以后",
        "很久以后",
        "伏笔",
    ]

    PAYOFF_MARKERS: ClassVar[list[str]] = [
        "终于明白",
        "原来如此",
        "怪不得",
        "竟然是",
        "真相是",
        "这才知道",
        "恍然大悟",
    ]

    def __init__(self) -> None:
        self._sentence_splitter = re.compile(r"[。！？!?\n]+")

    def detect_turning_points(self, text: str) -> list[dict]:
        """检测转折点"""
        sentences = [s.strip() for s in self._sentence_splitter.split(text) if s.strip()]
        turning_points = []

        for i, sent in enumerate(sentences):
            score = 0
            matched = []
            for marker in self.TURNING_POINT_MARKERS:
                if marker in sent:
                    score += 1
                    matched.append(marker)
            if score >= 1:
                turning_points.append(
                    {
                        "position": i,
                        "text": sent[:80],
                        "score": score,
                        "markers": matched,
                    }
                )

        return turning_points

    def detect_climax_candidates(self, text: str) -> list[dict]:
        """检测高潮候选段落"""
        sentences = [s.strip() for s in self._sentence_splitter.split(text) if s.strip()]
        candidates = []

        for i, sent in enumerate(sentences):
            score = 0
            matched = []
            for marker in self.CLIMAX_MARKERS:
                if marker in sent:
                    score += 1
                    matched.append(marker)
            if score >= 2:
                candidates.append(
                    {
                        "position": i,
                        "text": sent[:100],
                        "score": score,
                        "markers": matched,
                    }
                )

        return candidates

    def detect_setup_payoff_pairs(self, chapters: list[dict]) -> list[dict]:
        """检测伏笔-回收配对"""
        pairs = []
        setups = []  # (ch_num, text, marker)

        for ch in chapters:
            text = ch.get("text", "")
            ch_num = ch.get("num", 0)
            sentences = [s.strip() for s in self._sentence_splitter.split(text) if s.strip()]

            for sent in sentences:
                setups.extend(
                    (ch_num, sent[:100], marker)
                    for marker in self.FORESHADOW_MARKERS
                    if marker in sent
                )

                for marker in self.PAYOFF_MARKERS:
                    if marker in sent and setups:
                        last_setup = setups[-1]
                        pairs.append(
                            {
                                "setup_ch": last_setup[0],
                                "setup_text": last_setup[1],
                                "payoff_ch": ch_num,
                                "payoff_text": sent[:100],
                                "distance": ch_num - last_setup[0],
                            }
                        )

        return pairs

    def classify_scene(self, text: str) -> str:
        """场景分类：action/dialogue/description/internal_monologue/transition"""
        total_chars = len(text)
        if total_chars < 20:
            return "transition"

        dialogue_chars = len(re.findall(r'[""][^""]{2,}[""]', text)) + len(
            re.findall(r"「[^」]{2,}」", text)
        )
        dialogue_ratio = dialogue_chars / max(total_chars, 1)

        internal_chars = len(re.findall(r"(心想|暗想|心中|内心|暗道|默念)", text))
        internal_ratio = internal_chars / max(total_chars, 1) * 10

        action_count = sum(1 for v in TensionCurve.ACTION_VERBS if v in text)
        action_ratio = action_count / max(total_chars, 1) * 100

        if dialogue_ratio > 0.4:
            return "dialogue"
        if internal_ratio > 0.3:
            return "internal_monologue"
        if action_ratio > 0.02:
            return "action"
        if total_chars < 100:
            return "transition"
        return "description"


# ══════════════════════════════════════════════════════════════════════
# StoryStructureAnalyzer — 主分析器
# ══════════════════════════════════════════════════════════════════════


class StoryStructureAnalyzer:
    """故事结构分析器 — 主入口

    整合 BeatLibrary + TensionCurve + PlotPointDetector。
    纯规则分析（零LLM成本），可选LLM增强模式。
    """

    def __init__(self) -> None:
        self.beat_library = BeatLibrary()
        self.tension_curve = TensionCurve()
        self.plot_detector = PlotPointDetector()

    def analyze_chapter(self, text: str, chapter_num: int, total_chapters: int) -> StructureReport:
        """分析单章结构 — 识别当前章节处于哪个叙事阶段"""
        position_pct = (chapter_num / max(total_chapters, 1)) * 100
        expected_stc, expected_hero, expected_dramatica = BeatLibrary.get_expected_beat(
            position_pct
        )

        # 检测实际节拍（基于关键词匹配）
        detected_stc = self._detect_stc_beat(text)
        detected_hero = self._detect_hero_stage(text)
        detected_dramatica = self._detect_dramatica_point(text)

        # 是否在轨道上
        on_track = True
        notes = []

        if detected_stc and detected_stc != expected_stc:
            dist = abs(position_pct - self._get_stc_position(detected_stc))
            if dist > 15:
                on_track = False
                notes.append(
                    f"节拍偏离预期 {dist:.0f}%"
                    f"（检测到{detected_stc.label}，预期{expected_stc.label}）"
                )

        if detected_dramatica and detected_dramatica != expected_dramatica:
            dist = abs(
                position_pct
                - BeatLibrary.DRAMATICA_POINTS.get(detected_dramatica, {}).get("pct", 50)
            )
            if dist > 15:
                notes.append(f"Dramatica阶段偏离（检测到{detected_dramatica.label}）")

        return StructureReport(
            chapter_num=chapter_num,
            total_chapters=total_chapters,
            position_pct=round(position_pct, 1),
            detected_beat_stc=detected_stc,
            detected_beat_dramatica=detected_dramatica,
            detected_stage_hero=detected_hero,
            expected_beat_stc=expected_stc,
            expected_beat_dramatica=expected_dramatica,
            expected_stage_hero=expected_hero,
            on_track=on_track,
            notes=notes,
        )

    def get_structure_progress(self, all_chapters: list[dict]) -> list[StructureReport]:
        """全局结构进度分析"""
        total = len(all_chapters)
        return [
            self.analyze_chapter(ch.get("text", ""), ch.get("num", i + 1), total)
            for i, ch in enumerate(all_chapters)
        ]

    def check_structure_health(self, reports: list[StructureReport]) -> dict:
        """结构健康度检查"""
        missing_beats = []
        found_beats = set()

        for r in reports:
            if r.detected_beat_stc:
                found_beats.add(r.detected_beat_stc)

        for beat_info in BeatLibrary.STC_BEATS:
            if beat_info.beat not in found_beats and beat_info.position_pct > 5:
                chapter_range = f"第{int(beat_info.position_pct / 100 * len(reports))}章"
                missing_beats.append(
                    {
                        "beat": beat_info.beat.value,
                        "name": beat_info.name_cn,
                        "expected_around": chapter_range,
                        "importance": "high"
                        if beat_info.position_pct in (10, 20, 50, 75, 85)
                        else "medium",
                    }
                )

        off_track = [r for r in reports if not r.on_track]

        return {
            "total_chapters": len(reports),
            "missing_beats": missing_beats,
            "missing_count": len(missing_beats),
            "off_track_chapters": [r.chapter_num for r in off_track],
            "off_track_count": len(off_track),
            "health_score": max(0, 100 - len(missing_beats) * 5 - len(off_track) * 3),
            "summary": self._generate_health_summary(missing_beats, off_track),
        }

    def suggest_next_beat(self, chapter_num: int, total_chapters: int) -> dict:
        """建议下一个节拍"""
        position_pct = (chapter_num / max(total_chapters, 1)) * 100

        # 找最近的后续节拍
        next_beat = None
        for beat_info in BeatLibrary.STC_BEATS:
            if beat_info.position_pct > position_pct:
                next_beat = beat_info
                break

        if next_beat is None:
            next_beat = BeatLibrary.STC_BEATS[-1]

        # 生成建议
        suggestions = []
        if next_beat.beat == SaveTheCatBeat.CATALYST:
            suggestions = [
                "安排一个改变主角命运的关键事件",
                "常见形式：系统激活/穿越/重生/退婚/意外获宝",
            ]
        elif next_beat.beat == SaveTheCatBeat.BREAK_INTO_TWO:
            suggestions = ["主角主动离开舒适区", "进入新地图/新境界/新阶段"]
        elif next_beat.beat == SaveTheCatBeat.MIDPOINT:
            suggestions = ["设置一个假胜利或假失败", "提高赌注，让后续更紧张"]
        elif next_beat.beat == SaveTheCatBeat.ALL_IS_LOST:
            suggestions = ["让主角经历一次重大失败", "失去重要的人/物/机会"]
        elif next_beat.beat == SaveTheCatBeat.FINALE:
            suggestions = ["准备最终决战", "回收主要伏笔"]
        else:
            suggestions = [
                "按照大纲继续推进情节",
                f"确保当前阶段{next_beat.name_cn}的核心要素得到体现",
            ]

        return {
            "next_beat": next_beat.beat.value,
            "next_beat_name": next_beat.name_cn,
            "position_pct": next_beat.position_pct,
            "chapters_until": max(
                0, int(next_beat.position_pct / 100 * total_chapters) - chapter_num
            ),
            "suggestions": suggestions,
        }

    # ── 私有方法 ──

    def _detect_stc_beat(self, text: str) -> SaveTheCatBeat | None:
        """检测文本命中了哪个 STC 节拍"""
        best_beat = None
        best_score = 0.0
        for beat_info in BeatLibrary.STC_BEATS:
            score = beat_info.match_score(text)
            if score > best_score and score > 0.15:
                best_score = score
                best_beat = beat_info.beat
        return best_beat

    def _detect_hero_stage(self, text: str) -> HeroJourneyStage | None:
        """检测英雄之旅阶段"""
        best_stage = None
        best_score = 0.0
        for stage, data in BeatLibrary.HERO_STAGES.items():
            hits = sum(1 for kw in data["keywords"] if kw in text)
            score = hits / max(len(data["keywords"]), 1)
            if score > best_score and score > 0.2:
                best_score = score
                best_stage = stage
        return best_stage

    def _detect_dramatica_point(self, text: str) -> DramaticaPoint | None:
        """检测 Dramatica 阶段"""
        best_point = None
        best_score = 0.0
        for point, data in BeatLibrary.DRAMATICA_POINTS.items():
            hits = sum(1 for kw in data["keywords"] if kw in text)
            score = hits / max(len(data["keywords"]), 1)
            if score > best_score and score > 0.2:
                best_score = score
                best_point = point
        return best_point

    @staticmethod
    def _get_stc_position(beat: SaveTheCatBeat) -> float:
        for info in BeatLibrary.STC_BEATS:
            if info.beat == beat:
                return info.position_pct
        return 50.0

    @staticmethod
    def _generate_health_summary(missing_beats: list, off_track: list) -> str:
        if not missing_beats and not off_track:
            return "结构健康，所有关键节拍均已覆盖。"
        parts = []
        if missing_beats:
            names = [b["name"] for b in missing_beats[:3]]
            parts.append(f"缺失{len(missing_beats)}个节拍：{'、'.join(names)}")
        if off_track:
            parts.append(f"{len(off_track)}章偏离轨道")
        return "；".join(parts)


# ══════════════════════════════════════════════════════════════════════
# 模块级便捷实例
# ══════════════════════════════════════════════════════════════════════

structure_analyzer = StoryStructureAnalyzer()
tension_curve = TensionCurve()
plot_detector = PlotPointDetector()
