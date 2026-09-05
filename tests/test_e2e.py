"""
端到端集成测试 (E2E)
验证全链路：Makefile 章节生成 / pipeline_state 流转 / API 端点
所有测试使用 mock LLM（无 API key 时走降级路径），不依赖外部服务。
"""

import pytest
from fastapi.testclient import TestClient

from kunlun.api.main import app

pytestmark = pytest.mark.integration

@pytest.fixture
def client():
    return TestClient(app)


class TestFullGenerateChapterSync:
    """完整单章生成流程（通过 Makefile._run_chapter_pipeline_sync）"""

    @pytest.mark.asyncio
    async def test_full_generate_chapter_sync(self):
        """完整生成一章，验证各阶段产物非空"""
        from kunlun.agents.makefile import Makefile

        makefile = Makefile()
        result = await makefile.execute(
            {
                "action": "generate_chapter_sync",
                "book_id": "e2e_test_book",
                "chapter_number": 1,
                "mode": "single_fix",
            }
        )

        assert isinstance(result, dict)
        # 即使 LLM 不可用，也能通过降级 mock 产出内容
        assert "draft" in result
        assert "blueprint" in result
        assert "steps" in result
        # 至少应包含 snapshot + blueprint + draft + audit + polish + publish
        essential_steps = ["snapshot", "blueprint", "draft", "audit"]
        for step in essential_steps:
            assert step in result["steps"], f"缺少步骤: {step}"

    @pytest.mark.asyncio
    async def test_full_generate_multi_chapter(self):
        """连续生成多章，验证每章产物独立"""
        from kunlun.agents.makefile import Makefile

        makefile = Makefile()
        results = []
        for ch in [1, 2]:
            r = await makefile.execute(
                {
                    "action": "generate_chapter_sync",
                    "book_id": "e2e_test_book_multi",
                    "chapter_number": ch,
                    "mode": "single_fix",
                }
            )
            results.append(r)

        assert len(results) == 2
        for r in results:
            assert "draft" in r
            assert "success" in r


class TestMakefilePipelineState:
    """验证 pipeline_state 在 generate → audit → polish 各阶段正确流转"""

    @pytest.mark.asyncio
    async def test_pipeline_state_flow(self):
        """pipeline_state 通过完整流水线各步骤"""
        from kunlun.agents.makefile import Makefile

        makefile = Makefile()
        result = await makefile.execute(
            {
                "action": "generate_chapter_sync",
                "book_id": "pipeline_state_test",
                "chapter_number": 1,
                "mode": "single_fix",
            }
        )

        # 验证 pipeline_state 经过关键阶段
        steps = result.get("steps", [])
        assert "snapshot" in steps
        assert "blueprint" in steps
        assert "draft" in steps
        assert "audit" in steps
        # polish 和 publish 也应存在
        assert "polish" in steps
        assert "publish" in steps

    @pytest.mark.asyncio
    async def test_pipeline_state_revisions_bounded(self):
        """修订次数不超过 max_revisions (3)"""
        from kunlun.agents.makefile import Makefile

        makefile = Makefile()
        result = await makefile.execute(
            {
                "action": "generate_chapter_sync",
                "book_id": "pipeline_revision_test",
                "chapter_number": 1,
                "mode": "single_fix",
            }
        )

        revisions = result.get("revisions", 0)
        assert revisions <= 3, f"修订次数 {revisions} 超过上限 3"

    @pytest.mark.asyncio
    async def test_pipeline_result_has_all_fields(self):
        """pipeline 返回结果包含所有关键字段"""
        from kunlun.agents.makefile import Makefile

        makefile = Makefile()
        result = await makefile.execute(
            {
                "action": "generate_chapter_sync",
                "book_id": "pipeline_fields_test",
                "chapter_number": 1,
                "mode": "single_fix",
            }
        )

        required_fields = [
            "success",
            "pipeline_id",
            "book_id",
            "chapter",
            "draft",
            "blueprint",
            "audit_passed",
            "revisions",
            "style_changes",
            "steps",
        ]
        for field in required_fields:
            assert field in result, f"缺少字段: {field}"


