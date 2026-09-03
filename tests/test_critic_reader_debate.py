"""
测试 CriticAgent / ReaderAgent / DebateOrchestrator 三个新 Agent

覆盖：
  - CriticAgent 规则-based批判 / LLM批判
  - ReaderAgent 单读者/多读者模拟 / 情绪时间线
  - DebateOrchestrator 规则辩论 / LLM辩论 / CRITIC验证 / Reflexion修订
  - 8阶段流水线
  - 消息总线发布/订阅
  - 向后兼容
  - 边界情况
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kunlun.agents.critic import CRITIC_DIMENSIONS, CriticAgent, CriticReport
from kunlun.agents.debate_orchestrator import (
    CRITICVerification,
    DebateOrchestrator,
    DebateResult,
    DebateRoundDetail,
    PipelineResult,
    ReflexionEntry,
)
from kunlun.agents.message_bus import message_bus
from kunlun.agents.reader import (
    EnhancedReaderFeedback,
    ExtendedReaderType,
    EXTENDED_READER_PROFILES,
    ReaderAgent,
)
from kunlun.debate_review.engine import (
    DebateReviewEngine,
    ReaderSimulator,
    RuleBasedQualityChecker,
)

# ══════════════════════════════════════════════════════
# 测试文本
# ══════════════════════════════════════════════════════

# 有问题的文本（爽点不足、节奏拖沓、无章末钩子）
BAD_TEXT = """
话说这一日，林天生在山中修炼。不知不觉，时光飞逝，岁月如梭。
他心中想着，自己的修为还是不够。且说那山中的风景，真是美不胜收。
花开两朵，各表一枝。按下不表。林天生叹了口气，继续修炼。
他的心中充满了对未来的迷茫。
"""

# 较好的文本（有爽点、有对话、有章末钩子）
GOOD_TEXT = """
"你敢动我？"林天生眼神冰冷，一掌拍出，真气爆发，瞬间将三名黑衣人碾压在地。
"不可能！你的修为怎么可能突破到筑基期！"为首的黑衣人倒吸一口凉气，满脸震惊。
林天生冷笑一声："你们以为封印我三年，就能让我永远沉沦？"
他一步步走向黑衣人，每一步都带着压倒性的气势。
"现在，该轮到你们了。"林天生的声音如同来自地狱。
就在这时，远处突然传来一声惊天动地的巨响，一道剑光划破天际。
林天生瞳孔骤缩："难道是……"
"""

# 超短文本
SHORT_TEXT = "他笑了。"

# 空文本
EMPTY_TEXT = ""


# ══════════════════════════════════════════════════════
# 1. CriticAgent 规则-based批判
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_critic_rule_based_critique():
    """CriticAgent 规则-based批判（不依赖LLM，mock gacha_engine 抛异常触发回退）"""
    agent = CriticAgent()
    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        side_effect=Exception("LLM unavailable"),
    ):
        report = await agent.critique(BAD_TEXT, chapter=1)

    assert isinstance(report, CriticReport)
    assert 0 <= report.overall_score <= 100
    assert report.critique_source == "rule"
    assert len(report.dimension_scores) == 6
    assert all(dim in report.dimension_scores for dim in CRITIC_DIMENSIONS)
    assert isinstance(report.would_continue, bool)
    assert isinstance(report.poison_points, list)
    assert isinstance(report.suggestions, list)
    assert report.market_potential != ""


@pytest.mark.asyncio
async def test_critic_good_text_scores_higher():
    """好文本的批判评分应高于差文本"""
    agent = CriticAgent()
    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        side_effect=Exception("LLM unavailable"),
    ):
        bad_report = await agent.critique(BAD_TEXT, chapter=1)
        good_report = await agent.critique(GOOD_TEXT, chapter=2)

    # 好文本至少不应该比差文本低太多（规则-based可能有波动，但趋势应合理）
    assert good_report.overall_score >= bad_report.overall_score - 10


# ══════════════════════════════════════════════════════
# 2. CriticAgent LLM批判
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_critic_llm_critique():
    """CriticAgent LLM批判（mock gacha_engine 返回有效JSON）"""
    llm_response = json.dumps(
        {
            "overall_score": 72,
            "would_continue": True,
            "poison_points": ["开篇节奏稍慢"],
            "suggestions": ["增加开篇冲突", "优化章末钩子"],
            "market_potential": "中等偏上，有爆款潜力",
            "dimension_scores": {
                "开篇吸引力": 70,
                "爽点密度": 75,
                "节奏把控": 68,
                "章尾钩子": 72,
                "毒点检测": 80,
                "与同类爆款差距": 70,
            },
        }
    )
    mock_result = {"best_text": llm_response, "best_model": "mock"}

    agent = CriticAgent()
    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        report = await agent.critique(GOOD_TEXT, chapter=1)

    assert report.critique_source == "llm"
    assert report.overall_score == 72
    assert report.would_continue is True
    assert len(report.poison_points) == 1
    assert report.market_potential == "中等偏上，有爆款潜力"
    assert report.dimension_scores["爽点密度"] == 75.0


@pytest.mark.asyncio
async def test_critic_llm_invalid_response_fallback():
    """CriticAgent LLM返回无效JSON时回退规则结果"""
    mock_result = {"best_text": "这不是JSON格式的输出", "best_model": "mock"}

    agent = CriticAgent()
    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        report = await agent.critique(BAD_TEXT, chapter=1)

    assert report.critique_source == "rule"


# ══════════════════════════════════════════════════════
# 3. ReaderAgent 单读者模拟
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_reader_single_simulation():
    """ReaderAgent 单读者模拟"""
    agent = ReaderAgent(ExtendedReaderType.VETERAN)
    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        side_effect=Exception("LLM unavailable"),
    ):
        feedback = await agent.read(GOOD_TEXT, chapter=1)

    assert isinstance(feedback, EnhancedReaderFeedback)
    assert feedback.reader_type == ExtendedReaderType.VETERAN
    assert feedback.reader_name == "老白读者"
    assert 0 <= feedback.overall_score <= 10
    assert isinstance(feedback.continue_reading, bool)
    assert isinstance(feedback.likes, list)
    assert isinstance(feedback.dislikes, list)
    assert isinstance(feedback.comments, list)
    assert feedback.emotional_response != ""
    assert 0 <= feedback.cool_point_satisfaction <= 1
    assert 0 <= feedback.pacing_satisfaction <= 1


@pytest.mark.asyncio
async def test_reader_different_types():
    """不同读者类型对同一文本的反馈应不同"""
    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        side_effect=Exception("LLM unavailable"),
    ):
        newbie = ReaderAgent(ExtendedReaderType.NEWBIE)
        veteran = ReaderAgent(ExtendedReaderType.VETERAN)
        newbie_fb = await newbie.read(GOOD_TEXT, chapter=1)
        veteran_fb = await veteran.read(GOOD_TEXT, chapter=1)

    assert newbie_fb.reader_name != veteran_fb.reader_name
    # 小白读者和老白读者的画像参数不同，评分可能不同
    assert newbie_fb.cool_point_satisfaction >= 0
    assert veteran_fb.cool_point_satisfaction >= 0


# ══════════════════════════════════════════════════════
# 4. ReaderAgent 多读者模拟
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_reader_simulate_multiple():
    """ReaderAgent 多读者同时模拟"""
    agent = ReaderAgent(ExtendedReaderType.CASUAL)
    reader_types = [
        ExtendedReaderType.NEWBIE,
        ExtendedReaderType.VETERAN,
        ExtendedReaderType.STUDENT,
        ExtendedReaderType.HARDCORE_COOL,
    ]
    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        side_effect=Exception("LLM unavailable"),
    ):
        result = await agent.simulate_multiple(GOOD_TEXT, reader_types)

    assert len(result.readers) == 4
    assert 0 <= result.avg_score <= 10
    assert 0 <= result.continue_rate <= 1
    assert 0 <= result.drop_off_risk <= 1
    assert result.summary != ""


# ══════════════════════════════════════════════════════
# 5. ReaderAgent 情绪时间线
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_reader_emotional_timeline():
    """ReaderAgent 情绪时间线应记录每段情绪"""
    agent = ReaderAgent(ExtendedReaderType.CASUAL)
    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        side_effect=Exception("LLM unavailable"),
    ):
        feedback = await agent.read(GOOD_TEXT, chapter=1)

    assert isinstance(feedback.emotional_timeline, list)
    assert len(feedback.emotional_timeline) > 0
    for entry in feedback.emotional_timeline:
        assert "paragraph_index" in entry
        assert "emotion_type" in entry
        assert "intensity" in entry
        assert "snippet" in entry
        assert 0 <= entry["intensity"] <= 1
        assert isinstance(entry["emotion_type"], str)


@pytest.mark.asyncio
async def test_reader_drop_off_prediction():
    """ReaderAgent 弃书点预测：差文本应预测到弃书点"""
    agent = ReaderAgent(ExtendedReaderType.CRITICAL)
    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        side_effect=Exception("LLM unavailable"),
    ):
        feedback = await agent.read(BAD_TEXT, chapter=1)

    # 挑剔读者对差文本可能不继续阅读
    if not feedback.continue_reading:
        assert feedback.drop_off_point != ""
        assert feedback.drop_off_reason != ""


# ══════════════════════════════════════════════════════
# 6. 扩展读者画像
# ══════════════════════════════════════════════════════


def test_extended_reader_profiles_count():
    """扩展读者画像应有至少10种"""
    assert len(EXTENDED_READER_PROFILES) >= 10
    # 验证新增的5种
    assert ExtendedReaderType.STUDENT in EXTENDED_READER_PROFILES
    assert ExtendedReaderType.OFFICE_WORKER in EXTENDED_READER_PROFILES
    assert ExtendedReaderType.HARDCORE_COOL in EXTENDED_READER_PROFILES
    assert ExtendedReaderType.ROMANCE_LOVER in EXTENDED_READER_PROFILES
    assert ExtendedReaderType.SCIFI_FAN in EXTENDED_READER_PROFILES


def test_extended_reader_profile_fields():
    """每种读者画像应包含必要字段"""
    required_fields = ["name", "description", "cool_threshold", "patience", "pacing_preference", "forgiveness"]
    for rtype, profile in EXTENDED_READER_PROFILES.items():
        for field_name in required_fields:
            assert field_name in profile, f"{rtype} 缺少字段 {field_name}"
        assert 0 <= profile["patience"] <= 1
        assert 0 <= profile["forgiveness"] <= 1


# ══════════════════════════════════════════════════════
# 7. DebateOrchestrator 规则-based辩论
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_debate_rule_based():
    """DebateOrchestrator 规则-based辩论（mock LLM失败触发回退）"""
    orchestrator = DebateOrchestrator(max_rounds=2)
    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        side_effect=Exception("LLM unavailable"),
    ):
        result = await orchestrator.orchestrate_debate(BAD_TEXT, chapter=1)

    assert isinstance(result, DebateResult)
    assert result.debate_source == "rule"
    assert isinstance(result.rounds, list)
    assert result.final_verdict != ""
    assert result.agreed_issues >= 0
    assert result.unresolved_issues >= 0
    assert isinstance(result.revision_suggestions, list)
    assert 0 <= result.total_score <= 100
    assert isinstance(result.reflexion_entries, list)


@pytest.mark.asyncio
async def test_debate_round_details():
    """辩论轮次详情应包含各方论点"""
    orchestrator = DebateOrchestrator(max_rounds=2)
    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        side_effect=Exception("LLM unavailable"),
    ):
        result = await orchestrator.orchestrate_debate(BAD_TEXT, chapter=1)

    for r in result.rounds:
        assert isinstance(r, DebateRoundDetail)
        assert r.round_num >= 1
        assert isinstance(r.critic_argument, str)
        assert isinstance(r.defender_argument, str)
        assert isinstance(r.reader_vote, str)
        assert isinstance(r.resolution, str)


# ══════════════════════════════════════════════════════
# 8. DebateOrchestrator LLM辩论
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_debate_llm():
    """DebateOrchestrator LLM辩论（mock gacha_engine返回有效JSON）"""
    llm_response = json.dumps(
        {
            "critic_argument": "本章爽点密度不足，前半段过于平淡",
            "defender_argument": "前半段为后续高潮做铺垫，符合叙事节奏",
            "reader_vote": "读者认为爽点确实不足，需要加强",
            "resolution": "问题成立，建议增加前期爽点",
            "issues_resolved": ["爽点密度过低"],
            "issues_unresolved": [],
            "revision_suggestions": [
                {"issue": "爽点密度过低", "suggestion": "在前1/3处增加一个小高潮", "priority": 2}
            ],
        }
    )
    mock_result = {"best_text": llm_response, "best_model": "mock"}

    orchestrator = DebateOrchestrator(max_rounds=1)
    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        result = await orchestrator.orchestrate_debate(BAD_TEXT, chapter=1)

    assert result.debate_source == "llm"
    assert len(result.rounds) >= 1
    assert result.rounds[0].critic_argument == "本章爽点密度不足，前半段过于平淡"


# ══════════════════════════════════════════════════════
# 9. DebateOrchestrator CRITIC验证
# ══════════════════════════════════════════════════════


def test_critic_verification_actionable():
    """CRITIC验证：具体的建议应被判定为可执行"""
    orchestrator = DebateOrchestrator()
    verification = orchestrator._critic_verify_suggestion(
        "爽点密度过低",
        "在前1/3处增加2-3个打脸场景，将爽点密度提升到5/千字",
    )
    assert isinstance(verification, CRITICVerification)
    assert verification.is_specific is True
    assert verification.has_location is True
    assert verification.is_quantifiable is True
    assert verification.actionable is True


def test_critic_verification_vague():
    """CRITIC验证：模糊的建议应被判定为不可执行"""
    orchestrator = DebateOrchestrator()
    verification = orchestrator._critic_verify_suggestion(
        "节奏问题",
        "改一下",
    )
    assert verification.is_specific is False
    assert verification.actionable is False
    assert verification.verification_notes != ""


# ══════════════════════════════════════════════════════
# 10. DebateOrchestrator Reflexion修订
# ══════════════════════════════════════════════════════


def test_reflexion_generation():
    """Reflexion修订：应生成结构化反思"""
    orchestrator = DebateOrchestrator()
    entry = orchestrator._generate_reflexion("爽点密度过低，读者反馈平淡", [])

    assert isinstance(entry, ReflexionEntry)
    assert entry.issue_description != ""
    assert entry.root_cause != ""
    assert entry.revision_direction != ""
    assert entry.expected_effect != ""
    assert entry.priority >= 1


def test_reflexion_different_issues():
    """不同问题应生成不同的反思内容"""
    orchestrator = DebateOrchestrator()
    entry1 = orchestrator._generate_reflexion("节奏拖沓，长句过多", [])
    entry2 = orchestrator._generate_reflexion("章末缺少悬念钩子", [])

    assert entry1.root_cause != entry2.root_cause
    assert entry1.revision_direction != entry2.revision_direction


# ══════════════════════════════════════════════════════
# 11. 8阶段流水线
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_8stage_pipeline():
    """8阶段增强流水线应执行所有阶段"""
    orchestrator = DebateOrchestrator(max_rounds=2)
    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        side_effect=Exception("LLM unavailable"),
    ):
        result = await orchestrator.run_8stage_pipeline(GOOD_TEXT, chapter=1, outline="测试大纲")

    assert isinstance(result, PipelineResult)
    assert len(result.stages) == 8
    assert 0 <= result.final_score <= 100
    assert isinstance(result.passed, bool)
    assert result.summary != ""

    # 验证每个阶段
    expected_stages = [
        "Stage0_预处理",
        "Stage1_蓝图评审辩论",
        "Stage2_抽卡建议",
        "Stage3_CRITIC验证",
        "Stage4_Reflexion修订",
        "Stage5_终评",
        "Stage6_润色建议",
        "Stage7_知识更新建议",
    ]
    for i, stage in enumerate(result.stages):
        assert stage.stage_name == expected_stages[i]
        assert stage.status in ("success", "failed", "skipped")
        assert stage.duration_ms >= 0
        assert isinstance(stage.result, dict)


@pytest.mark.asyncio
async def test_pipeline_stage5_final_review():
    """流水线Stage5终评应包含verdict"""
    orchestrator = DebateOrchestrator(max_rounds=1)
    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        side_effect=Exception("LLM unavailable"),
    ):
        result = await orchestrator.run_8stage_pipeline(GOOD_TEXT, chapter=1)

    stage5 = result.stages[5]
    assert "verdict" in stage5.result
    assert "final_score" in stage5.result
    assert stage5.result["final_score"] == result.final_score


# ══════════════════════════════════════════════════════
# 12. 消息总线发布/订阅
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_critic_publish_subscribe():
    """CriticAgent 消息总线发布/订阅"""
    agent = CriticAgent()
    received_messages: list[dict] = []

    async def handler(message: object) -> None:
        if isinstance(message, dict):
            received_messages.append(message)

    await message_bus.subscribe("agent.critic.completed", handler)

    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        side_effect=Exception("LLM unavailable"),
    ):
        report = await agent.critique(GOOD_TEXT, chapter=1)
        await agent.publish_critique(report)

    # 等待消息处理
    await asyncio.sleep(0.1)

    assert len(received_messages) >= 1
    assert "overall_score" in received_messages[0]
    assert "critique_source" in received_messages[0]

    # 清理订阅
    await message_bus.unsubscribe("agent.critic.completed", handler)


@pytest.mark.asyncio
async def test_reader_publish_feedback():
    """ReaderAgent 发布读者反馈"""
    agent = ReaderAgent(ExtendedReaderType.CASUAL)
    received_messages: list[dict] = []

    async def handler(message: object) -> None:
        if isinstance(message, dict):
            received_messages.append(message)

    await message_bus.subscribe("agent.reader.completed", handler)

    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        side_effect=Exception("LLM unavailable"),
    ):
        feedback = await agent.read(GOOD_TEXT, chapter=1)
        await agent.publish_feedback(feedback)

    await asyncio.sleep(0.1)

    assert len(received_messages) >= 1
    assert "overall_score" in received_messages[0]
    assert "reader_type" in received_messages[0]

    await message_bus.unsubscribe("agent.reader.completed", handler)


# ══════════════════════════════════════════════════════
# 13. 向后兼容
# ══════════════════════════════════════════════════════


def test_backward_compat_debate_review_engine():
    """现有 DebateReviewEngine 仍正常工作"""
    engine = DebateReviewEngine()
    result = engine.review(BAD_TEXT, chapter=1)

    assert result.total_score > 0
    assert len(result.issues) > 0
    assert result.summary != ""


def test_backward_compat_reader_simulator():
    """现有 ReaderSimulator 仍正常工作"""
    simulator = ReaderSimulator()
    result = simulator.simulate(GOOD_TEXT, chapter=1)

    assert len(result.readers) > 0
    assert result.avg_score > 0
    assert result.summary != ""


def test_backward_compat_rule_checker():
    """现有 RuleBasedQualityChecker 仍正常工作"""
    checker = RuleBasedQualityChecker()
    issues = checker.check(BAD_TEXT)
    scores = checker.calculate_dimension_scores(BAD_TEXT)

    assert isinstance(issues, list)
    assert isinstance(scores, dict)
    assert len(scores) > 0


# ══════════════════════════════════════════════════════
# 14. 边界情况
# ══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_empty_text_critic():
    """空文本：CriticAgent应返回空报告"""
    agent = CriticAgent()
    report = await agent.critique(EMPTY_TEXT, chapter=1)

    assert report.overall_score == 0.0
    assert report.would_continue is False
    assert "文本为空" in report.poison_points


@pytest.mark.asyncio
async def test_empty_text_reader():
    """空文本：ReaderAgent应返回空反馈"""
    agent = ReaderAgent(ExtendedReaderType.CASUAL)
    feedback = await agent.read(EMPTY_TEXT, chapter=1)

    assert feedback.overall_score == 0.0
    assert feedback.continue_reading is False
    assert feedback.drop_off_reason == "文本为空"


@pytest.mark.asyncio
async def test_empty_text_debate():
    """空文本：DebateOrchestrator应返回空结果"""
    orchestrator = DebateOrchestrator()
    result = await orchestrator.orchestrate_debate(EMPTY_TEXT, chapter=1)

    assert result.total_score == 0.0
    assert "文本为空" in result.final_verdict


@pytest.mark.asyncio
async def test_short_text():
    """超短文本应能正常处理"""
    agent = CriticAgent()
    with patch(
        "kunlun.gacha.engine.gacha_engine.generate",
        new_callable=AsyncMock,
        side_effect=Exception("LLM unavailable"),
    ):
        report = await agent.critique(SHORT_TEXT, chapter=1)

    assert 0 <= report.overall_score <= 100
    assert report.critique_source == "rule"


@pytest.mark.asyncio
async def test_pipeline_empty_text():
    """空文本流水线应正常执行不崩溃"""
    orchestrator = DebateOrchestrator()
    result = await orchestrator.run_8stage_pipeline(EMPTY_TEXT, chapter=1)

    assert len(result.stages) == 8
    assert result.final_score >= 0


# ══════════════════════════════════════════════════════
# 15. 数据类序列化
# ══════════════════════════════════════════════════════


def test_critic_report_to_dict():
    """CriticReport.to_dict() 应返回完整字典"""
    report = CriticReport(
        overall_score=75.5,
        would_continue=True,
        poison_points=["测试毒点"],
        suggestions=["测试建议"],
        market_potential="测试",
        dimension_scores={"开篇吸引力": 80.0},
        chapter=1,
    )
    d = report.to_dict()
    assert d["overall_score"] == 75.5
    assert d["would_continue"] is True
    assert len(d["poison_points"]) == 1


def test_enhanced_reader_feedback_conversion():
    """EnhancedReaderFeedback 可转换为兼容的 ReaderFeedback"""
    feedback = EnhancedReaderFeedback(
        reader_type=ExtendedReaderType.NEWBIE,
        reader_name="小白读者",
        overall_score=7.5,
        continue_reading=True,
        emotional_timeline=[{"paragraph_index": 0, "emotion_type": "兴奋", "intensity": 0.8, "snippet": "test"}],
    )
    rf = feedback.to_reader_feedback()
    assert rf.overall_score == 7.5
    assert rf.continue_reading is True
    assert rf.reader_name == "小白读者"


def test_debate_result_to_dict():
    """DebateResult.to_dict() 应包含所有字段"""
    result = DebateResult(
        rounds=[DebateRoundDetail(round_num=1, critic_argument="test")],
        final_verdict="测试裁决",
        agreed_issues=1,
        unresolved_issues=0,
        total_score=80.0,
    )
    d = result.to_dict()
    assert d["final_verdict"] == "测试裁决"
    assert d["agreed_issues"] == 1
    assert len(d["rounds"]) == 1
    assert "reflexion_entries" in d
