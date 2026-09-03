"""
昆仑创作引擎 — 多Agent辩论式创作深化模块测试

覆盖:
  - DebateStore: 保存/加载/查询/更新/历史/统计/归档/序列化
  - DebatePipelineIntegration: 触发判断/共识度/自适应终止/决议/优先级/集成
  - DebateStage: 初始化/执行(mock)/上下文写入
  - PipelineRunner: 注册辩论阶段/启用禁用
  - 集成测试: 完整辩论流程

所有LLM调用用mock替代，全部非慢速测试。
"""

from __future__ import annotations

from typing import Any

import pytest

from kunlun.agents.debate_orchestrator import DebateResult, DebateRoundDetail
from kunlun.agents.debate_pipeline import (
    TRIGGER_BLUEPRINT_REVIEW,
    TRIGGER_CHAPTER_FINAL,
    TRIGGER_QUALITY_GATE,
    DebatePipelineIntegration,
)
from kunlun.agents.debate_store import DebateRecord, DebateStore
from kunlun.pipeline.engine import DebateStage, PipelineRunner

# ══════════════════════════════════════════════════════
# Mock 工具
# ══════════════════════════════════════════════════════


def make_debate_result(
    agreed: int = 3,
    unresolved: int = 1,
    score: float = 75.0,
    suggestions: list[dict[str, Any]] | None = None,
) -> DebateResult:
    """构造预设 DebateResult"""
    if suggestions is None:
        suggestions = [
            {"issue": "节奏拖沓", "suggestion": "拆分长句，增加对话", "priority": 1, "round": 1},
            {"issue": "爽点不足", "suggestion": "在前1/3增加小高潮", "priority": 2, "round": 1},
            {"issue": "人物扁平", "suggestion": "增加内心独白", "priority": 3, "round": 2},
            {"issue": "节奏拖沓", "suggestion": "删除冗余描写", "priority": 1, "round": 2},  # 重复
        ]
    rounds = [
        DebateRoundDetail(
            round_num=1,
            focus_issues=["节奏拖沓", "爽点不足"],
            critic_argument="前半段节奏偏慢",
            defender_argument="需要铺垫世界观",
            reader_vote="读者认同节奏问题",
            resolution="节奏问题成立",
            issues_resolved=["节奏拖沓"],
            issues_unresolved=[],
        ),
        DebateRoundDetail(
            round_num=2,
            focus_issues=["人物扁平"],
            critic_argument="主角动机不清晰",
            defender_argument="后续章节会揭示",
            reader_vote="读者希望更多内心戏",
            resolution="部分成立",
            issues_resolved=[],
            issues_unresolved=["人物扁平"],
        ),
    ]
    return DebateResult(
        rounds=rounds,
        final_verdict="辩论结束：共讨论4个问题，达成共识3个，未解决1个",
        agreed_issues=agreed,
        unresolved_issues=unresolved,
        revision_suggestions=suggestions,
        total_score=score,
        critic_report={"overall_score": score},
        reader_feedback={"overall_score": 7.5},
        debate_source="rule",
        reflexion_entries=[],
    )


class FakeDebateOrchestrator:
    """Mock DebateOrchestrator，返回预设 DebateResult"""

    def __init__(self, result: DebateResult | None = None):
        self._result = result or make_debate_result()
        self.calls: list[dict[str, Any]] = []

    async def orchestrate_debate(
        self, text: str, chapter: int = 0, context: str = ""
    ) -> DebateResult:
        self.calls.append({"text": text, "chapter": chapter, "context": context})
        return self._result


class FakePipelineWithHook:
    """Mock 管线引擎，有 register_hook 方法"""

    def __init__(self):
        self.hooks: dict[str, Any] = {}

    def register_hook(self, name: str, callback: Any) -> None:
        self.hooks[name] = callback


# ══════════════════════════════════════════════════════
# 测试文本（>=100字）
# ══════════════════════════════════════════════════════

