"""
昆仑创作引擎 — 市场评论家 Agent (CriticAgent)

从市场和读者视角对章节文本进行深度批判，
结合规则初筛与 LLM 深度分析，输出可执行的改进建议。

批判维度：
  - 开篇吸引力
  - 爽点密度
  - 节奏把控
  - 章尾钩子
  - 毒点检测
  - 与同类爆款差距

工作流程：
  1. RuleBasedQualityChecker 规则初筛（零 LLM 成本）
  2. gacha_engine.generate() LLM 深度批判（mode="single_fix"）
  3. LLM 失败时回退规则结果
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from loguru import logger

from kunlun.agents.base import AgentMessage, BaseAgent
from kunlun.agents.message_bus import message_bus
from kunlun.debate_review.engine import (
    ReviewIssue,
    RuleBasedQualityChecker,
)

# ══════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════

# 批判维度列表
CRITIC_DIMENSIONS: list[str] = [
    "开篇吸引力",
    "爽点密度",
    "节奏把控",
    "章尾钩子",
    "毒点检测",
    "与同类爆款差距",
]


@dataclass
class CriticReport:
    """评论家报告

    Attributes:
        overall_score: 综合评分 0-100
        would_continue: 是否愿意继续阅读
        poison_points: 毒点列表（严重问题）
        suggestions: 改进建议列表
        market_potential: 市场潜力评价
        dimension_scores: 各维度得分
        chapter: 章节号
        issues: 规则检测到的问题列表
        critique_source: 批判来源 (rule / llm / fallback)
    """

    overall_score: float
    would_continue: bool
    poison_points: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    market_potential: str = ""
    dimension_scores: dict[str, float] = field(default_factory=dict)
    chapter: int = 0
    issues: list[dict[str, Any]] = field(default_factory=list)
    critique_source: str = "rule"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return asdict(self)


# ══════════════════════════════════════════════════════
# CriticAgent
# ══════════════════════════════════════════════════════


class CriticAgent(BaseAgent):
    """市场评论家 Agent

    先用 RuleBasedQualityChecker 做规则初筛，
    再用 gacha_engine.generate() 做 LLM 深度批判，
    LLM 失败时回退规则结果。
    """

    agent_name = "critic"
    agent_id = "critic"
    name = "市场评论家"

    def __init__(self) -> None:
        super().__init__()
        self.rule_checker = RuleBasedQualityChecker()

    # ── BaseAgent 抽象方法实现 ──────────────────────────

    async def on_message(self, msg: AgentMessage) -> AgentMessage | None:
        """处理接收到的消息"""
        if msg.msg_type == "CRITIQUE_REQUEST":
            text = msg.payload.get("text", "")
            chapter = msg.payload.get("chapter", 0)
            context = msg.payload.get("context", "")
            report = await self.critique(text, chapter, context)
            await self.publish_critique(report)
            return AgentMessage(
                from_agent=self.agent_name,
                to_agent=msg.from_agent,
                msg_type="CRITIQUE_RESULT",
                payload=report.to_dict(),
                correlation_id=msg.correlation_id,
            )
        return None

    async def execute(self, task: dict) -> dict:
        """执行批判任务"""
        text = task.get("text", "")
        chapter = task.get("chapter", 0)
        context = task.get("context", "")
        report = await self.critique(text, chapter, context)
        return report.to_dict()

    # ── 核心批判方法 ────────────────────────────────────

    async def critique(self, text: str, chapter: int = 0, context: str = "") -> CriticReport:
        """对文本进行批判：规则初筛 → LLM 深度批判 → 回退规则

        Args:
            text: 章节文本
            chapter: 章节号
            context: 上下文信息

        Returns:
            CriticReport 批判报告
        """
        if not text or not text.strip():
            return self._empty_report(chapter)

        # 1. 规则初筛
        rule_issues = self.rule_checker.check(text, chapter)
        dimension_scores = self.rule_checker.calculate_dimension_scores(text)
        rule_report = self._build_rule_report(rule_issues, dimension_scores, chapter)

        # 2. LLM 深度批判（失败回退规则）
        try:
            llm_report = await self._llm_critique(
                text, chapter, context, rule_issues, dimension_scores
            )
            if llm_report is not None:
                return llm_report
        except Exception as e:
            logger.warning(f"[CriticAgent] LLM批判失败，回退规则结果: {e}")

        return rule_report

    # ── 规则-based 报告构建 ─────────────────────────────

    def _empty_report(self, chapter: int) -> CriticReport:
        """空文本报告"""
        return CriticReport(
            overall_score=0.0,
            would_continue=False,
            poison_points=["文本为空"],
            suggestions=["请提供有效文本"],
            market_potential="无法评估",
            dimension_scores=dict.fromkeys(CRITIC_DIMENSIONS, 0.0),
            chapter=chapter,
            critique_source="rule",
        )

    def _build_rule_report(
        self,
        issues: list[ReviewIssue],
        dimension_scores: dict[str, float],
        chapter: int,
    ) -> CriticReport:
        """基于规则检测结果构建报告

        Args:
            issues: 规则检测到的问题列表
            dimension_scores: 各维度得分
            chapter: 章节号

        Returns:
            CriticReport 规则-based 批判报告
        """
        # 计算总分（各维度平均）
        if dimension_scores:
            total_score = sum(dimension_scores.values()) / len(dimension_scores)
        else:
            total_score = 0.0
        total_score = max(0.0, min(100.0, total_score))

        # 毒点（严重度 >= 4 的问题）
        poison_points = [
            f"[{issue.dimension.value}] {issue.description}"
            for issue in issues
            if issue.severity >= 4
        ]

        # 建议（按严重度排序取前5）
        suggestions = [
            issue.suggestion
            for issue in sorted(issues, key=lambda i: i.severity, reverse=True)[:5]
            if issue.suggestion
        ]

        # 市场潜力评价
        if total_score >= 85:
            market_potential = "高，具备爆款潜质"
        elif total_score >= 70:
            market_potential = "中，有提升空间"
        else:
            market_potential = "低，需要大幅改进"

        # 维度得分映射到批判维度
        critic_dim_scores = self._map_dimension_scores(dimension_scores)

        return CriticReport(
            overall_score=round(total_score, 1),
            would_continue=total_score >= 60,
            poison_points=poison_points,
            suggestions=suggestions,
            market_potential=market_potential,
            dimension_scores=critic_dim_scores,
            chapter=chapter,
            issues=[i.to_dict() for i in issues],
            critique_source="rule",
        )

    @staticmethod
    def _map_dimension_scores(raw_scores: dict[str, float]) -> dict[str, float]:
        """将 ReviewDimension 得分映射到批判维度

        Args:
            raw_scores: 原始维度得分（key 为 ReviewDimension.value）

        Returns:
            批判维度得分字典
        """
        mapping: dict[str, float] = {
            "开篇吸引力": raw_scores.get("plot_logic", 85.0),
            "爽点密度": raw_scores.get("cool_point", 85.0),
            "节奏把控": raw_scores.get("pacing", 85.0),
            "章尾钩子": raw_scores.get("plot_logic", 85.0),
            "毒点检测": min(
                raw_scores.get("consistency", 85.0),
                raw_scores.get("writing", 85.0),
            ),
            "与同类爆款差距": (sum(raw_scores.values()) / len(raw_scores) if raw_scores else 85.0),
        }
        return {k: round(v, 1) for k, v in mapping.items()}

    # ── LLM 深度批判 ────────────────────────────────────

    async def _llm_critique(
        self,
        text: str,
        chapter: int,
        context: str,
        rule_issues: list[ReviewIssue],
        dimension_scores: dict[str, float],
    ) -> CriticReport | None:
        """使用 LLM 进行深度批判

        Args:
            text: 章节文本
            chapter: 章节号
            context: 上下文
            rule_issues: 规则初筛问题
            dimension_scores: 规则维度得分

        Returns:
            CriticReport 或 None（LLM 输出无法解析时）
        """
        from kunlun.gacha.engine import gacha_engine

        # 构建规则问题摘要
        issues_summary = (
            "\n".join(
                f"- [{i.dimension.value}][严重度{i.severity}] {i.description}"
                for i in rule_issues[:10]
            )
            or "无规则检测问题"
        )

        prompt = (
            "你是一位资深网文市场评论家，请对以下小说章节进行深度市场批判。\n\n"
            f"【章节信息】第{chapter}章\n"
            f"【上下文】{context or '无'}\n"
            "【规则初筛发现的问题】\n"
            f"{issues_summary}\n\n"
            "【章节文本】\n"
            f"{text[:3000]}\n\n"
            "请从以下6个维度进行批判：\n"
            "1. 开篇吸引力\n"
            "2. 爽点密度\n"
            "3. 节奏把控\n"
            "4. 章尾钩子\n"
            "5. 毒点检测\n"
            "6. 与同类爆款差距\n\n"
            "请严格以JSON格式输出，不要输出其他内容：\n"
            "{\n"
            '  "overall_score": 0-100的整数,\n'
            '  "would_continue": true/false,\n'
            '  "poison_points": ["毒点1", "毒点2"],\n'
            '  "suggestions": ["建议1", "建议2"],\n'
            '  "market_potential": "市场潜力评价",\n'
            '  "dimension_scores": {\n'
            '    "开篇吸引力": 0-100,\n'
            '    "爽点密度": 0-100,\n'
            '    "节奏把控": 0-100,\n'
            '    "章尾钩子": 0-100,\n'
            '    "毒点检测": 0-100,\n'
            '    "与同类爆款差距": 0-100\n'
            "  }\n"
            "}"
        )

        result = await gacha_engine.generate(prompt, mode="single_fix", agent="critic")
        best_text = result.get("best_text", "")

        if not best_text:
            return None

        parsed = self._parse_critic_json(best_text)
        if parsed is None:
            return None

        # 构建 LLM 批判报告
        dim_scores_raw = parsed.get("dimension_scores", {})
        dim_scores: dict[str, float] = {}
        for dim in CRITIC_DIMENSIONS:
            val = dim_scores_raw.get(dim, dimension_scores.get(dim, 85.0))
            try:
                dim_scores[dim] = round(float(val), 1)
            except (TypeError, ValueError):
                dim_scores[dim] = 85.0

        return CriticReport(
            overall_score=float(parsed.get("overall_score", 0)),
            would_continue=bool(parsed.get("would_continue", False)),
            poison_points=list(parsed.get("poison_points", [])),
            suggestions=list(parsed.get("suggestions", [])),
            market_potential=str(parsed.get("market_potential", "")),
            dimension_scores=dim_scores,
            chapter=chapter,
            issues=[i.to_dict() for i in rule_issues],
            critique_source="llm",
        )

    @staticmethod
    def _parse_critic_json(text: str) -> dict[str, Any] | None:
        """从 LLM 输出中解析 JSON

        Args:
            text: LLM 输出文本

        Returns:
            解析后的字典，失败返回 None
        """
        json_match = re.search(r"\{[\s\S]*\}", text)
        if not json_match:
            return None
        try:
            data = json.loads(json_match.group())
            if isinstance(data, dict):
                return data
            return None
        except (json.JSONDecodeError, ValueError):
            return None

    # ── 消息总线方法 ─────────────────────────────────────

    async def publish_critique(self, report: CriticReport) -> None:
        """通过消息总线发布批判结果

        发布主题: agent.critic.completed
        """
        await message_bus.publish("agent.critic.completed", report.to_dict())

    async def subscribe_to_requests(self) -> None:
        """订阅批判请求主题

        订阅主题: agent.critic.request
        收到请求后自动执行批判并发布结果
        """

        async def _handler(message: object) -> None:
            if isinstance(message, dict):
                text = message.get("text", "")
                chapter = message.get("chapter", 0)
                context = message.get("context", "")
                report = await self.critique(text, chapter, context)
                await self.publish_critique(report)

        await message_bus.subscribe("agent.critic.request", _handler)
