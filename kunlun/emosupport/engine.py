"""
emosupport 写作情感支持 — 写作瓶颈诊断、情绪追踪、里程碑庆祝

核心能力:
1. 写作瓶颈自动诊断（6类常见瓶颈）
2. 作者情绪追踪（写作速度、修改频率、卡顿时长）
3. 里程碑检测与庆祝（字数、连续写作天数）
4. 零LLM纯规则实现
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from loguru import logger

from kunlun.core.extension_base import BaseExtensionModule


class BlockReason(StrEnum):
    """写作瓶颈原因"""

    NO_IDEA = "no_idea"  # 不知道写什么
    PERFECTIONISM = "perfectionism"  # 完美主义（反复修改）
    FATIGUE = "fatigue"  # 疲劳
    PLOT_HOLE = "plot_hole"  # 剧情卡住
    CHARACTER_ISSUE = "character"  # 角色写不动
    EXTERNAL = "external"  # 外部干扰
    UNKNOWN = "unknown"  # 未知


class MilestoneType(StrEnum):
    """里程碑类型"""

    WORD_COUNT = "word_count"  # 字数里程碑
    STREAK = "streak"  # 连续写作天数
    CHAPTER = "chapter"  # 章节完成
    SPEED = "speed"  # 写作速度记录
    TOTAL_TIME = "total_time"  # 总写作时间


class WriterMood(StrEnum):
    """作者情绪状态"""

    FLOW = "flow"  # 心流状态
    STEADY = "steady"  # 稳定
    STRUGGLING = "struggling"  # 挣扎
    BLOCKED = "blocked"  # 卡文
    BURNT_OUT = "burnt_out"  # 倦怠


@dataclass
class WriterState:
    """作者写作状态快照"""

    timestamp: str = ""
    word_count: int = 0
    words_in_session: int = 0  # 本次写作会话字数
    session_duration_minutes: float = 0.0
    words_per_minute: float = 0.0
    edit_count: int = 0  # 修改次数
    mood: WriterMood = WriterMood.STEADY
    block_reason: BlockReason | None = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class BlockDiagnosis:
    """写作瓶颈诊断"""

    is_blocked: bool = False
    reason: BlockReason = BlockReason.UNKNOWN
    confidence: float = 0.0
    suggestions: list[str] = field(default_factory=list)
    blocked_duration_minutes: float = 0.0
    detail: str = ""


@dataclass
class Milestone:
    """写作里程碑"""

    milestone_type: MilestoneType
    value: str  # 里程碑值（如"10万字"）
    achieved_at: str = ""
    message: str = ""

    def __post_init__(self):
        if not self.achieved_at:
            self.achieved_at = datetime.now().isoformat()
        if not self.message:
            type_names = {
                MilestoneType.WORD_COUNT: "字数达成",
                MilestoneType.STREAK: "连续写作",
                MilestoneType.CHAPTER: "章节完成",
                MilestoneType.SPEED: "写作速度",
                MilestoneType.TOTAL_TIME: "总写作时间",
            }
            self.message = f"🎉 {type_names.get(self.milestone_type, '里程碑')}: {self.value}"


@dataclass
class EmoReport:
    """情感支持报告"""

    book_id: str
    current_mood: WriterMood = WriterMood.STEADY
    today_words: int = 0
    today_sessions: int = 0
    streak_days: int = 0
    total_words: int = 0
    average_wpm: float = 0.0
    block_diagnosis: BlockDiagnosis | None = None
    recent_milestones: list[Milestone] = field(default_factory=list)
    encouragement: str = ""

    def summary(self) -> str:
        return (
            f"写作状态: {self.current_mood.value}, "
            f"今日{self.today_words}字, "
            f"连续{self.streak_days}天, "
            f"总{self.total_words}字"
        )


class EmoSupport(BaseExtensionModule):
    """写作情感支持引擎"""

    # 瓶颈诊断阈值
    BLOCK_THRESHOLD_MINUTES = 15  # 15分钟无产出视为可能卡文
    LOW_SPEED_THRESHOLD = 5  # <5字/分钟
    HIGH_EDIT_RATIO = 0.5  # 修改比例>50%

    # 里程碑阈值
    WORD_MILESTONES = [1_0000, 3_0000, 5_0000, 10_0000, 20_0000, 50_0000, 100_0000]
    STREAK_MILESTONES = [3, 7, 14, 30, 60, 100, 365]

    def __init__(self, book_id: str = ""):
        super().__init__(book_id)
        self._states: list[WriterState] = []
        self._milestones: list[Milestone] = []
        self._total_words: int = 0
        self._sessions: list[dict[str, Any]] = []
        self._last_activity: datetime | None = None
        self._current_session_start: datetime | None = None
        self._current_session_words: int = 0

    def record_session(
        self,
        word_count: int,
        duration_minutes: float,
        edit_count: int = 0,
        _mood_hint: str = "",
    ) -> WriterState:
        """记录一次写作会话"""
        state = WriterState(
            word_count=word_count,
            words_in_session=word_count - self._current_session_words,
            session_duration_minutes=duration_minutes,
            words_per_minute=word_count / max(duration_minutes, 0.1),
            edit_count=edit_count,
        )

        # 情绪判定
        state.mood = self._detect_mood(state)

        # 瓶颈诊断
        if state.mood in (WriterMood.STRUGGLING, WriterMood.BLOCKED):
            state.block_reason = self._diagnose_block(state)

        self._states.append(state)
        self._total_words = word_count
        self._current_session_words = word_count
        self._last_activity = datetime.now()

        # 里程碑检测
        self._check_milestones()

        logger.info(
            f"写作会话记录: {state.words_in_session}字/"
            f"{duration_minutes:.0f}分钟, 情绪={state.mood.value}"
        )
        return state

    def _detect_mood(self, state: WriterState) -> WriterMood:
        """检测写作情绪"""
        wpm = state.words_per_minute

        if wpm >= 30:
            return WriterMood.FLOW
        if wpm >= 15:
            return WriterMood.STEADY
        if wpm >= 5:
            return WriterMood.STRUGGLING
        if (
            state.session_duration_minutes >= self.BLOCK_THRESHOLD_MINUTES
            and state.words_in_session < 50
        ):
            return WriterMood.BLOCKED
        return WriterMood.STRUGGLING

    def _diagnose_block(self, state: WriterState) -> BlockReason:
        """诊断写作瓶颈原因"""
        # 高修改率 = 完美主义
        if state.edit_count > 5 and state.words_in_session < 100:
            return BlockReason.PERFECTIONISM

        # 长时间低产出 = 疲劳
        if state.session_duration_minutes > 30 and state.words_per_minute < 3:
            return BlockReason.FATIGUE

        # 零产出 = 不知道写什么
        if state.words_in_session < 10 and state.session_duration_minutes > 10:
            return BlockReason.NO_IDEA

        return BlockReason.UNKNOWN

    def diagnose_current_block(self) -> BlockDiagnosis:
        """诊断当前是否卡文"""
        if not self._last_activity:
            return BlockDiagnosis(is_blocked=False)

        elapsed = (datetime.now() - self._last_activity).total_seconds() / 60
        if elapsed < self.BLOCK_THRESHOLD_MINUTES:
            return BlockDiagnosis(is_blocked=False)

        # 分析最近的写作状态
        recent_states = self._states[-5:] if len(self._states) >= 5 else self._states

        if not recent_states:
            return BlockDiagnosis(is_blocked=False)

        # 最近状态
        last_state = recent_states[-1]

        diagnosis = BlockDiagnosis(
            is_blocked=True,
            blocked_duration_minutes=elapsed,
        )

        if last_state.words_per_minute < self.LOW_SPEED_THRESHOLD:
            diagnosis.reason = BlockReason.FATIGUE
            diagnosis.confidence = 0.7
            diagnosis.suggestions = [
                "休息15分钟，喝杯水走一走",
                "换一个场景或音乐",
                "试试写一个简单的过渡段落",
            ]
        elif last_state.edit_count > 3 and last_state.words_in_session < 200:
            diagnosis.reason = BlockReason.PERFECTIONISM
            diagnosis.confidence = 0.8
            diagnosis.suggestions = [
                "先写完再改，不要边写边改",
                "设置一个'垃圾初稿'目标，允许自己写差",
                "用番茄钟法：25分钟只管写，不管质量",
            ]
        elif last_state.words_in_session < 50:
            diagnosis.reason = BlockReason.NO_IDEA
            diagnosis.confidence = 0.6
            diagnosis.suggestions = [
                "回到大纲看看下一个情节点",
                "写一个角色的内心独白",
                "跳到后面想写的场景先写着",
            ]
        else:
            diagnosis.reason = BlockReason.UNKNOWN
            diagnosis.confidence = 0.3
            diagnosis.suggestions = [
                "回顾一下前文，找找感觉",
                "看看读者的评论获取动力",
            ]

        diagnosis.detail = f"已卡文{elapsed:.0f}分钟，原因: {diagnosis.reason.value}"
        return diagnosis

    def _check_milestones(self) -> None:
        """检查是否达成里程碑"""
        # 字数里程碑
        for threshold in self.WORD_MILESTONES:
            if self._total_words >= threshold:
                milestone_key = f"words_{threshold}"
                if not any(
                    m.milestone_type == MilestoneType.WORD_COUNT and str(threshold) in m.value
                    for m in self._milestones
                ):
                    milestone = Milestone(
                        milestone_type=MilestoneType.WORD_COUNT,
                        value=f"{threshold // 10000}万字",
                    )
                    self._milestones.append(milestone)
                    logger.info(f"里程碑达成: {milestone.message}")

        # 连续天数
        streak = self.get_streak_days()
        for threshold in self.STREAK_MILESTONES:
            if streak >= threshold:
                milestone_key = f"streak_{threshold}"
                if not any(
                    m.milestone_type == MilestoneType.STREAK and str(threshold) in m.value
                    for m in self._milestones
                ):
                    milestone = Milestone(
                        milestone_type=MilestoneType.STREAK,
                        value=f"连续{threshold}天",
                    )
                    self._milestones.append(milestone)
                    logger.info(f"里程碑达成: {milestone.message}")

    def get_streak_days(self) -> int:
        """计算连续写作天数"""
        if not self._states:
            return 0

        # 按天分组
        days: set[str] = set()
        for state in self._states:
            if state.words_in_session > 0:
                dt = datetime.fromisoformat(state.timestamp)
                days.add(dt.strftime("%Y-%m-%d"))

        if not days:
            return 0

        # 从今天往回数连续天数
        today = datetime.now().strftime("%Y-%m-%d")
        sorted_days = sorted(days, reverse=True)

        if sorted_days[0] != today and sorted_days[0] != (
            datetime.now() - timedelta(days=1)
        ).strftime("%Y-%m-%d"):
            return 0  # 昨天和今天都没写

        streak = 1 if sorted_days[0] == today else 0
        for i in range(1, len(sorted_days)):
            d1 = datetime.strptime(sorted_days[i - 1], "%Y-%m-%d")
            d2 = datetime.strptime(sorted_days[i], "%Y-%m-%d")
            if (d1 - d2).days == 1:
                streak += 1
            else:
                break

        return streak

    def get_emo_report(self) -> EmoReport:
        """获取情感支持报告"""
        report = EmoReport(book_id=self.book_id)

        # 今日统计
        today = datetime.now().strftime("%Y-%m-%d")
        today_states = [
            s
            for s in self._states
            if datetime.fromisoformat(s.timestamp).strftime("%Y-%m-%d") == today
        ]
        report.today_sessions = len(today_states)
        report.today_words = sum(s.words_in_session for s in today_states)

        # 当前情绪
        if self._states:
            report.current_mood = self._states[-1].mood
            speeds = [s.words_per_minute for s in self._states[-10:] if s.words_per_minute > 0]
            report.average_wpm = sum(speeds) / len(speeds) if speeds else 0

        report.total_words = self._total_words
        report.streak_days = self.get_streak_days()

        # 瓶颈诊断
        report.block_diagnosis = self.diagnose_current_block()

        # 最近里程碑
        report.recent_milestones = self._milestones[-3:] if self._milestones else []

        # 鼓励语
        report.encouragement = self._generate_encouragement(report)

        logger.info(report.summary())
        return report

    def _generate_encouragement(self, report: EmoReport) -> str:
        """生成鼓励语"""
        if report.current_mood == WriterMood.FLOW:
            return "🔥 心流状态！继续保持，今天状态绝佳！"
        if report.current_mood == WriterMood.STEADY:
            return "💪 稳定输出，积少成多，每一字都算数。"
        if report.current_mood == WriterMood.STRUGGLING:
            return "🌱 慢一点也没关系，写下去就是胜利。"
        if report.current_mood == WriterMood.BLOCKED:
            return "🧘 卡文是创作的一部分，休息一下，灵感会来的。"
        if report.current_mood == WriterMood.BURNT_OUT:
            return "💤 今天好好休息吧，你已经写了很多了。明天继续！"

        if report.streak_days >= 7:
            return f"🏆 连续{report.streak_days}天！你已经很棒了！"
        if report.total_words >= 100000:
            return f"📚 {report.total_words // 10000}万字！这是一本书的体量了！"

        return "✨ 每一个字都在靠近终点，加油！"

    def get_milestones(self) -> list[Milestone]:
        """获取所有里程碑"""
        return self._milestones

    def get_stats(self) -> dict[str, Any]:
        """获取写作统计"""
        return {
            "total_words": self._total_words,
            "total_sessions": len(self._states),
            "streak_days": self.get_streak_days(),
            "average_wpm": (
                sum(s.words_per_minute for s in self._states) / max(len(self._states), 1)
                if self._states
                else 0
            ),
            "milestones_achieved": len(self._milestones),
            "current_mood": self._states[-1].mood.value if self._states else "unknown",
        }


_supports: dict[str, EmoSupport] = {}


def get_emo_support(book_id: str = "") -> EmoSupport:
    """获取情感支持实例"""
    if book_id not in _supports:
        _supports[book_id] = EmoSupport(book_id=book_id)
    return _supports[book_id]