SAMPLE_TEXT = (
    "林尘站在昆仑之巅，寒风如刀割般掠过他的面颊。三年前，他被宗门逐出，"
    "如同丧家之犬般流落荒野。那时所有人都以为他会死在妖兽横行的边境，"
    "可他不仅活了下来，还修成了被视为禁忌的九转玄功。如今他回来了，"
    "带着一身深不可测的修为，也带着三年来积攒的满腔恨意。宗门大比之日，"
    "正是他清算旧账之时。远处传来钟鸣，那是召集弟子的信号。林尘嘴角勾起"
    "一抹冷笑，纵身跃下悬崖，身形如电般射向宗门方向。"
)


# ══════════════════════════════════════════════════════
# DebateStore 测试
# ══════════════════════════════════════════════════════


class TestDebateStore:
    """DebateStore 测试"""

    @pytest.fixture
    def store(self, tmp_path):
        return DebateStore(storage_dir=str(tmp_path / "debate_records"))

    def _make_record(
        self,
        book_id: str = "test_book",
        chapter: int = 1,
        debate_type: str = "chapter_final",
        consensus: float = 0.75,
        status: str = "pending",
    ) -> DebateRecord:
        return DebateRecord(
            record_id="",
            book_id=book_id,
            chapter=chapter,
            debate_type=debate_type,
            debate_result=make_debate_result().to_dict(),
            final_decision="有条件通过",
            revision_suggestions=[{"issue": "节奏", "suggestion": "优化", "priority": 1}],
            consensus_score=consensus,
            status=status,
            metadata={"source": "test"},
        )

    def test_save_and_load_record(self, store):
        """测试保存记录后能正确加载"""
        record = self._make_record(chapter=5, debate_type="blueprint_review")
        record_id = store.save_record(record)

        assert record_id
        loaded = store.load_record(record_id)
        assert loaded is not None
        assert loaded.book_id == "test_book"
        assert loaded.chapter == 5
        assert loaded.debate_type == "blueprint_review"
        assert loaded.consensus_score == 0.75
        assert loaded.final_decision == "有条件通过"

    def test_load_nonexistent_returns_none(self, store):
        """加载不存在的记录返回None"""
        assert store.load_record("nonexistent_id_12345") is None

    def test_get_records_filtered(self, store):
        """测试按条件查询记录"""
        store.save_record(
            self._make_record(book_id="book_a", chapter=1, debate_type="chapter_final")
        )
        store.save_record(
            self._make_record(book_id="book_a", chapter=2, debate_type="blueprint_review")
        )
        store.save_record(
            self._make_record(book_id="book_b", chapter=1, debate_type="chapter_final")
        )

        # 按book_id过滤
        book_a_records = store.get_records(book_id="book_a", limit=10)
        assert len(book_a_records) == 2

        # 按chapter过滤
        ch1_records = store.get_records(book_id="book_a", chapter=1, limit=10)
        assert len(ch1_records) == 1
        assert ch1_records[0].chapter == 1

        # 按debate_type过滤
        bp_records = store.get_records(debate_type="blueprint_review", limit=10)
        assert len(bp_records) == 1
        assert bp_records[0].debate_type == "blueprint_review"

        # 按status过滤
        pending_records = store.get_records(status="pending", limit=10)
        assert len(pending_records) == 3

    def test_get_latest_record(self, store):
        """测试获取最新记录"""
        # 保存两条同类型记录（后保存的会覆盖前一条，因为文件名相同）
        r1 = self._make_record(chapter=3, debate_type="chapter_final", consensus=0.5)
        store.save_record(r1)

        latest = store.get_latest_record("test_book", 3, "chapter_final")
        assert latest is not None
        assert latest.consensus_score == 0.5

        # 不存在的返回None
        assert store.get_latest_record("test_book", 99, "chapter_final") is None

    def test_update_decision_and_status(self, store):
        """测试更新决议和状态"""
        record = self._make_record(chapter=7)
        record_id = store.save_record(record)

        # 更新决议
        success = store.update_decision(
            record_id,
            "通过，建议优化后发布",
            revision_suggestions=[{"issue": "新问题", "suggestion": "修复", "priority": 2}],
        )
        assert success is True

        loaded = store.load_record(record_id)
        assert loaded.final_decision == "通过，建议优化后发布"
        assert len(loaded.revision_suggestions) == 1
        assert loaded.status == "resolved"

        # 更新状态
        assert store.update_status(record_id, "archived") is True
        assert store.load_record(record_id).status == "archived"

        # 无效状态
        assert store.update_status(record_id, "invalid_status") is False

        # 不存在的记录
        assert store.update_decision("nonexistent", "test") is False
        assert store.update_status("nonexistent", "resolved") is False

    def test_get_debate_history(self, store):
        """测试获取某章节的辩论历史"""
        store.save_record(self._make_record(chapter=10, debate_type="blueprint_review"))
        store.save_record(self._make_record(chapter=10, debate_type="chapter_final"))
        store.save_record(self._make_record(chapter=11, debate_type="chapter_final"))

        history = store.get_debate_history("test_book", 10)
        assert len(history) == 2
        types = {r.debate_type for r in history}
        assert "blueprint_review" in types
        assert "chapter_final" in types

    def test_get_statistics(self, store):
        """测试统计功能"""
        store.save_record(
            self._make_record(chapter=1, consensus=0.8, debate_type="chapter_final")
        )
        store.save_record(
            self._make_record(chapter=2, consensus=0.6, debate_type="blueprint_review")
        )
        store.save_record(
            self._make_record(chapter=3, consensus=0.9, debate_type="chapter_final")
        )

        stats = store.get_statistics()
        assert stats["total_debates"] == 3
        assert 0.0 <= stats["avg_consensus"] <= 1.0
        assert "decision_distribution" in stats
        assert "type_distribution" in stats
        assert stats["type_distribution"]["chapter_final"] == 2

        # 按book_id过滤
        stats_book = store.get_statistics(book_id="test_book")
        assert stats_book["total_debates"] == 3

        # 空统计
        empty_stats = store.get_statistics(book_id="nonexistent")
        assert empty_stats["total_debates"] == 0
        assert empty_stats["avg_consensus"] == 0.0

    def test_archive_old_records(self, store):
        """测试归档旧章节记录"""
        store.save_record(self._make_record(chapter=1))
        store.save_record(self._make_record(chapter=2))
        store.save_record(self._make_record(chapter=5))

        archived = store.archive_old_records("test_book", before_chapter=3)
        assert archived == 2

        # 归档后章节1和2不在主目录
        assert store.get_latest_record("test_book", 1, "chapter_final") is None
        assert store.get_latest_record("test_book", 2, "chapter_final") is None
        # 章节5仍在
        assert store.get_latest_record("test_book", 5, "chapter_final") is not None

        # 归档文件存在
        from pathlib import Path

        archive_dir = Path(store.storage_dir) / "book_test_book" / "archive"
        assert archive_dir.is_dir()
        archived_files = list(archive_dir.iterdir())
        assert len(archived_files) == 2

    def test_record_serialization_roundtrip(self):
        """测试 DebateRecord to_dict/from_dict 往返序列化"""
        record = self._make_record(chapter=42, debate_type="general", consensus=0.88)
        record.metadata = {"key": "value", "number": 42}

        data = record.to_dict()
        assert isinstance(data, dict)
        assert data["chapter"] == 42
        assert data["debate_type"] == "general"
        assert data["metadata"]["key"] == "value"

        restored = DebateRecord.from_dict(data)
        assert restored.record_id == record.record_id
        assert restored.book_id == record.book_id
        assert restored.chapter == 42
        assert restored.consensus_score == 0.88
        assert restored.metadata["number"] == 42
        assert restored.debate_result["agreed_issues"] == 3


