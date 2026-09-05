"""
昆仑创作引擎 — 辩论编排器 (DebateOrchestrator)

编排 CriticAgent、ReaderAgent 和 Defender（Writer视角）进行多轮辩论，
实现 LLM 辩论、CRITIC 验证、Reflexion 修订三大核心能力。

辩论流程：
  1. 开场：CriticAgent 提出问题列表
  2. 各方陈述：Critic 批判 → Reader 反馈 → Defender 辩护
  3. 质询：每轮 Critic 追问，Defender 回应，Reader 投票
  4. 总结裁决：综合各方观点，判定问题是否成立
  5. 最多3轮，每轮聚焦最严重的2-3个问题

CRITIC 验证：对每个达成共识的问题，验证修改建议是否可执行
  - 检查建议是否具体
  - 是否有明确位置
  - 是否可量化

Reflexion 修订：对未解决问题，生成结构化反思
  - 问题根因 → 修改方向 → 预期效果

8阶段增强流水线：
  Stage0 预处理 → Stage1 蓝图评审辩论 → Stage2 抽卡建议
  → Stage3 CRITIC验证 → Stage4 Reflexion修订 → Stage5 终评
  → Stage6 润色建议 → Stage7 知识更新建议
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any

from loguru import logger

from kunlun.agents.critic import CriticAgent, CriticReport
from kunlun.agents.reader import (
    EnhancedReaderFeedback,
    ExtendedReaderType,
    ReaderAgent,
)
from kunlun.debate_review.engine import (
    DebateReviewEngine,
    ReviewIssue,
    RuleBasedQualityChecker,
)

# ══════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════


@dataclass
class DebateRoundDetail:
    """辩论轮次详情"""

    round_num: int
    focus_issues: list[str] = field(default_factory=list)
    critic_argument: str = ""
    defender_argument: str = ""
    reader_vote: str = ""
    resolution: str = ""
    issues_resolved: list[str] = field(default_factory=list)
    issues_unresolved: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DebateResult:
    """辩论结果

    Attributes:
        rounds: 辩论轮次列表
        final_verdict: 最终裁决
        agreed_issues: 达成共识的问题数
        unresolved_issues: 未解决问题数
        revision_suggestions: 修订建议列表
        total_score: 综合评分 0-100
        critic_report: 评论家报告（可选）
        reader_feedback: 读者反馈（可选）
        debate_source: 辩论来源 (llm / rule)
    """

    rounds: list[DebateRoundDetail] = field(default_factory=list)
    final_verdict: str = ""
    agreed_issues: int = 0
    unresolved_issues: int = 0
    revision_suggestions: list[dict[str, Any]] = field(default_factory=list)
    total_score: float = 0.0
    critic_report: dict[str, Any] = field(default_factory=dict)
    reader_feedback: dict[str, Any] = field(default_factory=dict)
    debate_source: str = "rule"
    reflexion_entries: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rounds": [r.to_dict() for r in self.rounds],
            "final_verdict": self.final_verdict,
            "agreed_issues": self.agreed_issues,
            "unresolved_issues": self.unresolved_issues,
            "revision_suggestions": self.revision_suggestions,
            "total_score": self.total_score,
            "critic_report": self.critic_report,
            "reader_feedback": self.reader_feedback,
            "debate_source": self.debate_source,
            "reflexion_entries": self.reflexion_entries,
        }


@dataclass
class CRITICVerification:
    """CRITIC 验证结果"""

    issue_description: str
    suggestion: str
    is_specific: bool  # 建议是否具体
    has_location: bool  # 是否有明确位置
    is_quantifiable: bool  # 是否可量化
    actionable: bool  # 综合判定是否可执行
    verification_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReflexionEntry:
    """Reflexion 反思条目"""

    issue_description: str
    root_cause: str  # 问题根因
    revision_direction: str  # 修改方向
    expected_effect: str  # 预期效果
    priority: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineStage:
    """流水线阶段"""

    stage_name: str
    status: str  # success / skipped / failed
    result: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineResult:
    """8阶段流水线结果"""

    stages: list[PipelineStage] = field(default_factory=list)
    final_score: float = 0.0
    passed: bool = False
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "stages": [s.to_dict() for s in self.stages],
            "final_score": self.final_score,
            "passed": self.passed,
            "summary": self.summary,
        }


# ══════════════════════════════════════════════════════
# DebateOrchestrator
# ══════════════════════════════════════════════════════


class DebateOrchestrator:
    """辩论编排器

    编排 CriticAgent、ReaderAgent 和 Defender 进行多轮辩论，
    实现 LLM 辩论、CRITIC 验证、Reflexion 修订。
    """

    def __init__(self, max_rounds: int = 3) -> None:
        self.max_rounds = max_rounds
        self.critic_agent = CriticAgent()
        self.reader_agent = ReaderAgent(ExtendedReaderType.VETERAN)
        self.rule_checker = RuleBasedQualityChecker()
        self.rule_debate_engine = DebateReviewEngine(max_rounds=max_rounds)

    # ── 核心辩论编排 ────────────────────────────────────

    async def orchestrate_debate(
        self, text: str, chapter: int = 0, context: str = ""
    ) -> DebateResult:
        """编排多轮辩论

        流程：
          1. 开场：CriticAgent 提出问题列表
          2. 各方陈述：Critic 批判 → Reader 反馈 → Defender 辩护
          3. 质询：每轮 Critic 追问，Defender 回应，Reader 投票
          4. 总结裁决

        Args:
            text: 章节文本
            chapter: 章节号
            context: 上下文

        Returns:
            DebateResult 辩论结果
        """
        if not text or not text.strip():
            return DebateResult(
                final_verdict="文本为空，无法进行辩论",
                total_score=0.0,
                debate_source="rule",
            )

        # 1. 开场：CriticAgent 提出问题列表
        critic_report = await self.critic_agent.critique(text, chapter, context)
        reader_feedback = await self.reader_agent.read(text, chapter)

        # 获取问题列表（从规则检测结果）
        rule_issues = self.rule_checker.check(text, chapter)
        # 按严重度排序，取最严重的问题
        sorted_issues = sorted(rule_issues, key=lambda i: i.severity, reverse=True)

        # 2. 尝试 LLM 辩论
        try:
            debate_result = await self._llm_debate(
                text, chapter, context, sorted_issues, critic_report, reader_feedback
            )
            if debate_result is not None:
                # CRITIC 验证 + Reflexion 修订
                debate_result = await self._apply_critic_and_reflexion(debate_result, sorted_issues)
                return debate_result
        except Exception as e:
            logger.warning(f"[DebateOrchestrator] LLM辩论失败，回退规则辩论: {e}")

        # 3. 回退规则-based 辩论
        debate_result = self._rule_debate(
            text, chapter, context, sorted_issues, critic_report, reader_feedback
        )
        # CRITIC 验证 + Reflexion 修订
        debate_result = await self._apply_critic_and_reflexion(debate_result, sorted_issues)
        return debate_result

    # ── LLM 辩论 ────────────────────────────────────────

    async def _llm_debate(
        self,
        text: str,
        chapter: int,
        context: str,
        issues: list[ReviewIssue],
        critic_report: CriticReport,
        reader_feedback: EnhancedReaderFeedback,
    ) -> DebateResult | None:
        """使用 LLM 进行多轮辩论

        Args:
            text: 章节文本
            chapter: 章节号
            context: 上下文
            issues: 问题列表
            critic_report: 评论家报告
            reader_feedback: 读者反馈

        Returns:
            DebateResult 或 None（LLM 输出无效时）
        """
        from kunlun.gacha.engine import gacha_engine

        if not issues:
            # 无问题时直接返回好评
            return DebateResult(
                rounds=[],
                final_verdict="未发现明显问题，文本质量良好",
                agreed_issues=0,
                unresolved_issues=0,
                revision_suggestions=[],
                total_score=critic_report.overall_score,
                critic_report=critic_report.to_dict(),
                reader_feedback=reader_feedback.to_dict(),
                debate_source="llm",
            )

        rounds: list[DebateRoundDetail] = []
        all_agreed: list[str] = []
        all_unresolved: list[str] = []
        revision_suggestions: list[dict[str, Any]] = []

        # 每轮聚焦最严重的2-3个问题
        issues_per_round = min(3, max(2, len(issues) // self.max_rounds + 1))

        for round_num in range(1, self.max_rounds + 1):
            start_idx = (round_num - 1) * issues_per_round
            round_issues = issues[start_idx : start_idx + issues_per_round]
            if not round_issues:
                break

            focus_descriptions = [i.description for i in round_issues]

            # 构建辩论 prompt
            prompt = self._build_debate_prompt(
                text,
                chapter,
                context,
                round_num,
                round_issues,
                critic_report,
                reader_feedback,
            )

            result = await gacha_engine.generate(prompt, mode="single_fix", agent="debate")
            best_text = result.get("best_text", "")

            if not best_text:
                return None

            # 解析辩论结果
            parsed = self._parse_debate_response(best_text)
            if parsed is None:
                return None

            round_detail = DebateRoundDetail(
                round_num=round_num,
                focus_issues=focus_descriptions,
                critic_argument=parsed.get("critic_argument", ""),
                defender_argument=parsed.get("defender_argument", ""),
                reader_vote=parsed.get("reader_vote", ""),
                resolution=parsed.get("resolution", ""),
                issues_resolved=parsed.get("issues_resolved", []),
                issues_unresolved=parsed.get("issues_unresolved", []),
            )
            rounds.append(round_detail)
            all_agreed.extend(parsed.get("issues_resolved", []))
            all_unresolved.extend(parsed.get("issues_unresolved", []))

            # 收集修订建议
            for suggestion in parsed.get("revision_suggestions", []):
                revision_suggestions.append(
                    {
                        "round": round_num,
                        "issue": suggestion.get("issue", ""),
                        "suggestion": suggestion.get("suggestion", ""),
                        "priority": suggestion.get("priority", 3),
                    }
                )

        # 最终裁决
        final_verdict = self._generate_final_verdict(all_agreed, all_unresolved, critic_report)
        total_score = self._calculate_debate_score(
            critic_report, reader_feedback, len(all_agreed), len(all_unresolved)
        )

        return DebateResult(
            rounds=rounds,
            final_verdict=final_verdict,
            agreed_issues=len(all_agreed),
            unresolved_issues=len(all_unresolved),
            revision_suggestions=revision_suggestions,
            total_score=total_score,
            critic_report=critic_report.to_dict(),
            reader_feedback=reader_feedback.to_dict(),
            debate_source="llm",
        )

    def _build_debate_prompt(
        self,
        text: str,
        chapter: int,
        context: str,
        round_num: int,
        issues: list[ReviewIssue],
        critic_report: CriticReport,
        reader_feedback: EnhancedReaderFeedback,
    ) -> str:
        """构建 LLM 辩论 prompt"""
        issues_text = "\n".join(
            f"  问题{i + 1}: [{issue.dimension.value}][严重度{issue.severity}] "
            f"{issue.description}（位置: {issue.location}）"
            f"{' 建议: ' + issue.suggestion if issue.suggestion else ''}"
            for i, issue in enumerate(issues)
        )

        return (
            f"你是一场小说质量辩论的主持人。请主持第{round_num}轮辩论。\n\n"
            f"【章节信息】第{chapter}章\n"
            f"【上下文】{context or '无'}\n\n"
            f"【本轮聚焦问题】\n{issues_text}\n\n"
            f"【评论家观点】综合评分{critic_report.overall_score}/100，"
            f"主要毒点: {', '.join(critic_report.poison_points[:3]) if critic_report.poison_points else '无'}\n\n"
            f"【读者反馈】{reader_feedback.reader_name}评分{reader_feedback.overall_score}/10，"
            f"继续阅读={reader_feedback.continue_reading}，"
            f"情感反应: {reader_feedback.emotional_response}\n\n"
            f"【章节文本片段】\n{text[:2000]}\n\n"
            "请模拟三方辩论并输出结果：\n"
            "1. Critic（评论家）：深入批判本轮问题\n"
            "2. Defender（作者辩护）：从创作意图角度回应\n"
            "3. Reader（读者投票）：站在读者角度投票\n"
            "4. 裁决：判定每个问题是否成立\n\n"
            "请严格以JSON格式输出：\n"
            "{\n"
            '  "critic_argument": "评论家论点",\n'
            '  "defender_argument": "辩护方回应",\n'
            '  "reader_vote": "读者投票结果",\n'
            '  "resolution": "本轮裁决总结",\n'
            '  "issues_resolved": ["成立的问题描述1", "成立的问题描述2"],\n'
            '  "issues_unresolved": ["不成立或存疑的问题描述"],\n'
            '  "revision_suggestions": [\n'
            '    {"issue": "问题", "suggestion": "具体修改建议", "priority": 1-5}\n'
            "  ]\n"
            "}"
        )

    @staticmethod
    def _parse_debate_response(text: str) -> dict[str, Any] | None:
        """解析 LLM 辩论响应"""
        import json
        import re

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

    # ── 规则-based 辩论（回退） ─────────────────────────

    def _rule_debate(
        self,
        text: str,
        chapter: int,
        context: str,
        issues: list[ReviewIssue],
        critic_report: CriticReport,
        reader_feedback: EnhancedReaderFeedback,
    ) -> DebateResult:
        """规则-based 辩论（复用 DebateReviewEngine 逻辑）

        Args:
            text: 章节文本
            chapter: 章节号
            context: 上下文
            issues: 问题列表
            critic_report: 评论家报告
            reader_feedback: 读者反馈

        Returns:
            DebateResult 规则辩论结果
        """
        # 复用现有 DebateReviewEngine 的辩论逻辑
        rule_result = self.rule_debate_engine.review(text, chapter, context)

        rounds: list[DebateRoundDetail] = []
        all_agreed: list[str] = []
        all_unresolved: list[str] = []
        revision_suggestions: list[dict[str, Any]] = []

        # 将规则辩论轮次转换为详细轮次
        for i, dr in enumerate(rule_result.debate_rounds):
            round_num = i + 1
            # 找到对应的问题
            related_issues = issues[i : i + 1] if i < len(issues) else []
            focus = [iss.description for iss in related_issues]

            is_resolved = dr.issue_resolved
            resolved_list = focus if is_resolved else []
            unresolved_list = [] if is_resolved else focus

            round_detail = DebateRoundDetail(
                round_num=round_num,
                focus_issues=focus,
                critic_argument=dr.critic_argument,
                defender_argument=dr.defender_argument,
                reader_vote=("读者认同问题存在" if is_resolved else "读者认为问题影响较小"),
                resolution=dr.resolution,
                issues_resolved=resolved_list,
                issues_unresolved=unresolved_list,
            )
            rounds.append(round_detail)
            all_agreed.extend(resolved_list)
            all_unresolved.extend(unresolved_list)

        # 收集修订建议
        for priority in rule_result.revision_priority[:5]:
            revision_suggestions.append(
                {
                    "round": 1,
                    "issue": priority.get("description", ""),
                    "suggestion": priority.get("suggestion", ""),
                    "priority": priority.get("priority", 3),
                }
            )

        final_verdict = self._generate_final_verdict(all_agreed, all_unresolved, critic_report)
        total_score = self._calculate_debate_score(
            critic_report, reader_feedback, len(all_agreed), len(all_unresolved)
        )

        return DebateResult(
            rounds=rounds,
            final_verdict=final_verdict,
            agreed_issues=len(all_agreed),
            unresolved_issues=len(all_unresolved),
            revision_suggestions=revision_suggestions,
            total_score=total_score,
            critic_report=critic_report.to_dict(),
            reader_feedback=reader_feedback.to_dict(),
            debate_source="rule",
        )

    # ── CRITIC 验证 + Reflexion 修订 ───────────────────

    async def _apply_critic_and_reflexion(
        self, debate_result: DebateResult, issues: list[ReviewIssue]
    ) -> DebateResult:
        """对辩论结果应用 CRITIC 验证和 Reflexion 修订

        Args:
            debate_result: 原始辩论结果
            issues: 问题列表

        Returns:
            增强后的辩论结果
        """
        # CRITIC 验证：对达成共识的问题验证建议可执行性
        verified_suggestions: list[dict[str, Any]] = []
        for suggestion in debate_result.revision_suggestions:
            verification = self._critic_verify_suggestion(
                suggestion.get("issue", ""),
                suggestion.get("suggestion", ""),
            )
            suggestion["critic_verification"] = verification.to_dict()
            verified_suggestions.append(suggestion)
        debate_result.revision_suggestions = verified_suggestions

        # Reflexion 修订：对未解决问题生成结构化反思
        reflexion_entries: list[ReflexionEntry] = []
        unresolved_descriptions = set()
        for r in debate_result.rounds:
            unresolved_descriptions.update(r.issues_unresolved)

        for desc in list(unresolved_descriptions)[:5]:
            entry = self._generate_reflexion(desc, issues)
            reflexion_entries.append(entry)

        debate_result.reflexion_entries = [e.to_dict() for e in reflexion_entries]

        return debate_result

    def _critic_verify_suggestion(self, issue: str, suggestion: str) -> CRITICVerification:
        """CRITIC 验证：检查修改建议是否可执行

        验证维度：
          - is_specific: 建议是否具体（长度 > 10，包含动作词）
          - has_location: 是否有明确位置（包含位置相关词）
          - is_quantifiable: 是否可量化（包含数字或程度词）

        Args:
            issue: 问题描述
            suggestion: 修改建议

        Returns:
            CRITICVerification 验证结果
        """
        # 检查是否具体
        action_words = [
            "增加",
            "删除",
            "修改",
            "替换",
            "调整",
            "优化",
            "拆分",
            "合并",
            "强化",
            "弱化",
        ]
        is_specific = len(suggestion) > 10 and any(w in suggestion for w in action_words)

        # 检查是否有明确位置
        location_words = [
            "开头",
            "结尾",
            "中段",
            "前1/3",
            "后1/3",
            "章末",
            "开篇",
            "对话",
            "段落",
            "场景",
        ]
        has_location = any(w in suggestion for w in location_words)

        # 检查是否可量化
        quantifiable_words = [
            "个",
            "处",
            "字",
            "次",
            "比例",
            "密度",
            "3-5",
            "2-3",
            "至少",
            "不超过",
        ]
        import re

        has_number = bool(re.search(r"\d", suggestion))
        is_quantifiable = has_number or any(w in suggestion for w in quantifiable_words)

        # 综合判定
        actionable = is_specific and (has_location or is_quantifiable)

        notes_parts = []
        if not is_specific:
            notes_parts.append("建议不够具体")
        if not has_location:
            notes_parts.append("缺少明确位置")
        if not is_quantifiable:
            notes_parts.append("难以量化评估")
        verification_notes = "；".join(notes_parts) if notes_parts else "建议可执行"

        return CRITICVerification(
            issue_description=issue,
            suggestion=suggestion,
            is_specific=is_specific,
            has_location=has_location,
            is_quantifiable=is_quantifiable,
            actionable=actionable,
            verification_notes=verification_notes,
        )

    def _generate_reflexion(
        self, issue_description: str, issues: list[ReviewIssue]
    ) -> ReflexionEntry:
        """生成 Reflexion 结构化反思

        对未解决问题，生成：问题根因 → 修改方向 → 预期效果

        Args:
            issue_description: 问题描述
            issues: 所有问题列表（用于上下文）

        Returns:
            ReflexionEntry 反思条目
        """
        # 基于问题描述推断根因
        root_cause = self._infer_root_cause(issue_description)
        revision_direction = self._infer_revision_direction(issue_description, root_cause)
        expected_effect = self._infer_expected_effect(issue_description, revision_direction)

        # 优先级基于问题在列表中的严重度
        priority = 3
        for issue in issues:
            if issue.description in issue_description or issue_description in issue.description:
                priority = issue.severity
                break

        return ReflexionEntry(
            issue_description=issue_description,
            root_cause=root_cause,
            revision_direction=revision_direction,
            expected_effect=expected_effect,
            priority=priority,
        )

    @staticmethod
    def _infer_root_cause(issue_description: str) -> str:
        """推断问题根因"""
        if "爽点" in issue_description or "平淡" in issue_description:
            return "爽点排布不合理，前期铺垫过长，缺乏即时反馈"
        if "节奏" in issue_description or "拖沓" in issue_description:
            return "叙事节奏失控，长句和描写过多，缺少对话和动作推进"
        if "逻辑" in issue_description or "矛盾" in issue_description:
            return "前后设定不一致，情节推进缺乏合理铺垫"
        if "人物" in issue_description or "人设" in issue_description:
            return "人物行为动机不清晰，性格刻画扁平"
        if "章末" in issue_description or "钩子" in issue_description:
            return "章节收尾过于平淡，未设置悬念或冲突延续"
        if "情感" in issue_description or "代入" in issue_description:
            return "情感描写不足，读者难以与角色产生共鸣"
        return "问题根因需进一步分析，建议结合上下文深入排查"

    @staticmethod
    def _infer_revision_direction(issue_description: str, root_cause: str) -> str:
        """推断修改方向"""
        if "爽点" in issue_description or "平淡" in issue_description:
            return "在前1/3处增加一个小高潮，将爽点密度提升到3-5/千字，确保每500字有一个小反馈"
        if "节奏" in issue_description or "拖沓" in issue_description:
            return "拆分超过50字的长句，增加角色对话比例到15%以上，删除冗余的环境描写"
        if "逻辑" in issue_description or "矛盾" in issue_description:
            return "梳理时间线和设定表，在矛盾处增加过渡解释或调整前文设定"
        if "人物" in issue_description or "人设" in issue_description:
            return "为关键角色增加内心独白和行为动机描写，通过细节展现性格而非直接陈述"
        if "章末" in issue_description or "钩子" in issue_description:
            return "在章末设置悬念（新角色登场/危机降临/真相暗示），用疑问句或转折句收尾"
        if "情感" in issue_description or "代入" in issue_description:
            return "增加角色的感官描写和情感反应，通过具体场景触发读者共情"
        return f"针对根因（{root_cause}）进行系统性修改，建议先定位具体段落再逐一优化"

    @staticmethod
    def _infer_expected_effect(issue_description: str, revision_direction: str) -> str:
        """推断预期效果"""
        if "爽点" in issue_description:
            return "预计提升爽点满足度20-30%，追读率提升15%"
        if "节奏" in issue_description:
            return "预计提升阅读流畅度，平均阅读时间减少15%，弃书率降低10%"
        if "逻辑" in issue_description:
            return "预计消除逻辑硬伤，老白读者满意度提升25%"
        if "人物" in issue_description:
            return "预计增强角色记忆点，读者角色认同感提升20%"
        if "章末" in issue_description:
            return "预计提升章末转化率，下一章打开率提升10-15%"
        if "情感" in issue_description:
            return "预计增强情感代入，读者评论中情感相关提及率提升30%"
        return "预计整体质量评分提升5-10分，读者满意度显著改善"

    # ── 辅助方法 ────────────────────────────────────────

    @staticmethod
    def _generate_final_verdict(
        agreed: list[str], unresolved: list[str], critic_report: CriticReport
    ) -> str:
        """生成最终裁决"""
        total = len(agreed) + len(unresolved)
        if total == 0:
            return "未发现需要辩论的问题，文本质量良好"
        agreed_rate = len(agreed) / total
        if agreed_rate >= 0.7:
            level = "问题基本成立"
        elif agreed_rate >= 0.4:
            level = "部分问题成立"
        else:
            level = "大部分问题不成立"
        return (
            f"辩论结束：共讨论{total}个问题，达成共识{len(agreed)}个，"
            f"未解决{len(unresolved)}个。{level}。"
            f"评论家综合评分{critic_report.overall_score}/100。"
        )

    @staticmethod
    def _calculate_debate_score(
        critic_report: CriticReport,
        reader_feedback: EnhancedReaderFeedback,
        agreed_count: int,
        unresolved_count: int,
    ) -> float:
        """计算辩论综合评分"""
        # 评论家评分 60% + 读者评分 40%
        critic_score = critic_report.overall_score
        reader_score = reader_feedback.overall_score * 10  # 转换为0-100
        base = critic_score * 0.6 + reader_score * 0.4

        # 未解决问题扣分
        penalty = unresolved_count * 2.0
        final = max(0.0, min(100.0, base - penalty))
        return round(final, 1)

    # ── 8阶段增强流水线 ─────────────────────────────────

    async def run_8stage_pipeline(
        self, text: str, chapter: int, outline: str = ""
    ) -> PipelineResult:
        """运行8阶段增强流水线

        Stage0 预处理 → Stage1 蓝图评审辩论 → Stage2 抽卡建议
        → Stage3 CRITIC验证 → Stage4 Reflexion修订 → Stage5 终评
        → Stage6 润色建议 → Stage7 知识更新建议

        注意：Stage2/6/7 输出建议而非实际执行（避免重复调用LLM），
        核心是 Stage1/3/4/5 的辩论逻辑。

        Args:
            text: 章节文本
            chapter: 章节号
            outline: 大纲信息

        Returns:
            PipelineResult 流水线结果
        """
        stages: list[PipelineStage] = []

        # Stage0: 预处理
        stage0 = self._stage0_preprocess(text, chapter)
        stages.append(stage0)

        # Stage1: 蓝图评审辩论（核心）
        stage1 = await self._stage1_debate(text, chapter, outline)
        stages.append(stage1)

        # Stage2: 抽卡建议（输出建议，不实际执行）
        stage2 = self._stage2_gacha_suggestion(text, chapter, stage1)
        stages.append(stage2)

        # Stage3: CRITIC验证（核心）
        stage3 = self._stage3_critic_verification(stage1)
        stages.append(stage3)

        # Stage4: Reflexion修订（核心）
        stage4 = self._stage4_reflexion(stage1)
        stages.append(stage4)

        # Stage5: 终评（核心）
        stage5 = self._stage5_final_review(text, chapter, stage1, stage3, stage4)
        stages.append(stage5)

        # Stage6: 润色建议（输出建议）
        stage6 = self._stage6_polish_suggestion(text, stage5)
        stages.append(stage6)

        # Stage7: 知识更新建议（输出建议）
        stage7 = self._stage7_knowledge_update(text, chapter, stage1)
        stages.append(stage7)

        # 汇总
        final_score = stage5.result.get("final_score", 0.0)
        passed = final_score >= 60.0
        summary = self._generate_pipeline_summary(stages, final_score, passed)

        return PipelineResult(
            stages=stages,
            final_score=final_score,
            passed=passed,
            summary=summary,
        )

    def _stage0_preprocess(self, text: str, chapter: int) -> PipelineStage:
        """Stage0: 预处理"""
        start = time.monotonic()
        total_chars = len(text.replace(" ", "").replace("\n", ""))
        paragraphs = [p for p in text.split("\n") if p.strip()]
        result = {
            "chapter": chapter,
            "total_chars": total_chars,
            "paragraph_count": len(paragraphs),
            "text_empty": not text.strip(),
        }
        duration = (time.monotonic() - start) * 1000
        return PipelineStage(
            stage_name="Stage0_预处理",
            status="success",
            result=result,
            duration_ms=round(duration, 2),
        )

    async def _stage1_debate(self, text: str, chapter: int, outline: str) -> PipelineStage:
        """Stage1: 蓝图评审辩论（核心）"""
        start = time.monotonic()
        try:
            debate_result = await self.orchestrate_debate(text, chapter, outline)
            status = "success"
            result = debate_result.to_dict()
        except Exception as e:
            status = "failed"
            result = {"error": str(e)}
        duration = (time.monotonic() - start) * 1000
        return PipelineStage(
            stage_name="Stage1_蓝图评审辩论",
            status=status,
            result=result,
            duration_ms=round(duration, 2),
        )

    def _stage2_gacha_suggestion(
        self, text: str, chapter: int, stage1: PipelineStage
    ) -> PipelineStage:
        """Stage2: 抽卡建议（输出建议，不实际执行）"""
        start = time.monotonic()
        debate_data = stage1.result
        agreed_count = debate_data.get("agreed_issues", 0)
        total_score = debate_data.get("total_score", 50.0)

        # 根据辩论结果给出抽卡建议
        if total_score < 60:
            suggestion = "建议使用 gacha_cascade 模式，3个模型并行抽卡，重点优化爽点和节奏"
            recommended_mode = "gacha_cascade"
            min_candidates = 3
        elif total_score < 80:
            suggestion = "建议使用 single_fix 模式针对性修复，重点处理达成共识的问题"
            recommended_mode = "single_fix"
            min_candidates = 1
        else:
            suggestion = "质量良好，可使用 gacha_vibe 模式做创意性微调"
            recommended_mode = "gacha_vibe"
            min_candidates = 2

        result = {
            "recommended_mode": recommended_mode,
            "min_candidates": min_candidates,
            "suggestion": suggestion,
            "focus_issues": agreed_count,
            "note": "本阶段仅输出建议，不实际调用抽卡引擎",
        }
        duration = (time.monotonic() - start) * 1000
        return PipelineStage(
            stage_name="Stage2_抽卡建议",
            status="success",
            result=result,
            duration_ms=round(duration, 2),
        )

    def _stage3_critic_verification(self, stage1: PipelineStage) -> PipelineStage:
        """Stage3: CRITIC验证（核心）"""
        start = time.monotonic()
        debate_data = stage1.result
        revision_suggestions = debate_data.get("revision_suggestions", [])

        verifications: list[dict[str, Any]] = []
        actionable_count = 0
        for sug in revision_suggestions:
            verification = self._critic_verify_suggestion(
                sug.get("issue", ""), sug.get("suggestion", "")
            )
            verifications.append(verification.to_dict())
            if verification.actionable:
                actionable_count += 1

        result = {
            "total_suggestions": len(revision_suggestions),
            "actionable_count": actionable_count,
            "actionable_rate": round(actionable_count / max(1, len(revision_suggestions)), 2),
            "verifications": verifications,
        }
        duration = (time.monotonic() - start) * 1000
        return PipelineStage(
            stage_name="Stage3_CRITIC验证",
            status="success",
            result=result,
            duration_ms=round(duration, 2),
        )

    def _stage4_reflexion(self, stage1: PipelineStage) -> PipelineStage:
        """Stage4: Reflexion修订（核心）"""
        start = time.monotonic()
        debate_data = stage1.result
        rounds = debate_data.get("rounds", [])

        unresolved: list[str] = []
        for r in rounds:
            unresolved.extend(r.get("issues_unresolved", []))

        reflexion_entries: list[dict[str, Any]] = []
        for desc in list(set(unresolved))[:5]:
            entry = self._generate_reflexion(desc, [])
            reflexion_entries.append(entry.to_dict())

        result = {
            "unresolved_count": len(set(unresolved)),
            "reflexion_entries": reflexion_entries,
            "note": "对未解决问题生成结构化反思：根因→修改方向→预期效果",
        }
        duration = (time.monotonic() - start) * 1000
        return PipelineStage(
            stage_name="Stage4_Reflexion修订",
            status="success",
            result=result,
            duration_ms=round(duration, 2),
        )

    def _stage5_final_review(
        self,
        text: str,
        chapter: int,
        stage1: PipelineStage,
        stage3: PipelineStage,
        stage4: PipelineStage,
    ) -> PipelineStage:
        """Stage5: 终评（核心）"""
        start = time.monotonic()
        debate_data = stage1.result
        total_score = debate_data.get("total_score", 0.0)
        agreed = debate_data.get("agreed_issues", 0)
        unresolved = debate_data.get("unresolved_issues", 0)

        # 综合终评
        actionable_rate = stage3.result.get("actionable_rate", 0.0)
        reflexion_count = stage4.result.get("unresolved_count", 0)

        # 终评分数 = 辩论分数 * 0.7 + 可执行率 * 20 * 0.2 + (10 - 反思数) * 0.1
        final_score = (
            total_score * 0.7 + actionable_rate * 20 * 0.2 + max(0, 10 - reflexion_count) * 0.1
        )
        final_score = round(max(0.0, min(100.0, final_score)), 1)

        if final_score >= 85:
            verdict = "优秀，可发布"
        elif final_score >= 70:
            verdict = "良好，建议 minor 修订后发布"
        elif final_score >= 60:
            verdict = "及格，需要 major 修订"
        else:
            verdict = "不合格，建议重写"

        result = {
            "final_score": final_score,
            "debate_score": total_score,
            "agreed_issues": agreed,
            "unresolved_issues": unresolved,
            "actionable_rate": actionable_rate,
            "verdict": verdict,
        }
        duration = (time.monotonic() - start) * 1000
        return PipelineStage(
            stage_name="Stage5_终评",
            status="success",
            result=result,
            duration_ms=round(duration, 2),
        )

    def _stage6_polish_suggestion(self, text: str, stage5: PipelineStage) -> PipelineStage:
        """Stage6: 润色建议（输出建议，不实际执行）"""
        start = time.monotonic()
        final_score = stage5.result.get("final_score", 50.0)
        verdict = stage5.result.get("verdict", "")

        # 基于终评给出润色建议
        suggestions: list[str] = []
        if final_score < 70:
            suggestions.append("重点润色前1/3内容，提升开篇吸引力")
            suggestions.append("检查并优化对话比例，建议提升到15-25%")
        if final_score < 85:
            suggestions.append("优化章末钩子，设置悬念或冲突延续")
            suggestions.append("统一语言风格，去除AI痕迹和重复用词")
        suggestions.append("通读全文，检查错别字和标点符号")

        result = {
            "polish_suggestions": suggestions,
            "based_on_verdict": verdict,
            "note": "本阶段仅输出润色建议，不实际执行润色",
        }
        duration = (time.monotonic() - start) * 1000
        return PipelineStage(
            stage_name="Stage6_润色建议",
            status="success",
            result=result,
            duration_ms=round(duration, 2),
        )

    def _stage7_knowledge_update(
        self, text: str, chapter: int, stage1: PipelineStage
    ) -> PipelineStage:
        """Stage7: 知识更新建议（输出建议，不实际执行）"""
        start = time.monotonic()
        debate_data = stage1.result
        agreed = debate_data.get("agreed_issues", 0)
        unresolved = debate_data.get("unresolved_issues", 0)

        # 基于辩论结果给出知识图谱更新建议
        update_suggestions: list[dict[str, Any]] = []
        if agreed > 0:
            update_suggestions.append(
                {
                    "type": "character",
                    "action": "review",
                    "reason": f"有{agreed}个问题达成共识，需检查相关人物设定是否一致",
                }
            )
        if unresolved > 0:
            update_suggestions.append(
                {
                    "type": "plot",
                    "action": "flag",
                    "reason": f"有{unresolved}个未解决问题，建议在知识图谱中标记为待确认",
                }
            )
        update_suggestions.append(
            {
                "type": "world",
                "action": "sync",
                "reason": f"第{chapter}章内容已更新，建议同步世界观知识图谱",
            }
        )

        result = {
            "update_suggestions": update_suggestions,
            "chapter": chapter,
            "note": "本阶段仅输出知识更新建议，不实际修改知识图谱",
        }
        duration = (time.monotonic() - start) * 1000
        return PipelineStage(
            stage_name="Stage7_知识更新建议",
            status="success",
            result=result,
            duration_ms=round(duration, 2),
        )

    @staticmethod
    def _generate_pipeline_summary(
        stages: list[PipelineStage], final_score: float, passed: bool
    ) -> str:
        """生成流水线摘要"""
        success_count = sum(1 for s in stages if s.status == "success")
        status_text = "通过" if passed else "未通过"
        stage_names = " → ".join(s.stage_name for s in stages)
        return (
            f"8阶段流水线完成：{success_count}/{len(stages)}阶段成功 | "
            f"终评分数: {final_score}/100 ({status_text}) | "
            f"流程: {stage_names}"
        )