class TestApiGenerateEndpoint:
    """通过 FastAPI TestClient 调用 /generate 端点"""

    def test_generate_endpoint_returns_200(self, client):
        """调用 /generate 端点返回 HTTP 200"""
        payload = {
            "book_id": "api_e2e_test",
            "chapter": 1,
            "mode": "single_fix",
            "chapter_type": "normal",
        }
        response = client.post(
            "/api/v1/books/api_e2e_test/chapters/1/generate",
            json=payload,
        )
        assert response.status_code == 200, f"期望 200，得到 {response.status_code}"

    def test_generate_endpoint_response_structure(self, client):
        """验证 /generate 端点响应结构"""
        payload = {
            "book_id": "api_e2e_test_2",
            "chapter": 1,
            "mode": "single_fix",
            "chapter_type": "normal",
        }
        response = client.post(
            "/api/v1/books/api_e2e_test_2/chapters/1/generate",
            json=payload,
        )
        data = response.json()
        assert "success" in data
        if data.get("success"):
            assert "draft" in data
            assert "pipeline_id" in data
        else:
            assert "error" in data

    def test_generate_endpoint_with_gacha_mode(self, client):
        """使用 gacha_parallel_3 模式调用"""
        payload = {
            "book_id": "api_e2e_gacha",
            "chapter": 1,
            "mode": "gacha_parallel_3",
            "chapter_type": "normal",
        }
        response = client.post(
            "/api/v1/books/api_e2e_gacha/chapters/1/generate",
            json=payload,
        )
        assert response.status_code == 200

    def test_status_endpoint(self, client):
        """/status 端点可访问"""
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "kg" in data or "data" in data

    def test_health_endpoint(self, client):
        """/health 端点可访问"""
        response = client.get("/health")
        assert response.status_code == 200


class TestMessageBusE2E:
    """验证进程内消息总线可触发 Makefile 的 on_message 回调链"""

    @pytest.mark.asyncio
    async def test_message_bus_publish_subscribe(self):
        """消息总线基本发布/订阅"""
        from kunlun.agents.message_bus import InProcessMessageBus

        # 获取新实例（重置单例）
        bus = InProcessMessageBus()
        received = []

        async def callback(message):
            received.append(message)

        await bus.subscribe("test.topic", callback)
        await bus.publish("test.topic", {"data": "hello"})

        assert len(received) == 1
        assert received[0]["data"] == "hello"

    @pytest.mark.asyncio
    async def test_message_bus_wildcard(self):
        """通配符订阅 agent.*"""
        from kunlun.agents.message_bus import InProcessMessageBus

        bus = InProcessMessageBus()
        received = []

        async def callback(message):
            received.append(message)

        await bus.subscribe("agent.*", callback)
        await bus.publish("agent.architect", {"type": "test"})
        await bus.publish("agent.writer", {"type": "test2"})

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_makefile_on_message_via_bus(self):
        """通过消息总线向 Makefile 发送 BLUEPRINT_READY 消息，验证回调触发"""
        from kunlun.agents.base import AgentMessage
        from kunlun.agents.makefile import Makefile
        from kunlun.agents.message_bus import message_bus

        makefile = Makefile()
        # 触发惰性订阅
        await makefile._ensure_bus_subscribed()

        # 构建 BLUEPRINT_READY 消息
        msg = AgentMessage(
            from_agent="architect",
            to_agent="makefile",
            msg_type="BLUEPRINT_READY",
            payload={"blueprint": {"chapter": 1}},
            correlation_id="book_test_ch1",
        )

        # 通过总线发布
        await message_bus.publish("kunlun.agent.makefile", msg.__dict__)

        # 验证流水线被创建
        state = makefile._active_pipelines.get("book_test_ch1")
        assert state is not None, "Makefile 应创建 pipeline state"
        assert state.blueprint is not None

    @pytest.mark.asyncio
    async def test_agent_post_message_uses_bus_when_no_nats(self):
        """无 NATS 时 post_message 走进程内总线"""
        from kunlun.agents.makefile import Makefile

        # MockNATS 应在无真实 NATS 时自动激活
        from kunlun.common.nats_mock import MockNATS

        received = []

        async def arch_callback(message):
            received.append(message)

        mock_nats = MockNATS()
        await mock_nats.connect()
        await mock_nats.subscribe("kunlun.agent.architect", arch_callback)

        makefile = Makefile(nats_client=mock_nats)
        await makefile.post_message(
            "architect",
            "GENERATE_BLUEPRINT",
            {"book_id": "test", "chapter": 1},
            correlation_id="test_corr",
        )

        assert len(received) == 1
        msg = received[0]
        assert msg["msg_type"] == "GENERATE_BLUEPRINT"
        assert msg["correlation_id"] == "test_corr"