# ══════════════════════════════════════════════════════
# DebatePipelineIntegration 测试
# ══════════════════════════════════════════════════════


class TestDebatePipelineIntegration:
    """DebatePipelineIntegration 测试"""

    @pytest.fixture
    def integration(self):
        return DebatePipelineIntegration(max_rounds=3, consensus_threshold=0.7)

    # ── 触发判断 ────────────────────────────────────────

    def test_trigger_blueprint_review_complex(self, integration):
        """蓝图评审：大纲复杂度高时触发"""
        chapter_data = {"chapter_count": 15, "character_count": 8}
        assert integration.should_trigger_debate(TRIGGER_BLUEPRINT_REVIEW, chapter_data) is True

    def test_trigger_blueprint_review_low_quality(self, integration):
        """蓝图评审：质量分低时触发"""
        chapter_data = {"chapter_count": 5, "character_count": 3}
        assert integration.should_trigger_debate(
            TRIGGER_BLUEPRINT_REVIEW, chapter_data, quality_score=60
        ) is True

    def test_no_trigger_blueprint_review(self, integration):
        """蓝图评审：简单大纲且质量合格时不触发"""
        chapter_data = {"chapter_count": 5, "character_count": 3}
        assert integration.should_trigger_debate(
            TRIGGER_BLUEPRINT_REVIEW, chapter_data, quality_score=85
        ) is False

    def test_trigger_chapter_final_low_quality(self, integration):
        """章节终评：质量分低时触发"""
        chapter_data: dict[str, Any] = {"issues": []}
        assert integration.should_trigger_debate(
            TRIGGER_CHAPTER_FINAL, chapter_data, quality_score=70
        ) is True

    def test_trigger_chapter_final_severe_issue(self, integration):
        """章节终评：检测到严重问题时触发"""
        chapter_data = {
            "issues": [
                {"description": "存在逻辑硬伤，时间线矛盾", "severity": 5},
            ]
        }
        assert integration.should_trigger_debate(
            TRIGGER_CHAPTER_FINAL, chapter_data, quality_score=90
        ) is True

    def test_no_trigger_chapter_final(self, integration):
        """章节终评：质量合格且无严重问题时不触发"""
        chapter_data: dict[str, Any] = {"issues": [{"description": " minor issue", "severity": 1}]}
        assert integration.should_trigger_debate(
            TRIGGER_CHAPTER_FINAL, chapter_data, quality_score=85
        ) is False

    def test_trigger_quality_gate_failed(self, integration):
        """质量门禁：审计未通过时触发"""
        chapter_data = {"audit_passed": False, "failed_gates": ["G3", "G5"]}
        assert integration.should_trigger_debate(TRIGGER_QUALITY_GATE, chapter_data) is True

    def test_no_trigger_quality_gate_passed(self, integration):
        """质量门禁：审计通过时不触发"""
        chapter_data = {"audit_passed": True, "gates": {"G1": True, "G2": True}}
        assert integration.should_trigger_debate(TRIGGER_QUALITY_GATE, chapter_data) is False

    def test_invalid_trigger_type(self, integration):
        """无效触发点类型返回False"""
        assert integration.should_trigger_debate("invalid_type", {}) is False

    # ── 共识度计算 ──────────────────────────────────────

    def test_calculate_consensus_normal(self, integration):
        """正常共识度计算"""
        result = make_debate_result(agreed=6, unresolved=2)
        consensus = integration.calculate_consensus(result)
        assert consensus == pytest.approx(0.75, abs=0.01)

    def test_calculate_consensus_no_issues(self, integration):
        """无问题时共识度为1.0"""
        result = make_debate_result(agreed=0, unresolved=0)
        assert integration.calculate_consensus(result) == 1.0

    def test_calculate_consensus_from_dict(self, integration):
        """从字典计算共识度"""
        data = {"agreed_issues": 8, "unresolved_issues": 2}
        assert integration.calculate_consensus(data) == pytest.approx(0.8, abs=0.01)

    # ── 自适应终止 ──────────────────────────────────────

    def test_continue_debate_max_rounds(self, integration):
        """达到最大轮次时终止"""
        results = [make_debate_result(), make_debate_result()]
        assert integration.should_continue_debate(results, current_round=3, max_rounds=3) is False

    def test_continue_debate_consensus_threshold(self, integration):
        """共识度达到阈值时提前终止"""
        high_consensus = make_debate_result(agreed=9, unresolved=1)  # 0.9
        results = [high_consensus]
        assert (
            integration.should_continue_debate(results, current_round=1, max_rounds=3)
            is False
        )

    def test_continue_debate_should_continue(self, integration):
        """未达到终止条件时继续"""
        low_consensus = make_debate_result(agreed=2, unresolved=3)  # 0.4
        results = [low_consensus]
        assert (
            integration.should_continue_debate(results, current_round=1, max_rounds=3)
            is True
        )

    def test_continue_debate_no_new_consensus(self, integration):
        """连续2轮无新共识时终止"""
        no_agreed = make_debate_result(agreed=0, unresolved=3)
        results = [no_agreed, no_agreed]
        assert (
            integration.should_continue_debate(results, current_round=2, max_rounds=5)
            is False
        )

    # ── 最终决议 ────────────────────────────────────────

    def test_generate_final_decision_pass(self, integration):
        """高共识度生成'通过'决议"""
        result = make_debate_result(agreed=9, unresolved=1, score=90.0)
        decision = integration.generate_final_decision(result)
        assert "通过" in decision
        assert "90.0" in decision

    def test_generate_final_decision_conditional(self, integration):
        """中等共识度生成'有条件通过'决议"""
        result = make_debate_result(agreed=6, unresolved=3, score=70.0)  # 0.667
        decision = integration.generate_final_decision(result)
        assert "有条件通过" in decision

    def test_generate_final_decision_reject(self, integration):
        """低共识度生成'不通过'决议"""
        result = make_debate_result(agreed=1, unresolved=4, score=40.0)  # 0.2
        decision = integration.generate_final_decision(result)
        assert "不通过" in decision

    # ── 修订优先级 ──────────────────────────────────────

    def test_get_revision_priority_sorted(self, integration):
        """修订建议按优先级排序并去重"""
        result = make_debate_result()
        priorities = integration.get_revision_priority(result, top_k=5)

        assert len(priorities) <= 5
        # 去重："节奏拖沓"出现两次但只保留一次
        issues = [p["issue"] for p in priorities]
        assert issues.count("节奏拖沓") == 1
        # 按priority排序（数字越小越靠前）
        for i in range(len(priorities) - 1):
            assert priorities[i]["priority"] <= priorities[i + 1]["priority"]

    def test_get_revision_priority_empty(self, integration):
        """空建议列表返回空"""
        result = make_debate_result(suggestions=[])
        assert integration.get_revision_priority(result) == []

    # ── 管线集成 ────────────────────────────────────────

    def test_integrate_with_pipeline_with_hook(self, integration):
        """与有register_hook的管线集成"""
        fake_pipeline = FakePipelineWithHook()
        integration.integrate_with_pipeline(fake_pipeline)

        assert "blueprint_review" in fake_pipeline.hooks
        assert "chapter_final" in fake_pipeline.hooks

    def test_integrate_with_pipeline_without_hook(self, integration):
        """与无register_hook的管线集成不报错"""
        class NoHookPipeline:
            pass

        integration.integrate_with_pipeline(NoHookPipeline())
        # 不报错即通过

    def test_integrate_with_none_pipeline(self, integration):
        """与None管线集成不报错"""
        integration.integrate_with_pipeline(None)


