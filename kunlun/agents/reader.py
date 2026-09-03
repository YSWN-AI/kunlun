"""
昆仑创作引擎 — 模拟读者 Agent (ReaderAgent)

模拟不同类型读者的阅读体验，包括：
  - 逐段情绪反应记录（emotional_timeline）
  - 弃书点预测（drop_off_point / drop_off_reason）
  - 读者评论模拟（LLM 增强 + 模板回退）
  - 多画像同时模拟（simulate_multiple）

读者画像（11种）：
  现有6种：小白读者、老白读者、付费读者、女频读者、挑剔读者、休闲读者
  新增5种：学生党、上班族、硬核爽文读者、女频言情读者、科幻爱好者
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from kunlun.agents.base import AgentMessage, BaseAgent
from kunlun.agents.message_bus import message_bus
from kunlun.debate_review.engine import (
    ReaderFeedback,
    ReaderSimulationResult,
    ReaderType,
    RuleBasedQualityChecker,
)

# ══════════════════════════════════════════════════════
# 扩展读者类型
# ══════════════════════════════════════════════════════


class ExtendedReaderType(Enum):
    """扩展读者类型枚举（11种）

    在现有6种基础上增加5种：学生党、上班族、硬核爽文读者、女频言情读者、科幻爱好者
    """

    NEWBIE = "newbie"  # 小白读者
    VETERAN = "veteran"  # 老白读者
    PAYING = "paying"  # 付费读者
    FEMALE = "female"  # 女频读者
    CRITICAL = "critical"  # 挑剔读者
    CASUAL = "casual"  # 休闲读者
    STUDENT = "student"  # 学生党（新增）
    OFFICE_WORKER = "office_worker"  # 上班族（新增）
    HARDCORE_COOL = "hardcore_cool"  # 硬核爽文读者（新增）
    ROMANCE_LOVER = "romance_lover"  # 女频言情读者（新增）
    SCIFI_FAN = "scifi_fan"  # 科幻爱好者（新增）


# 扩展读者画像配置
EXTENDED_READER_PROFILES: dict[ExtendedReaderType, dict[str, Any]] = {
    ExtendedReaderType.NEWBIE: {
        "name": "小白读者",
        "description": "刚接触网文，追求简单直接的爽感，耐心较低",
        "cool_threshold": 4.0,
        "patience": 0.4,
        "pacing_preference": "fast",
        "forgiveness": 0.7,
    },
    ExtendedReaderType.VETERAN: {
        "name": "老白读者",
        "description": "阅读经验丰富，追求逻辑和创新，对套路敏感",
        "cool_threshold": 3.0,
        "patience": 0.7,
        "pacing_preference": "medium",
        "forgiveness": 0.4,
    },
    ExtendedReaderType.PAYING: {
        "name": "付费读者",
        "description": "愿意付费，追求稳定更新和持续爽感，对质量要求高",
        "cool_threshold": 3.5,
        "patience": 0.6,
        "pacing_preference": "medium",
        "forgiveness": 0.5,
    },
    ExtendedReaderType.FEMALE: {
        "name": "女频读者",
        "description": "偏好情感线和人物关系，对感情描写敏感",
        "cool_threshold": 3.0,
        "patience": 0.6,
        "pacing_preference": "medium",
        "forgiveness": 0.5,
    },
    ExtendedReaderType.CRITICAL: {
        "name": "挑剔读者",
        "description": "对文笔和逻辑要求极高，容易弃书",
        "cool_threshold": 2.5,
        "patience": 0.3,
        "pacing_preference": "medium",
        "forgiveness": 0.2,
    },
    ExtendedReaderType.CASUAL: {
        "name": "休闲读者",
        "description": "随便看看，要求不高，容易被爽点吸引",
        "cool_threshold": 5.0,
        "patience": 0.5,
        "pacing_preference": "fast",
        "forgiveness": 0.8,
    },
    # ── 新增5种读者画像 ──────────────────────────────
    ExtendedReaderType.STUDENT: {
        "name": "学生党",
        "description": "在校学生，时间碎片化，喜欢校园/逆袭/系统流题材，代入感强",
        "cool_threshold": 4.5,
        "patience": 0.45,
        "pacing_preference": "fast",
        "forgiveness": 0.65,
    },
    ExtendedReaderType.OFFICE_WORKER: {
        "name": "上班族",
        "description": "通勤/午休阅读，追求解压和轻松，偏好职场/都市/轻松向",
        "cool_threshold": 3.8,
        "patience": 0.5,
        "pacing_preference": "medium",
        "forgiveness": 0.6,
    },
    ExtendedReaderType.HARDCORE_COOL: {
        "name": "硬核爽文读者",
        "description": "只看爽文，要求高密度打脸和逆袭，对逻辑容忍度高但对爽点要求极高",
        "cool_threshold": 6.0,
        "patience": 0.35,
        "pacing_preference": "fast",
        "forgiveness": 0.75,
    },
    ExtendedReaderType.ROMANCE_LOVER: {
        "name": "女频言情读者",
        "description": "专注言情小说，重视感情线发展和CP感，对虐恋/甜宠有明确偏好",
        "cool_threshold": 2.5,
        "patience": 0.65,
        "pacing_preference": "medium",
        "forgiveness": 0.55,
    },
    ExtendedReaderType.SCIFI_FAN: {
        "name": "科幻爱好者",
        "description": "喜欢科幻/设定流，重视世界观严谨性和创意，对硬科幻设定有要求",
        "cool_threshold": 2.0,
        "patience": 0.75,
        "pacing_preference": "medium",
        "forgiveness": 0.45,
    },
}


# ══════════════════════════════════════════════════════
# 增强读者反馈数据类
# ══════════════════════════════════════════════════════


@dataclass
class EnhancedReaderFeedback:
    """增强读者反馈（含情绪时间线）

    在 ReaderFeedback 基础上增加 emotional_timeline 字段，
    记录逐段阅读的情绪反应。
    """

    reader_type: ExtendedReaderType
    reader_name: str
    overall_score: float  # 0-10
    continue_reading: bool
    drop_off_point: str = ""
    drop_off_reason: str = ""
    likes: list[str] = field(default_factory=list)
    dislikes: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    emotional_response: str = ""
    cool_point_satisfaction: float = 0.0
    pacing_satisfaction: float = 0.0
    emotional_timeline: list[dict[str, Any]] = field(default_factory=list)
    chapter: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["reader_type"] = self.reader_type.value
        return data

    def to_reader_feedback(self) -> ReaderFeedback:
        """转换为兼容的 ReaderFeedback"""
        return ReaderFeedback(
            reader_type=ReaderType(self.reader_type.value)
            if self.reader_type.value in {t.value for t in ReaderType}
            else ReaderType.CASUAL,
            reader_name=self.reader_name,
            overall_score=self.overall_score,
            continue_reading=self.continue_reading,
            drop_off_point=self.drop_off_point,
            drop_off_reason=self.drop_off_reason,
            likes=self.likes,
            dislikes=self.dislikes,
            comments=self.comments,
            emotional_response=self.emotional_response,
            cool_point_satisfaction=self.cool_point_satisfaction,
            pacing_satisfaction=self.pacing_satisfaction,
        )


# ══════════════════════════════════════════════════════
# ReaderAgent
# ══════════════════════════════════════════════════════


class ReaderAgent(BaseAgent):
    """模拟读者 Agent

    逐段模拟阅读体验，记录情绪时间线，预测弃书点，
    生成个性化读者评论（LLM 增强 + 模板回退）。
    """

    agent_name = "reader"
    agent_id = "reader"
    name = "模拟读者"

    # 情绪关键词映射（用于规则-based 情绪检测）
    EMOTION_KEYWORDS: dict[str, list[str]] = {
        "兴奋": ["震惊", "倒吸", "突破", "觉醒", "秒杀", "碾压", "爆", "轰"],
        "愤怒": ["怒", "恨", "咬牙", "愤怒", "怒火", "震怒"],
        "悲伤": ["悲", "痛", "泪", "哭", "凄凉", "哀伤"],
        "紧张": ["突然", "就在这时", "危机", "危险", "紧张", "屏住"],
        "期待": ["期待", "即将", "终于", "等待", "悬念", "未知"],
        "满足": ["爽", "过瘾", "痛快", "解气", "舒服", "畅快"],
        "无聊": ["话说", "且说", "闲话", "不知不觉", "时光飞逝"],
        "疑惑": ["难道", "究竟", "到底", "怎么回事", "为什么"],
    }

    def __init__(self, reader_type: ExtendedReaderType = ExtendedReaderType.CASUAL) -> None:
        super().__init__()
        self.reader_type = reader_type
        self.profile: dict[str, Any] = EXTENDED_READER_PROFILES[reader_type]
        self.rule_checker = RuleBasedQualityChecker()

    # ── BaseAgent 抽象方法实现 ──────────────────────────

    async def on_message(self, msg: AgentMessage) -> AgentMessage | None:
        """处理接收到的消息"""
        if msg.msg_type == "READ_REQUEST":
            text = msg.payload.get("text", "")
            chapter = msg.payload.get("chapter", 0)
            feedback = await self.read(text, chapter)
            await self.publish_feedback(feedback)
            return AgentMessage(
                from_agent=self.agent_name,
                to_agent=msg.from_agent,
                msg_type="READ_RESULT",
                payload=feedback.to_dict(),
                correlation_id=msg.correlation_id,
            )
        return None

    async def execute(self, task: dict) -> dict:
        """执行阅读模拟任务"""
        text = task.get("text", "")
        chapter = task.get("chapter", 0)
        feedback = await self.read(text, chapter)
        return feedback.to_dict()

    # ── 核心阅读模拟方法 ────────────────────────────────

    async def read(self, text: str, chapter: int = 0) -> EnhancedReaderFeedback:
        """逐段模拟阅读体验

        Args:
            text: 章节文本
            chapter: 章节号

        Returns:
            EnhancedReaderFeedback 增强读者反馈
        """
        if not text or not text.strip():
            return self._empty_feedback(chapter)

        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        total_chars = len(text.replace(" ", "").replace("\n", ""))

        # 1. 逐段情绪时间线
        emotional_timeline = self._build_emotional_timeline(paragraphs)

        # 2. 爽点密度计算
        cool_count = sum(text.count(k) for k in self.rule_checker.COOL_KEYWORDS)
        cool_density = cool_count / max(1, total_chars / 1000)
        cool_satisfaction = min(1.0, cool_density / self.profile["cool_threshold"])

        # 3. 节奏满足度
        sentences = re.split(r"(?<=[。！？])", text)
        sentences = [s for s in sentences if s.strip()]
        avg_len = total_chars / max(1, len(sentences))
        if self.profile["pacing_preference"] == "fast":
            pacing_satisfaction = max(0.0, 1.0 - abs(avg_len - 15) / 30)
        else:
            pacing_satisfaction = max(0.0, 1.0 - abs(avg_len - 25) / 30)

        # 4. 规则问题检测
        issues = self.rule_checker.check(text, chapter)
        severe_issues = [i for i in issues if i.severity >= 3]
        issue_penalty = len(severe_issues) * (1 - self.profile["forgiveness"]) * 0.5

        # 5. 综合评分（0-10）
        base_score = 7.0
        score = (
            base_score
            + cool_satisfaction * 1.5
            + pacing_satisfaction * 1.0
            - issue_penalty
        )
        score = max(1.0, min(10.0, score))

        # 6. 是否继续阅读
        continue_reading = score >= 6.0 and cool_satisfaction >= 0.3

        # 7. 弃书点预测
        drop_off_point, drop_off_reason = self._predict_drop_off(
            continue_reading, cool_satisfaction, issue_penalty, severe_issues, emotional_timeline
        )

        # 8. 喜好/厌恶
        likes, dislikes = self._build_likes_dislikes(
            cool_satisfaction, pacing_satisfaction, severe_issues, emotional_timeline
        )

        # 9. 情感反应
        emotional_response = self._generate_emotional_response(cool_satisfaction, score)

        # 10. 读者评论（LLM 增强 + 模板回退）
        comments = await self._generate_comments(score, likes, dislikes, text[:500])

        return EnhancedReaderFeedback(
            reader_type=self.reader_type,
            reader_name=self.profile["name"],
            overall_score=round(score, 1),
            continue_reading=continue_reading,
            drop_off_point=drop_off_point,
            drop_off_reason=drop_off_reason,
            likes=likes,
            dislikes=dislikes,
            comments=comments,
            emotional_response=emotional_response,
            cool_point_satisfaction=round(cool_satisfaction, 2),
            pacing_satisfaction=round(pacing_satisfaction, 2),
            emotional_timeline=emotional_timeline,
            chapter=chapter,
        )

    async def simulate_multiple(
        self, text: str, reader_types: list[ExtendedReaderType]
    ) -> ReaderSimulationResult:
        """多画像同时模拟

        Args:
            text: 章节文本
            reader_types: 要模拟的读者类型列表

        Returns:
            ReaderSimulationResult 读者模拟结果汇总
        """
        if not reader_types:
            reader_types = [
                ExtendedReaderType.NEWBIE,
                ExtendedReaderType.VETERAN,
                ExtendedReaderType.PAYING,
                ExtendedReaderType.CRITICAL,
                ExtendedReaderType.CASUAL,
            ]

        readers: list[ReaderFeedback] = []
        for rtype in reader_types:
            agent = ReaderAgent(rtype)
            feedback = await agent.read(text)
            readers.append(feedback.to_reader_feedback())

        # 汇总统计
        avg_score = sum(r.overall_score for r in readers) / len(readers)
        continue_rate = sum(1 for r in readers if r.continue_reading) / len(readers)
        avg_cool = sum(r.cool_point_satisfaction for r in readers) / len(readers)

        # 共同喜好/厌恶
        all_likes = [l for r in readers for l in r.likes]
        all_dislikes = [d for r in readers for d in r.dislikes]
        common_likes = list(set(all_likes))[:5]
        common_dislikes = list(set(all_dislikes))[:5]

        # 弃书风险
        drop_off_count = sum(1 for r in readers if not r.continue_reading)
        drop_off_risk = drop_off_count / len(readers)

        summary = self._generate_simulation_summary(
            avg_score, continue_rate, drop_off_risk, common_dislikes
        )

        return ReaderSimulationResult(
            readers=readers,
            avg_score=round(avg_score, 1),
            continue_rate=round(continue_rate, 2),
            avg_cool_satisfaction=round(avg_cool, 2),
            common_likes=common_likes,
            common_dislikes=common_dislikes,
            drop_off_risk=round(drop_off_risk, 2),
            summary=summary,
        )

    # ── 情绪时间线构建 ──────────────────────────────────

    def _build_emotional_timeline(self, paragraphs: list[str]) -> list[dict[str, Any]]:
        """构建逐段情绪时间线

        Args:
            paragraphs: 段落列表

        Returns:
            情绪时间线列表，每项包含 paragraph_index, emotion_type, intensity, snippet
        """
        timeline: list[dict[str, Any]] = []
        for idx, para in enumerate(paragraphs):
            emotion_type, intensity = self._detect_paragraph_emotion(para)
            snippet = para[:50] + ("..." if len(para) > 50 else "")
            timeline.append(
                {
                    "paragraph_index": idx,
                    "emotion_type": emotion_type,
                    "intensity": round(intensity, 2),
                    "snippet": snippet,
                }
            )
        return timeline

    def _detect_paragraph_emotion(self, paragraph: str) -> tuple[str, float]:
        """检测单段情绪类型和强度

        Args:
            paragraph: 段落文本

        Returns:
            (情绪类型, 强度0-1)
        """
        emotion_scores: dict[str, int] = {}
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            count = sum(paragraph.count(k) for k in keywords)
            if count > 0:
                emotion_scores[emotion] = count

        if not emotion_scores:
            return "平静", 0.1

        # 取得分最高的情绪
        dominant = max(emotion_scores, key=lambda k: emotion_scores[k])
        max_count = emotion_scores[dominant]
        # 强度基于关键词数量，上限1.0
        intensity = min(1.0, 0.2 + max_count * 0.15)
        return dominant, intensity

    # ── 弃书点预测 ──────────────────────────────────────

    @staticmethod
    def _predict_drop_off(
        continue_reading: bool,
        cool_satisfaction: float,
        issue_penalty: float,
        severe_issues: list[Any],
        emotional_timeline: list[dict[str, Any]],
    ) -> tuple[str, str]:
        """预测弃书点和原因

        Returns:
            (弃书点, 弃书原因)
        """
        if continue_reading:
            return "", ""

        if cool_satisfaction < 0.3:
            return "前1/3处", "爽点不足，不够吸引人"
        if issue_penalty > 1.0:
            return "问题出现处", f"存在{len(severe_issues)}个严重问题，影响阅读体验"
        # 检查情绪时间线中是否有持续低情绪段
        low_emotion_count = sum(
            1 for e in emotional_timeline if e["intensity"] < 0.2
        )
        if low_emotion_count > len(emotional_timeline) * 0.5:
            return "中段", "情绪持续平淡，缺乏起伏"
        return "章末", "整体质量一般，没有继续阅读的动力"

    # ── 喜好/厌恶构建 ───────────────────────────────────

    def _build_likes_dislikes(
        self,
        cool_satisfaction: float,
        pacing_satisfaction: float,
        severe_issues: list[Any],
        emotional_timeline: list[dict[str, Any]],
    ) -> tuple[list[str], list[str]]:
        """构建喜好和厌恶列表"""
        likes: list[str] = []
        dislikes: list[str] = []

        if cool_satisfaction >= 0.7:
            likes.append("爽点充足，看得过瘾")
        if pacing_satisfaction >= 0.7:
            likes.append("节奏合适，读起来流畅")
        # 检查情绪时间线中是否有高潮
        high_emotions = [e for e in emotional_timeline if e["intensity"] >= 0.6]
        if high_emotions:
            likes.append(f"有{len(high_emotions)}处情绪高潮，代入感强")

        if cool_satisfaction < 0.4:
            dislikes.append("爽点不够，有点平淡")
        if pacing_satisfaction < 0.4:
            dislikes.append("节奏有问题，读起来累")
        if severe_issues:
            dislikes.append(f"有{len(severe_issues)}个明显问题")

        return likes, dislikes

    # ── 情感反应生成 ─────────────────────────────────────

    @staticmethod
    def _generate_emotional_response(cool_satisfaction: float, score: float) -> str:
        """生成整体情感反应"""
        if cool_satisfaction >= 0.8 and score >= 8:
            return "热血沸腾，欲罢不能"
        if cool_satisfaction >= 0.6 and score >= 7:
            return "看得挺爽，期待下一章"
        if score >= 6:
            return "平静阅读，没有特别强烈的感觉"
        return "有点无聊，注意力不集中"

    # ── 读者评论生成（LLM 增强 + 模板回退） ─────────────

    async def _generate_comments(
        self, score: float, likes: list[str], dislikes: list[str], text_snippet: str
    ) -> list[str]:
        """生成个性化读者评论

        优先使用 LLM 生成，失败时回退模板评论。

        Args:
            score: 综合评分
            likes: 喜好列表
            dislikes: 厌恶列表
            text_snippet: 文本片段（用于 LLM 上下文）

        Returns:
            评论列表
        """
        # 先尝试 LLM 增强
        try:
            llm_comments = await self._llm_generate_comments(score, likes, dislikes, text_snippet)
            if llm_comments:
                return llm_comments
        except Exception as e:
            logger.debug(f"[ReaderAgent] LLM评论生成失败，使用模板: {e}")

        # 回退模板评论
        return self._template_comments(score)

    async def _llm_generate_comments(
        self, score: float, likes: list[str], dislikes: list[str], text_snippet: str
    ) -> list[str]:
        """使用 LLM 生成个性化读者评论"""
        from kunlun.gacha.engine import gacha_engine

        reader_name = self.profile["name"]
        reader_desc = self.profile["description"]

        prompt = (
            f"你是一位{reader_name}（{reader_desc}），刚读完以下小说片段。\n\n"
            f"【你的评分】{score}/10\n"
            f"【你喜欢的点】{', '.join(likes) if likes else '无'}\n"
            f"【你不喜欢的点】{', '.join(dislikes) if dislikes else '无'}\n\n"
            f"【小说片段】\n{text_snippet}\n\n"
            "请以第一人称写2-3条真实的读者评论（每条不超过50字），"
            "语气要自然，符合你的读者身份。直接输出评论，每行一条，不要编号。"
        )

        result = await gacha_engine.generate(prompt, mode="single_fix", agent="reader")
        best_text = result.get("best_text", "")

        if not best_text:
            return []

        # 解析评论（按行分割，过滤空行）
        comments = [
            line.strip().lstrip("-•*").strip()
            for line in best_text.split("\n")
            if line.strip() and len(line.strip()) > 5
        ]
        return comments[:3] if comments else []

    def _template_comments(self, score: float) -> list[str]:
        """模板-based 评论（回退）"""
        if score >= 8:
            templates = [
                "这章不错，继续加油！",
                "看得很过瘾，催更！",
                "作者大大写得真好，已收藏！",
            ]
        elif score >= 6:
            templates = [
                "还可以，继续看看",
                "中规中矩，希望后面更精彩",
                "能看下去，期待后续发展",
            ]
        else:
            templates = [
                "有点无聊，再看一章试试",
                "节奏太慢了，爽点不够",
                "写得一般，可能要弃书了",
            ]
        # 根据 reader_type 选择不同的模板索引
        idx = hash(self.reader_type.value) % len(templates)
        return [templates[idx]]

    # ── 模拟结果摘要 ─────────────────────────────────────

    @staticmethod
    def _generate_simulation_summary(
        avg_score: float,
        continue_rate: float,
        drop_off_risk: float,
        dislikes: list[str],
    ) -> str:
        """生成读者模拟结果摘要"""
        level = (
            "优秀"
            if avg_score >= 8
            else "良好"
            if avg_score >= 7
            else "中等"
            if avg_score >= 6
            else "待提升"
        )
        risk_level = "低" if drop_off_risk < 0.2 else "中" if drop_off_risk < 0.4 else "高"
        return (
            f"读者模拟: 平均评分{avg_score:.1f}/10 ({level}) | "
            f"追读率{continue_rate * 100:.0f}% | "
            f"弃书风险{risk_level}({drop_off_risk * 100:.0f}%) | "
            f"主要问题: {', '.join(dislikes[:3]) if dislikes else '无明显共性问题'}"
        )

    # ── 空反馈 ──────────────────────────────────────────

    def _empty_feedback(self, chapter: int) -> EnhancedReaderFeedback:
        """空文本反馈"""
        return EnhancedReaderFeedback(
            reader_type=self.reader_type,
            reader_name=self.profile["name"],
            overall_score=0.0,
            continue_reading=False,
            drop_off_point="开头",
            drop_off_reason="文本为空",
            comments=["没有内容可读"],
            emotional_timeline=[],
            chapter=chapter,
        )

    # ── 消息总线方法 ─────────────────────────────────────

    async def publish_feedback(self, feedback: EnhancedReaderFeedback) -> None:
        """通过消息总线发布读者反馈

        发布主题: agent.reader.completed
        """
        await message_bus.publish("agent.reader.completed", feedback.to_dict())

    async def subscribe_to_requests(self) -> None:
        """订阅阅读请求主题

        订阅主题: agent.reader.request
        """

        async def _handler(message: object) -> None:
            if isinstance(message, dict):
                text = message.get("text", "")
                chapter = message.get("chapter", 0)
                feedback = await self.read(text, chapter)
                await self.publish_feedback(feedback)

        await message_bus.subscribe("agent.reader.request", _handler)
