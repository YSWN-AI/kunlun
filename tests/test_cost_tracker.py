"""
成本追踪模块标准 pytest 测试
覆盖: CostTracker 核心路径 — 记录/概览/预算状态/模型定价
"""

import pytest

pytestmark = pytest.mark.integration


class TestCostTracker:
    """LLM 成本追踪器"""

    @pytest.fixture
    def tracker(self):
        """隔离实例避免全局状态污染"""
        import tempfile

        from kunlun.cost_tracker import CostTracker

        td = tempfile.mkdtemp()
        return CostTracker(daily_limit=10.0, monthly_limit=100.0, project_limit=20.0, data_dir=td)

    def test_record_single_call(self, tracker):
        tracker.record(
            model="deepseek-chat",
            provider="deepseek",
            agent="writer",
            action="generate",
            book_id="test_book",
            chapter=1,
            input_tokens=500,
            output_tokens=200,
            latency_ms=1200,
        )
        status = tracker.get_budget_status()
        assert status.total_calls == 1
        assert status.daily_used > 0

    def test_record_multiple_models(self, tracker):
        tracker.record(
            "deepseek-chat",
            "deepseek",
            "writer",
            "generate",
            "test_book",
            1,
            300,
            150,
            latency_ms=800,
        )
        tracker.record(
            "gpt-4o", "openai", "editor", "polish", "test_book", 2, 400, 250, latency_ms=2000
        )
        tracker.record(
            "deepseek-chat",
            "deepseek",
            "writer",
            "generate",
            "test_book",
            3,
            200,
            100,
            latency_ms=500,
        )
        status = tracker.get_budget_status()
        assert status.total_calls == 3

    def test_get_summary(self, tracker):
        tracker.record(
            "deepseek-chat",
            "deepseek",
            "writer",
            "generate",
            "test_book",
            1,
            1000,
            500,
            latency_ms=1500,
        )
        summary = tracker.get_summary()
        assert "budget" in summary
        assert "usage" in summary
        assert "daily_cost" in summary
        assert summary["budget"]["tier"] is not None
        assert summary["usage"]["total_calls"] == 1

    def test_get_budget_status(self, tracker):
        status = tracker.get_budget_status()
        assert status.tier is not None
        assert status.daily_used == 0
        assert status.daily_limit > 0
        assert status.total_calls == 0

    def test_empty_start_state(self, tracker):
        """新实例应有零值统计"""
        status = tracker.get_budget_status()
        assert status.total_calls == 0
        assert status.daily_used == 0

    def test_report_generation(self, tracker):
        tracker.record(
            "deepseek-chat",
            "deepseek",
            "writer",
            "generate",
            "test_book",
            1,
            200,
            100,
            latency_ms=500,
        )
        report = tracker.generate_report("daily")
        assert report.total_cost is not None
        assert isinstance(report.by_model, dict)

    def test_model_pricing_known(self):
        """已知模型应有定价"""
        from kunlun.cost_tracker import MODEL_PRICING, CostTracker

        assert "deepseek-chat" in MODEL_PRICING
        assert "gpt-4o" in MODEL_PRICING
        assert "default" in MODEL_PRICING  # 回退定价

        # 未知模型使用默认定价
        cost = CostTracker()._calculate_cost("unknown-model-xyz", 1000, 100)
        # 默认定价: input=1.0, output=4.0 每1M tokens
        # (1000/1000000)*1.0 + (100/1000000)*4.0 = 0.0014...
        assert cost > 0