# ══════════════════════════════════════════════════════
# DebateStage 测试
# ══════════════════════════════════════════════════════


class TestDebateStage:
    """DebateStage 测试"""

    def test_debate_stage_init(self):
        """测试 DebateStage 初始化"""
        stage = DebateStage(debate_type="chapter_final")
        assert stage.debate_type == "chapter_final"
        assert stage._integration is None

        stage2 = DebateStage()
        assert stage2.debate_type == "chapter_final"

    async def test_debate_stage_execute_with_mock(self, tmp_path):
        """测试 DebateStage 执行（使用mock orchestrator）"""
        stage = DebateStage(debate_type="chapter_final")

        # 注入带mock的integration
        fake_orch = FakeDebateOrchestrator(result=make_debate_result(agreed=5, unresolved=1))
        store = DebateStore(storage_dir=str(tmp_path / "records"))
        integration = DebatePipelineIntegration(
            debate_orchestrator=fake_orch,
            debate_store=store,
        )
        stage._integration = integration

        context = {
            "text": SAMPLE_TEXT,
            "chapter": 3,
            "outline": "第3章：主角回归宗门",
            "book_id": "test_book",
        }

        result = await stage.execute(context)

        # 验证结果
        assert "triggered" in result
        assert "debate_result" in result
        assert "final_decision" in result

        # 验证context被写入
        assert "debate_result" in context
        assert "debate_final_decision" in context
        assert "debate_triggered" in context

        # 验证orchestrator被调用
        assert len(fake_orch.calls) == 1
        assert fake_orch.calls[0]["chapter"] == 3

    async def test_debate_stage_execute_no_text(self):
        """测试 DebateStage 无文本时跳过"""
        stage = DebateStage(debate_type="chapter_final")
        context = {"text": "", "chapter": 1}
        result = await stage.execute(context)
        assert result["triggered"] is False
        assert "上下文缺少文本" in result["reason"]


