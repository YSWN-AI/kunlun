"""上下文Token预算分配器测试"""

import pytest

pytestmark = pytest.mark.unit

from kunlun.context.budget import (
    DEFAULT_BUDGET_ALLOCATION,
    ContextBudgetAllocator,
    create_context_budget,
    log_distance_decay,
    sliding_window_weight,
)


class TestDistanceDecay:
    def test_current_chapter(self):
        assert log_distance_decay(0) == 1.0

    def test_near_chapter(self):
        d = log_distance_decay(1)
        assert 0.5 < d < 1.0, f"距离1章衰减应为0.59左右: {d}"

    def test_far_chapter(self):
        d = log_distance_decay(50)
        assert 0.15 < d < 0.3, f"距离50章衰减应趋近0.2: {d}"

    def test_monotonic(self):
        vals = [log_distance_decay(i) for i in range(0, 20)]
        for i in range(len(vals) - 1):
            assert vals[i] >= vals[i + 1], f"非单调递减在 {i}: {vals[i]} < {vals[i + 1]}"


class TestSlidingWindow:
    def test_current(self):
        assert sliding_window_weight(5, 5, 100) == 1.0

    def test_near(self):
        assert sliding_window_weight(3, 5, 100) == 0.8

    def test_far(self):
        w = sliding_window_weight(1, 50, 100)
        assert 0 < w < 0.5

    def test_beyond_20(self):
        w = sliding_window_weight(1, 30, 100)
        assert w < 0.4


class TestBudgetAllocator:
    def test_default_allocation(self):
        allocator = ContextBudgetAllocator(total_budget=8000)
        total_pct = sum(DEFAULT_BUDGET_ALLOCATION.values())
        assert abs(total_pct - 1.0) < 0.01  # 所有段分配总和应等于1.0
        assert allocator._input_budget > 0
        assert allocator._reserve_budget > 0

    def test_segment_budget(self):
        allocator = ContextBudgetAllocator(total_budget=10000)
        sys_budget = allocator.get_segment_budget("system_rules")
        assert 0 < sys_budget < 2000

    def test_truncate_short_text(self):
        allocator = ContextBudgetAllocator(total_budget=8000)
        text = "短文本"
        result = allocator.truncate_to_budget(text, 1000)
        assert result == text

    def test_truncate_long_text(self):
        allocator = ContextBudgetAllocator(total_budget=8000)
        text = "第一章内容。" * 500
        result = allocator.truncate_to_budget(text, 500)
        # 中文 1 token ≈ 1.5 字符，500 tokens ≈ 750 字符（含标点后约 820）
        assert len(result) <= 850

    def test_truncate_with_distance(self):
        allocator = ContextBudgetAllocator(total_budget=8000, current_chapter=50)
        text = "第一章内容。" * 500
        # 距离当前章距离30 → 衰减到0.2左右
        result = allocator.truncate_to_budget(text, 2000, chapter_distance=30)
        assert len(result) < 2000

    def test_assemble_empty(self):
        allocator = ContextBudgetAllocator(total_budget=8000)
        result = allocator.assemble({})
        assert result == {}

    def test_assemble_full(self):
        allocator = ContextBudgetAllocator(total_budget=8000, current_chapter=10)
        segments = {
            "system_rules": "规则说明。" * 100,
            "character_cards": "角色卡内容。" * 200,
            "chapter_summaries": "摘要内容。" * 300,
            "current_blueprint": "蓝图内容。" * 50,
        }
        result = allocator.assemble(segments)
        assert "system_rules" in result
        assert "character_cards" in result
        assert len(result["system_rules"]) > 0

    def test_create_context_budget_shortcut(self):
        result = create_context_budget(
            total_budget=5000,
            current_chapter=1,
            system_rules="系统规则",
            character_cards="角色卡",
        )
        assert isinstance(result, dict)
        assert "system_rules" in result
        assert "character_cards" in result
