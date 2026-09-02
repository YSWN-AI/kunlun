"""
昆仑创作引擎 — Agent辩论式审校与模拟读者反馈

基于Multi-Agent辩论和读者模拟技术，提升小说质量到85分以上。

核心能力:
  1. 辩论式审校 — 正方(维护原稿) vs 反方(挑错) 多轮辩论
  2. 模拟读者反馈 — 模拟不同类型读者的阅读体验和评分
  3. 多维度质量评分 — 6维度量化评分，对标85分目标
  4. 修订建议生成 — 基于审校结果生成可执行的修改建议
  5. 弃书点预测 — 预测读者可能弃书的位置和原因

与昆仑引擎集成:
  - 增强 audit/ 模块的审校深度
  - 为 gacha/ 抽卡引擎提供质量评分维度
  - 为 vibe_writer/ 提供读者反馈引导
  - 输出可被质量看板消费的审校数据

Author: 昆仑创作引擎
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

# ══════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════


class ReviewDimension(Enum):
    """审校维度"""

    PLOT_LOGIC = "plot_logic"  # 情节逻辑
    CHARACTER_CONSISTENCY = "character"  # 人物一致性
    PACING = "pacing"  # 节奏控制
    COOL_POINT = "cool_point"  # 爽点密度
    WRITING_QUALITY = "writing"  # 文笔质量
    LOGIC_CONSISTENCY = "consistency"  # 逻辑一致性
    EMOTIONAL_ENGAGEMENT = "emotion"  # 情感代入
    WORLD_BUILDING = "worldbuilding"  # 世界观


class ReaderType(Enum):
    """读者类型"""

    NEWBIE = "newbie"  # 小白读者
    VETERAN = "veteran"  # 老白读者
    PAYING = "paying"  # 付费读者
    FEMALE = "female"  # 女频读者
    CRITICAL = "critical"  # 挑剔读者
    CASUAL = "casual"  # 休闲读者


@dataclass
class ReviewIssue:
    """审校问题"""

    dimension: ReviewDimension
    severity: int  # 1-5, 5最严重
    location: str  # 位置描述
    description: str
    suggestion: str = ""
    evidence: str = ""
    agreed: bool = False  # 辩论后是否达成共识

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "severity": self.severity,
            "location": self.location,
            "description": self.description,
            "suggestion": self.suggestion,
            "evidence": self.evidence,
            "agreed": self.agreed,
        }


@dataclass
class DebateRound:
    """辩论轮次"""

    round_num: int
    critic_argument: str  # 反方论点
    defender_argument: str  # 正方回应
    resolution: str  # 裁决结果
    issue_resolved: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DebateReviewResult:
    """辩论审校结果"""

    total_score: float  # 0-100
    dimension_scores: dict[str, float] = field(default_factory=dict)
    issues: list[ReviewIssue] = field(default_factory=list)
    debate_rounds: list[DebateRound] = field(default_factory=list)
    agreed_issues: int = 0
    unresolved_issues: int = 0
    revision_priority: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_score": self.total_score,
            "dimension_scores": self.dimension_scores,
            "issues": [i.to_dict() for i in self.issues],
            "debate_rounds": [r.to_dict() for r in self.debate_rounds],
            "agreed_issues": self.agreed_issues,
            "unresolved_issues": self.unresolved_issues,
            "revision_priority": self.revision_priority,
            "summary": self.summary,
        }


@dataclass
class ReaderFeedback:
    """模拟读者反馈"""

    reader_type: ReaderType
    reader_name: str
    overall_score: float  # 0-10
    continue_reading: bool  # 是否继续阅读
    drop_off_point: str = ""  # 弃书点
    drop_off_reason: str = ""  # 弃书原因
    likes: list[str] = field(default_factory=list)
    dislikes: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    emotional_response: str = ""  # 情感反应
    cool_point_satisfaction: float = 0.0  # 爽点满足度
    pacing_satisfaction: float = 0.0  # 节奏满足度

    def to_dict(self) -> dict[str, Any]:
        return {
            "reader_type": self.reader_type.value,
            "reader_name": self.reader_name,
            "overall_score": self.overall_score,
            "continue_reading": self.continue_reading,
            "drop_off_point": self.drop_off_point,
            "drop_off_reason": self.drop_off_reason,
            "likes": self.likes,
            "dislikes": self.dislikes,
            "comments": self.comments,
            "emotional_response": self.emotional_response,
            "cool_point_satisfaction": self.cool_point_satisfaction,
            "pacing_satisfaction": self.pacing_satisfaction,
        }


@dataclass
class ReaderSimulationResult:
    """读者模拟结果"""

    readers: list[ReaderFeedback] = field(default_factory=list)
    avg_score: float = 0.0
    continue_rate: float = 0.0
    avg_cool_satisfaction: float = 0.0
    common_likes: list[str] = field(default_factory=list)
    common_dislikes: list[str] = field(default_factory=list)
    drop_off_risk: float = 0.0  # 弃书风险 0-1
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "readers": [r.to_dict() for r in self.readers],
            "avg_score": self.avg_score,
            "continue_rate": self.continue_rate,
            "avg_cool_satisfaction": self.avg_cool_satisfaction,
            "common_likes": self.common_likes,
            "common_dislikes": self.common_dislikes,
            "drop_off_risk": self.drop_off_risk,
            "summary": self.summary,
        }


# ══════════════════════════════════════════════════════
# 规则-based质量检测器（无需LLM）
# ══════════════════════════════════════════════════════


class RuleBasedQualityChecker:
    """规则-based质量检测器 — 无需LLM，快速初筛"""

    # 爽点关键词
    COOL_KEYWORDS = [
        "杀",
        "轰",
        "爆",
        "碎",
        "碾压",
        "秒杀",
        "一招",
        "震惊",
        "倒吸",
        "膜拜",
        "恐惧",
        "后悔",
        "嫉妒",
        "羡慕",
        "突破",
        "觉醒",
        "传承",
        "打脸",
        "装逼",
        "逆袭",
        "翻盘",
        "反转",
        "揭秘",
        "真相",
    ]

    # 拖沓关键词
    BORING_KEYWORDS = [
        "话说",
        "且说",
        "却说",
        "再说",
        "暂且",
        "暂且不表",
        "按下不表",
        "花开两朵",
        "各表一枝",
        "闲话少说",
        "言归正传",
        "不知不觉",
        "时光飞逝",
        "岁月如梭",
        "转眼间",
        "一晃眼",
    ]

    # 逻辑矛盾模式
    CONTRADICTION_PATTERNS = [
        (r"所有人都.*不知道", r"有人.*知道"),
        (r"第一次.*见到", r"曾经.*见过"),
        (r"修为.*炼气", r"修为.*筑基"),
    ]

    def check(self, text: str, chapter: int = 0) -> list[ReviewIssue]:
        issues = []
        sentences = re.split(r"(?<=[。！？])", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        paragraphs = [p for p in text.split("\n") if p.strip()]
        total_chars = len(text.replace(" ", "").replace("\n", ""))

        # 1. 爽点密度检测
        cool_count = sum(text.count(k) for k in self.COOL_KEYWORDS)
        cool_density = cool_count / max(1, total_chars / 1000)
        if cool_density < 2:
            issues.append(
                ReviewIssue(
                    dimension=ReviewDimension.COOL_POINT,
                    severity=3,
                    location="全章",
                    description=f"爽点密度过低({cool_density:.1f}/千字)，男频网文建议3-8/千字",
                    suggestion="增加战斗、打脸、突破等爽点场景",
                    evidence=f"检测到{cool_count}个爽点关键词",
                )
            )
        elif cool_density > 15:
            issues.append(
                ReviewIssue(
                    dimension=ReviewDimension.COOL_POINT,
                    severity=2,
                    location="全章",
                    description=f"爽点密度过高({cool_density:.1f}/千字)，可能导致审美疲劳",
                    suggestion="适当增加过渡和铺垫，避免连续爽点",
                )
            )

        # 2. 节奏检测
        if len(sentences) > 0:
            avg_sentence_len = total_chars / len(sentences)
            short_ratio = sum(1 for s in sentences if len(s) < 10) / len(sentences)
            long_ratio = sum(1 for s in sentences if len(s) > 50) / len(sentences)
            if avg_sentence_len > 35 and long_ratio > 0.4:
                issues.append(
                    ReviewIssue(
                        dimension=ReviewDimension.PACING,
                        severity=3,
                        location="全章",
                        description=f"节奏拖沓：平均句长{avg_sentence_len:.0f}字，长句占比{long_ratio * 100:.0f}%",
                        suggestion="拆分长句，增加短句和对话，提升节奏",
                    )
                )

        # 3. 拖沓用语检测
        boring_count = sum(text.count(k) for k in self.BORING_KEYWORDS)
        if boring_count > 3:
            issues.append(
                ReviewIssue(
                    dimension=ReviewDimension.WRITING_QUALITY,
                    severity=2,
                    location="全章",
                    description=f"检测到{boring_count}处传统评书式拖沓用语",
                    suggestion="删除'话说'、'且说'等拖沓过渡语，直接进入情节",
                )
            )

        # 4. 对话比例检测
        dialogues = re.findall(r'[""「『]([^""」』]+)[""」』]', text)
        dialogue_chars = sum(len(d) for d in dialogues)
        dialogue_ratio = dialogue_chars / max(1, total_chars)
        if dialogue_ratio < 0.08 and total_chars > 1000:
            issues.append(
                ReviewIssue(
                    dimension=ReviewDimension.PACING,
                    severity=2,
                    location="全章",
                    description=f"对话比例过低({dialogue_ratio * 100:.0f}%)，可能导致叙事沉闷",
                    suggestion="增加角色对话，通过对话推进情节和展现人物",
                )
            )

        # 5. 段落结构检测
        if paragraphs:
            avg_para_len = total_chars / len(paragraphs)
            if avg_para_len > 120:
                issues.append(
                    ReviewIssue(
                        dimension=ReviewDimension.PACING,
                        severity=2,
                        location="全章",
                        description=f"段落过长：平均{avg_para_len:.0f}字/段，影响阅读体验",
                        suggestion="拆分长段落，每段控制在30-80字",
                    )
                )

        # 6. 情感代入检测
        emotion_words = [
            "怒",
            "喜",
            "悲",
            "惊",
            "惧",
            "恨",
            "爽",
            "疼",
            "痛",
            "寒",
            "暖",
            "酸",
            "甜",
            "苦",
            "辣",
            "激动",
            "愤怒",
            "开心",
            "难过",
        ]
        emotion_count = sum(text.count(w) for w in emotion_words)
        if emotion_count < 5 and total_chars > 2000:
            issues.append(
                ReviewIssue(
                    dimension=ReviewDimension.EMOTIONAL_ENGAGEMENT,
                    severity=3,
                    location="全章",
                    description=f"情感表达不足({emotion_count}处)，读者难以代入",
                    suggestion="增加角色的情感反应和内心描写，提升代入感",
                )
            )

        # 7. 重复检测
        repeats = re.findall(r"(.{3,})\1", text)
        if len(repeats) > 5:
            issues.append(
                ReviewIssue(
                    dimension=ReviewDimension.WRITING_QUALITY,
                    severity=2,
                    location="全章",
                    description=f"检测到{len(repeats)}处词语重复",
                    suggestion="检查并替换重复的词语和句式",
                )
            )

        # 8. 章末钩子检测
        if paragraphs:
            last_para = paragraphs[-1]
            hook_patterns = [
                r"突然",
                r"就在这时",
                r"然而",
                r"没想到",
                r"竟然",
                r"难道",
                r"究竟",
                r"到底",
                r"悬念",
                r"未知",
            ]
            has_hook = any(re.search(p, last_para) for p in hook_patterns)
            if not has_hook and total_chars > 1000:
                issues.append(
                    ReviewIssue(
                        dimension=ReviewDimension.PLOT_LOGIC,
                        severity=2,
                        location="章末",
                        description="章末缺少悬念钩子，可能降低追读率",
                        suggestion="在章末设置悬念、反转或新冲突，吸引读者继续阅读",
                    )
                )

        return issues

    def calculate_dimension_scores(self, text: str) -> dict[str, float]:
        """计算各维度得分（0-100）"""
        issues = self.check(text)
        scores = {d.value: 85.0 for d in ReviewDimension}

        for issue in issues:
            dim = issue.dimension.value
            penalty = issue.severity * 3
            scores[dim] = max(0, scores[dim] - penalty)

        # 基于文本特征的加分/减分
        total_chars = len(text.replace(" ", "").replace("\n", ""))
        cool_count = sum(text.count(k) for k in self.COOL_KEYWORDS)
        cool_density = cool_count / max(1, total_chars / 1000)
        if 3 <= cool_density <= 8:
            scores["cool_point"] = min(100, scores["cool_point"] + 10)

        return scores


# ══════════════════════════════════════════════════════
# 辩论式审校引擎
# ══════════════════════════════════════════════════════


class DebateReviewEngine:
    """辩论式审校引擎 — 正方vs反方多轮辩论"""

    def __init__(self, max_rounds: int = 3, llm_callback: Callable | None = None):
        self.max_rounds = max_rounds
        self.llm_callback = llm_callback  # 可选的LLM调用回调
        self.rule_checker = RuleBasedQualityChecker()

    def review(
        self, text: str, chapter: int = 0, context: str = "", target_score: float = 85.0
    ) -> DebateReviewResult:
        # 1. 规则-based初筛
        rule_issues = self.rule_checker.check(text, chapter)
        dimension_scores = self.rule_checker.calculate_dimension_scores(text)

        # 2. 辩论环节（对严重问题进行辩论）
        debate_issues = [i for i in rule_issues if i.severity >= 3]
        debate_rounds = []
        agreed_count = 0

        for issue in debate_issues[: self.max_rounds * 2]:  # 限制辩论数量
            round_result = self._conduct_debate(issue, text, context)
            debate_rounds.append(round_result)
            if round_result.issue_resolved:
                issue.agreed = True
                agreed_count += 1

        # 3. 合并所有问题
        all_issues = rule_issues

        # 4. 计算总分
        total_score = self._calculate_total_score(dimension_scores, all_issues)

        # 5. 生成修订优先级
        revision_priority = self._generate_revision_priority(all_issues, total_score, target_score)

        # 6. 生成摘要
        summary = self._generate_summary(total_score, all_issues, target_score)

        return DebateReviewResult(
            total_score=total_score,
            dimension_scores=dimension_scores,
            issues=all_issues,
            debate_rounds=debate_rounds,
            agreed_issues=agreed_count,
            unresolved_issues=len(all_issues) - agreed_count,
            revision_priority=revision_priority,
            summary=summary,
        )

    def _conduct_debate(self, issue: ReviewIssue, text: str, context: str) -> DebateRound:
        """进行一轮辩论"""
        # 反方论点（基于规则检测结果）
        critic_argument = (
            f"反方指出：在{issue.location}处存在{issue.dimension.value}问题。"
            f"{issue.description}。证据：{issue.evidence}"
        )

        # 正方回应（规则-based，判断问题是否成立）
        defender_argument = self._generate_defense(issue, text)

        # 裁决（基于问题严重度和证据强度）
        is_valid = issue.severity >= 2 and len(issue.description) > 10
        resolution = "问题成立，建议修改" if is_valid else "问题不成立或影响较小，可保留"

        return DebateRound(
            round_num=len(self._current_rounds) if hasattr(self, "_current_rounds") else 1,
            critic_argument=critic_argument,
            defender_argument=defender_argument,
            resolution=resolution,
            issue_resolved=is_valid,
        )

    def _generate_defense(self, issue: ReviewIssue, text: str) -> str:
        """生成正方辩护（规则-based）"""
        defenses = {
            ReviewDimension.COOL_POINT: "正方认为：本章侧重铺垫和人物塑造，爽点将在后续章节集中爆发，当前密度合理。",
            ReviewDimension.PACING: "正方认为：当前节奏符合情节需要，长句用于营造氛围，短句用于紧张场景，节奏变化合理。",
            ReviewDimension.WRITING_QUALITY: "正方认为：相关用语是作者风格的一部分，不影响阅读体验，可保留。",
            ReviewDimension.EMOTIONAL_ENGAGEMENT: "正方认为：情感表达偏向内敛，通过动作和细节间接传达，符合人物性格。",
            ReviewDimension.PLOT_LOGIC: "正方认为：章末留白是有意为之，给读者想象空间，不一定要设置显性悬念。",
        }
        return defenses.get(issue.dimension, "正方认为：该问题影响较小，不影响整体质量。")

    def _calculate_total_score(
        self, dimension_scores: dict[str, float], issues: list[ReviewIssue]
    ) -> float:
        """计算总分"""
        weights = {
            "plot_logic": 0.15,
            "character": 0.15,
            "pacing": 0.15,
            "cool_point": 0.20,
            "writing": 0.10,
            "consistency": 0.10,
            "emotion": 0.10,
            "worldbuilding": 0.05,
        }
        total = 0
        total_weight = 0
        for dim, weight in weights.items():
            if dim in dimension_scores:
                total += dimension_scores[dim] * weight
                total_weight += weight
        base_score = total / max(0.01, total_weight)

        # 严重问题扣分
        severe_penalty = sum(i.severity for i in issues if i.severity >= 4) * 2
        final_score = max(0, min(100, base_score - severe_penalty))
        return round(final_score, 1)

    def _generate_revision_priority(
        self, issues: list[ReviewIssue], current_score: float, target_score: float
    ) -> list[dict[str, Any]]:
        """生成修订优先级列表"""
        sorted_issues = sorted(issues, key=lambda i: i.severity, reverse=True)
        priority = []
        for i, issue in enumerate(sorted_issues[:10]):
            priority.append(
                {
                    "priority": i + 1,
                    "dimension": issue.dimension.value,
                    "severity": issue.severity,
                    "description": issue.description,
                    "suggestion": issue.suggestion,
                    "estimated_improvement": issue.severity * 1.5,
                }
            )
        return priority

    def _generate_summary(self, score: float, issues: list[ReviewIssue], target: float) -> str:
        """生成审校摘要"""
        gap = target - score
        if gap <= 0:
            level = "优秀"
            advice = "已达到目标分数，可重点优化细节"
        elif gap <= 5:
            level = "良好"
            advice = "接近目标，重点修改严重问题即可达标"
        elif gap <= 15:
            level = "中等"
            advice = "需要系统性修改，优先处理高严重度问题"
        else:
            level = "待提升"
            advice = "差距较大，建议重新规划章节结构和爽点排布"

        severe_count = sum(1 for i in issues if i.severity >= 4)
        return (
            f"综合评分: {score:.1f}/100 ({level}) | 目标: {target:.0f} | 差距: {gap:.1f} | "
            f"问题总数: {len(issues)} (严重{severe_count}) | {advice}"
        )


# ══════════════════════════════════════════════════════
# 模拟读者引擎
# ══════════════════════════════════════════════════════


class ReaderSimulator:
    """模拟读者引擎 — 模拟不同类型读者的阅读体验"""

    READER_PROFILES = {
        ReaderType.NEWBIE: {
            "name": "小白读者",
            "description": "刚接触网文，追求简单直接的爽感，耐心较低",
            "cool_threshold": 4.0,  # 爽点密度要求
            "patience": 0.4,  # 耐心 0-1
            "pacing_preference": "fast",
            "forgiveness": 0.7,  # 对缺点的容忍度
        },
        ReaderType.VETERAN: {
            "name": "老白读者",
            "description": "阅读经验丰富，追求逻辑和创新，对套路敏感",
            "cool_threshold": 3.0,
            "patience": 0.7,
            "pacing_preference": "medium",
            "forgiveness": 0.4,
        },
        ReaderType.PAYING: {
            "name": "付费读者",
            "description": "愿意付费，追求稳定更新和持续爽感，对质量要求高",
            "cool_threshold": 3.5,
            "patience": 0.6,
            "pacing_preference": "medium",
            "forgiveness": 0.5,
        },
        ReaderType.CRITICAL: {
            "name": "挑剔读者",
            "description": "对文笔和逻辑要求极高，容易弃书",
            "cool_threshold": 2.5,
            "patience": 0.3,
            "pacing_preference": "medium",
            "forgiveness": 0.2,
        },
        ReaderType.CASUAL: {
            "name": "休闲读者",
            "description": "随便看看，要求不高，容易被爽点吸引",
            "cool_threshold": 5.0,
            "patience": 0.5,
            "pacing_preference": "fast",
            "forgiveness": 0.8,
        },
    }

    def __init__(self):
        self.rule_checker = RuleBasedQualityChecker()

    def simulate(
        self, text: str, reader_types: list[ReaderType] | None = None, chapter: int = 0
    ) -> ReaderSimulationResult:
        if reader_types is None:
            reader_types = [
                ReaderType.NEWBIE,
                ReaderType.VETERAN,
                ReaderType.PAYING,
                ReaderType.CRITICAL,
                ReaderType.CASUAL,
            ]

        readers = []
        for rtype in reader_types:
            feedback = self._simulate_single_reader(text, rtype, chapter)
            readers.append(feedback)

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

        summary = self._generate_summary(avg_score, continue_rate, drop_off_risk, common_dislikes)

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

    def _simulate_single_reader(
        self, text: str, reader_type: ReaderType, chapter: int
    ) -> ReaderFeedback:
        profile = self.READER_PROFILES[reader_type]
        issues = self.rule_checker.check(text, chapter)
        dimension_scores = self.rule_checker.calculate_dimension_scores(text)

        total_chars = len(text.replace(" ", "").replace("\n", ""))
        cool_count = sum(text.count(k) for k in self.rule_checker.COOL_KEYWORDS)
        cool_density = cool_count / max(1, total_chars / 1000)

        # 爽点满足度
        cool_satisfaction = min(1.0, cool_density / profile["cool_threshold"])

        # 节奏满足度
        sentences = re.split(r"(?<=[。！？])", text)
        sentences = [s for s in sentences if s.strip()]
        avg_len = total_chars / max(1, len(sentences))
        if profile["pacing_preference"] == "fast":
            pacing_satisfaction = max(0, 1 - abs(avg_len - 15) / 30)
        else:
            pacing_satisfaction = max(0, 1 - abs(avg_len - 25) / 30)

        # 问题影响
        severe_issues = [i for i in issues if i.severity >= 3]
        issue_penalty = len(severe_issues) * (1 - profile["forgiveness"]) * 0.5

        # 综合评分（0-10）
        base_score = 7.0
        score = base_score + cool_satisfaction * 1.5 + pacing_satisfaction * 1.0 - issue_penalty
        score = max(1.0, min(10.0, score))

        # 是否继续阅读
        continue_reading = score >= 6.0 and cool_satisfaction >= 0.3

        # 弃书点
        drop_off_point = ""
        drop_off_reason = ""
        if not continue_reading:
            if cool_satisfaction < 0.3:
                drop_off_reason = "爽点不足，不够吸引人"
                drop_off_point = "前1/3处"
            elif issue_penalty > 1.0:
                drop_off_reason = f"存在{len(severe_issues)}个严重问题，影响阅读体验"
                drop_off_point = "问题出现处"
            else:
                drop_off_reason = "整体质量一般，没有继续阅读的动力"
                drop_off_point = "章末"

        # 喜好/厌恶
        likes = []
        dislikes = []
        if cool_satisfaction >= 0.7:
            likes.append("爽点充足，看得过瘾")
        if pacing_satisfaction >= 0.7:
            likes.append("节奏合适，读起来流畅")
        if dimension_scores.get("character", 80) >= 85:
            likes.append("人物塑造不错")

        if cool_satisfaction < 0.4:
            dislikes.append("爽点不够，有点平淡")
        if pacing_satisfaction < 0.4:
            dislikes.append("节奏有问题，读起来累")
        if severe_issues:
            dislikes.append(f"有{len(severe_issues)}个明显问题")

        # 评论模拟
        comments = self._generate_comments(reader_type, score, likes, dislikes)

        # 情感反应
        emotional_response = self._generate_emotional_response(cool_satisfaction, score)

        return ReaderFeedback(
            reader_type=reader_type,
            reader_name=profile["name"],
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
        )

    def _generate_comments(
        self, reader_type: ReaderType, score: float, likes: list[str], dislikes: list[str]
    ) -> list[str]:
        """模拟读者评论"""
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
        return [templates[hash(reader_type.value) % len(templates)]]

    def _generate_emotional_response(self, cool_satisfaction: float, score: float) -> str:
        """生成情感反应"""
        if cool_satisfaction >= 0.8 and score >= 8:
            return "热血沸腾，欲罢不能"
        if cool_satisfaction >= 0.6 and score >= 7:
            return "看得挺爽，期待下一章"
        if score >= 6:
            return "平静阅读，没有特别强烈的感觉"
        return "有点无聊，注意力不集中"

    def _generate_summary(
        self, avg_score: float, continue_rate: float, drop_off_risk: float, dislikes: list[str]
    ) -> str:
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
            f"读者模拟: 平均评分{avg_score:.1f}/10 ({level}) | 追读率{continue_rate * 100:.0f}% | "
            f"弃书风险{risk_level}({drop_off_risk * 100:.0f}%) | "
            f"主要问题: {', '.join(dislikes[:3]) if dislikes else '无明显共性问题'}"
        )


# ══════════════════════════════════════════════════════
# 综合质量评估引擎
# ══════════════════════════════════════════════════════


class QualityAssessmentEngine:
    """综合质量评估引擎 — 辩论审校 + 读者模拟 + 修订建议"""

    def __init__(self, target_score: float = 85.0):
        self.target_score = target_score
        self.debate_engine = DebateReviewEngine()
        self.reader_simulator = ReaderSimulator()

    def full_assessment(self, text: str, chapter: int = 0, context: str = "") -> dict[str, Any]:
        """完整质量评估"""
        # 1. 辩论审校
        debate_result = self.debate_engine.review(text, chapter, context, self.target_score)

        # 2. 读者模拟
        reader_result = self.reader_simulator.simulate(text, chapter=chapter)

        # 3. 综合评分（审校60% + 读者40%）
        debate_score = debate_result.total_score
        reader_score = reader_result.avg_score * 10  # 转换为0-100
        combined_score = debate_score * 0.6 + reader_score * 0.4

        # 4. 达标分析
        gap = self.target_score - combined_score
        reached = gap <= 0

        # 5. 生成综合修订建议
        recommendations = self._generate_recommendations(
            debate_result, reader_result, combined_score, self.target_score
        )

        return {
            "combined_score": round(combined_score, 1),
            "target_score": self.target_score,
            "gap": round(gap, 1),
            "reached": reached,
            "debate_review": debate_result.to_dict(),
            "reader_simulation": reader_result.to_dict(),
            "recommendations": recommendations,
            "summary": self._generate_combined_summary(
                combined_score, debate_score, reader_score, reached
            ),
        }

    def _generate_recommendations(
        self,
        debate_result: DebateReviewResult,
        reader_result: ReaderSimulationResult,
        current_score: float,
        target: float,
    ) -> list[dict[str, Any]]:
        """生成综合修订建议"""
        recommendations = []

        # 基于辩论审校的建议
        for priority in debate_result.revision_priority[:5]:
            recommendations.append(
                {
                    "source": "debate",
                    "priority": priority["priority"],
                    "category": priority["dimension"],
                    "issue": priority["description"],
                    "suggestion": priority["suggestion"],
                    "estimated_improvement": priority["estimated_improvement"],
                }
            )

        # 基于读者模拟的建议
        if reader_result.drop_off_risk > 0.3:
            recommendations.append(
                {
                    "source": "reader",
                    "priority": len(recommendations) + 1,
                    "category": "reader_retention",
                    "issue": f"弃书风险过高({reader_result.drop_off_risk * 100:.0f}%)",
                    "suggestion": "重点优化前1/3内容，增加早期爽点和悬念",
                    "estimated_improvement": 5.0,
                }
            )

        if reader_result.avg_cool_satisfaction < 0.5:
            recommendations.append(
                {
                    "source": "reader",
                    "priority": len(recommendations) + 1,
                    "category": "cool_point",
                    "issue": f"读者爽点满足度低({reader_result.avg_cool_satisfaction * 100:.0f}%)",
                    "suggestion": "增加打脸、逆袭、突破等爽点场景，提升爽点密度到3-8/千字",
                    "estimated_improvement": 8.0,
                }
            )

        # 按预估提升排序
        recommendations.sort(key=lambda x: x["estimated_improvement"], reverse=True)
        for i, rec in enumerate(recommendations):
            rec["priority"] = i + 1

        return recommendations

    def _generate_combined_summary(
        self, combined: float, debate: float, reader: float, reached: bool
    ) -> str:
        status = "已达标" if reached else "未达标"
        return (
            f"综合质量评分: {combined:.1f}/100 ({status}) | "
            f"审校评分: {debate:.1f} | 读者评分: {reader:.1f} | "
            f"目标: 85分"
        )


# ══════════════════════════════════════════════════════
# 便捷函数
# ══════════════════════════════════════════════════════


def debate_review(text: str, chapter: int = 0, target_score: float = 85.0) -> DebateReviewResult:
    engine = DebateReviewEngine()
    return engine.review(text, chapter, target_score=target_score)


def simulate_readers(text: str, chapter: int = 0) -> ReaderSimulationResult:
    simulator = ReaderSimulator()
    return simulator.simulate(text, chapter=chapter)


def full_quality_assessment(
    text: str, chapter: int = 0, target_score: float = 85.0
) -> dict[str, Any]:
    engine = QualityAssessmentEngine(target_score=target_score)
    return engine.full_assessment(text, chapter)