# ══════════════════════════════════════════════════════
# PipelineRunner 辩论集成方法测试
# ══════════════════════════════════════════════════════


class TestPipelineRunnerDebate:
    """PipelineRunner 辩论集成方法测试"""

    def test_register_debate_stage(self):
        """测试注册辩论阶段到指定位置"""
        runner = PipelineRunner(book_id="test")
        runner.create_pipeline(
            pipeline_id="pipe1",
            name="测试管线",
            node_defs=[
                {"node_id": "n1", "name": "步骤1"},
                {"node_id": "n2", "name": "步骤2"},
                {"node_id": "n3", "name": "步骤3"},
            ],
        )

        success = runner.register_debate_stage("chapter_final", position=1)
        assert success is True

        state = runner.get_pipeline("pipe1")
        assert state is not None
        # 位置1插入后，节点顺序: n1, debate_chapter_final, n2, n3
        assert state.nodes[1].node_id == "debate_chapter_final"
        assert len(state.nodes) == 4

    def test_register_debate_stage_invalid_type(self):
        """测试注册无效辩论类型"""
        runner = PipelineRunner(book_id="test")
        assert runner.register_debate_stage("invalid_type", position=0) is False

    def test_register_debate_stage_duplicate(self):
        """测试重复注册辩论阶段不重复添加"""
        runner = PipelineRunner(book_id="test")
        runner.create_pipeline(
            pipeline_id="pipe1",
            name="测试管线",
            node_defs=[{"node_id": "n1", "name": "步骤1"}],
        )

        runner.register_debate_stage("blueprint_review", position=0)
        runner.register_debate_stage("blueprint_review", position=0)

        state = runner.get_pipeline("pipe1")
        debate_nodes = [n for n in state.nodes if n.node_id == "debate_blueprint_review"]
        assert len(debate_nodes) == 1

    def test_enable_disable_debate(self):
        """测试启用和禁用辩论"""
        runner = PipelineRunner(book_id="test")
        runner.create_pipeline(
            pipeline_id="pipe1",
            name="测试管线",
            node_defs=[
                {"node_id": "n1", "name": "步骤1"},
                {"node_id": "n2", "name": "步骤2"},
            ],
        )

        # 启用辩论
        runner.enable_debate(blueprint_review=True, chapter_final=True)
        state = runner.get_pipeline("pipe1")
        debate_nodes = [n for n in state.nodes if n.node_id.startswith("debate_")]
        assert len(debate_nodes) == 2

        # 禁用辩论
        runner.disable_debate()
        state = runner.get_pipeline("pipe1")
        debate_nodes = [n for n in state.nodes if n.node_id.startswith("debate_")]
        assert len(debate_nodes) == 0


