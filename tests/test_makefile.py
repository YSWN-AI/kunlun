"""
测试: Makefile 流水线编排
"""

import pytest

from kunlun.agents.makefile import Makefile, PipelineState, PipelineStep

pytestmark = pytest.mark.integration

class TestPipelineState:
    """流水线状态"""

    def test_default_state(self):
        state = PipelineState(book_id="book_001", chapter_number=5, mode="gacha_parallel_3")
        assert state.current_step == PipelineStep.BLUEPRINT
        assert state.revision_count == 0
        assert state.max_revisions == 3
        assert state.mode == "gacha_parallel_3"
        assert state.errors == []

    def test_state_transition(self):
        state = PipelineState(book_id="book_001", chapter_number=3)
        state.current_step = PipelineStep.DRAFT
        assert state.current_step == PipelineStep.DRAFT
        state.current_step = PipelineStep.AUDIT
        assert state.current_step == PipelineStep.AUDIT

    def test_max_revisions_default(self):
        state = PipelineState(book_id="book_001", chapter_number=3)
        assert state.max_revisions == 3

    def test_errors_accumulation(self):
        state = PipelineState(book_id="book_001", chapter_number=3)
        state.errors.append("error_1")
        state.errors.append("error_2")
        assert len(state.errors) == 2
        assert "error_1" in state.errors

    def test_pipeline_id_generation(self):
        state = PipelineState(book_id="book_001", chapter_number=5, pipeline_id="book_001_ch5")
        assert state.pipeline_id == "book_001_ch5"


class TestMakefileExecute:
    """execute 异步路由"""

    @pytest.fixture
    def makefile(self):
        return Makefile()

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self, makefile):
        """未知动作返回错误"""
        result = await makefile.execute({"action": "unknown_action"})
        assert "success" in result
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_execute_generate_chapter_no_kg(self, makefile):
        """generate_chapter 在KG不可用时优雅降级"""
        task = {
            "action": "generate_chapter",
            "book_id": "book_test",
            "chapter_number": 1,
            "mode": "gacha_parallel_3",
        }
        # 不崩溃，返回结果
        result = await makefile.execute(task)
        assert isinstance(result, dict)
        assert "pipeline_id" in result or "error" in result

    @pytest.mark.asyncio
    async def test_execute_publish_no_file(self, makefile):
        """发布空正文不崩溃"""
        result = await makefile._run_publish(
            {
                "book_id": "book_test",
                "chapter": 1,
                "draft": "",
            }
        )
        assert isinstance(result, dict)
        assert result.get("chapter") == 1


class TestMakefileAgentMetadata:
    """Agent元数据"""

    def test_agent_name(self):
        makefile = Makefile()
        assert makefile.agent_name == "makefile"

    def test_capabilities(self):
        makefile = Makefile()
        assert "pipeline_orchestration" in makefile.capabilities
        assert "chapter_generation_flow" in makefile.capabilities
        assert "audit_retry_loop" in makefile.capabilities

    def test_initial_pipelines_empty(self):
        makefile = Makefile()
        assert len(makefile._active_pipelines) == 0


class TestPipelineStepEnum:
    """流水线步骤枚举"""

    def test_all_steps_defined(self):
        expected_steps = {
            "blueprint",
            "draft",
            "audit",
            "revise",
            "polish",
            "user_review",
            "kg_update",
            "publish",
            "done",
            "failed",
        }
        actual_steps = {step.value for step in PipelineStep}
        assert actual_steps == expected_steps
