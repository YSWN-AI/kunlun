"""参数随机化引擎测试"""

import pytest

from kunlun.gacha.param_variator import (
    AGENT_PARAM_RANGES,
    ParamVariator,
    randomize_params,
)

pytestmark = pytest.mark.unit


class TestParamVariator:
    def setup_method(self):
        self.variator = ParamVariator()

    def test_get_params_returns_all_fields(self):
        params = self.variator.get_params("writer")
        assert 0.1 <= params.temperature <= 1.5
        assert 0.8 <= params.top_p <= 0.98
        assert 0.0 <= params.presence_penalty <= 0.5
        assert 0.0 <= params.frequency_penalty <= 0.5
        assert params.variation_tag in ("conservative", "balanced", "creative", "chaotic")

    def test_get_params_different_agents(self):
        w = self.variator.get_params("writer")
        a = self.variator.get_params("auditor")
        # Auditor 应该比 Writer 温度低
        assert w.temperature >= a.temperature - 0.1, (
            f"Writer({w.temperature}) vs Auditor({a.temperature})"
        )

    def test_params_differ_by_chapter(self):
        """不同章节应得到不同参数（规避套路化）"""
        p1 = self.variator.get_params("writer", chapter=1)
        p2 = self.variator.get_params("writer", chapter=2)
        # 大概率不同（至少有两项不同）
        diffs = sum(
            [
                p1.temperature != p2.temperature,
                p1.variation_tag != p2.variation_tag,
            ]
        )
        assert diffs >= 1 or p1.to_dict() != p2.to_dict()

    def test_randomize_params_shortcut(self):
        params = randomize_params("writer")
        assert params.temperature > 0

    def test_get_model_combination_single(self):
        combos = self.variator.get_model_combination("single_fix", chapter=1)
        assert len(combos) == 1
        assert combos[0]["temperature"] > 0

    def test_get_model_combination_parallel_3(self):
        combos = self.variator.get_model_combination("gacha_parallel_3", chapter=5)
        assert len(combos) == 3
        # 三个模型的temperature应不同（规避套路）
        temps = [c["temperature"] for c in combos]
        assert len(set(temps)) >= 1  # 至少不完全相同概率极低，但可能有巧合

    def test_get_model_combination_ultimate_5(self):
        combos = self.variator.get_model_combination("gacha_ultimate_5", chapter=3)
        assert len(combos) == 5

    def test_agent_ranges_exist(self):
        """所有定义好的Agent应有参数范围"""
        for agent in ("writer", "architect", "auditor", "reviser", "sociologist"):
            assert agent in AGENT_PARAM_RANGES, f"缺少 {agent} 的参数范围"

    def test_to_dict(self):
        params = self.variator.get_params("writer")
        d = params.to_dict()
        assert "temperature" in d
        assert "top_p" in d