# ══════════════════════════════════════════════════════
# 集成测试：完整辩论流程
# ══════════════════════════════════════════════════════


class TestFullDebateFlow:
    """完整辩论流程集成测试"""

    async def test_full_debate_flow(self, tmp_path):
        """构造章节文本 → 判断触发 → 触发辩论(mock) → 保存记录 → 查询历史 → 生成决议"""
        # 1. 初始化
        store = DebateStore(storage_dir=str(tmp_path / "debate_records"))
        fake_orch = FakeDebateOrchestrator(
            result=make_debate_result(agreed=7, unresolved=2, score=82.0)
        )
        integration = DebatePipelineIntegration(
            debate_orchestrator=fake_orch,
            debate_store=store,
            max_rounds=3,
            consensus_threshold=0.7,
        )

        # 2. 判断是否触发（质量分低 → 应触发）
        chapter_data: dict[str, Any] = {"issues": [{"description": "节奏拖沓", "severity": 3}]}
        should_trigger = integration.should_trigger_debate(
            TRIGGER_CHAPTER_FINAL, chapter_data, quality_score=75
        )
        assert should_trigger is True

        # 3. 执行辩论
        result = await integration.run_debate_at_stage(
            trigger_type=TRIGGER_CHAPTER_FINAL,
            text=SAMPLE_TEXT,
            chapter=5,
            outline="第5章：宗门大比",
            context="主角林尘回归",
            book_id="integration_book",
        )

        # 4. 验证辩论结果
        assert result["triggered"] is True
        assert "debate_result" in result
        assert "final_decision" in result
        assert result["record_id"] != ""
        assert "consensus_score" in result
        assert "revision_priority" in result

        # 共识度 = 7/(7+2) = 0.778
        assert result["consensus_score"] == pytest.approx(7 / 9, abs=0.01)

        # 5. 查询历史
        history = store.get_debate_history("integration_book", 5)
        assert len(history) == 1
        assert history[0].debate_type == "chapter_final"
        assert history[0].consensus_score == pytest.approx(7 / 9, abs=0.01)

        # 6. 验证决议内容
        decision = result["final_decision"]
        assert "通过" in decision  # 0.778 >= 0.5 有条件通过或通过
        assert "7" in decision  # 达成共识数

        # 7. 验证修订优先级
        priorities = result["revision_priority"]
        assert len(priorities) > 0
        assert all("issue" in p and "priority" in p for p in priorities)

        # 8. 统计
        stats = store.get_statistics(book_id="integration_book")
        assert stats["total_debates"] == 1
        assert stats["avg_consensus"] == pytest.approx(7 / 9, abs=0.01)

    async def test_skip_debate_flow(self, tmp_path):
        """测试不满足触发条件时跳过辩论"""
        store = DebateStore(storage_dir=str(tmp_path / "debate_records"))
        fake_orch = FakeDebateOrchestrator()
        integration = DebatePipelineIntegration(
            debate_orchestrator=fake_orch,
            debate_store=store,
        )

        # quality_gate: 审计通过 → 不触发
        result = await integration.run_debate_at_stage(
            trigger_type=TRIGGER_QUALITY_GATE,
            text=SAMPLE_TEXT,
            chapter=10,
            book_id="skip_book",
        )

        assert result["triggered"] is False
        assert "reason" in result
        # orchestrator不应被调用
        assert len(fake_orch.calls) == 0
        # 不应有记录
        assert store.get_records(book_id="skip_book", limit=10) == []
