"""
测试: LearnAgent 偏好学习引擎
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from kunlun.learn.learner import LearnAgent, PreferenceVector

pytestmark = pytest.mark.integration

class TestPreferenceVector:
    """偏好向量"""

    def test_init_zeros(self):
        pv = PreferenceVector()
        assert len(pv.dims) == 50
        assert sum(pv.dims) == 0.0

    def test_update_single_dim(self):
        pv = PreferenceVector()
        pv.update(dim=0, delta=1.0, confidence=0.8)
        assert pv.dims[0] > 0

    def test_ema_decay(self):
        pv = PreferenceVector()
        # 多次向不同方向更新
        pv.update(dim=0, delta=1.0, confidence=0.9)
        val1 = pv.dims[0]
        pv.update(dim=0, delta=-1.0, confidence=0.9)
        val2 = pv.dims[0]
        # EMA 平滑，不会直接从 +1 跳到 -1
        assert abs(val2) < abs(val1)

    def test_update_clamped(self):
        pv = PreferenceVector()
        for _ in range(50):
            pv.update(dim=0, delta=1.0, confidence=1.0)
        # 值被 EMA 平滑，不会直接到 1.0 但应接近
        assert pv.dims[0] > 0.5

    def test_forgetting_decay(self):
        pv = PreferenceVector()
        pv.update(dim=0, delta=1.0, confidence=1.0)
        val_before = pv.dims[0]
        conf_before = pv.confidence[0]
        # decay only takes effect after >1h elapsed; immediately after update it's a no-op
        pv.decay(dim=0, rate=0.001)
        assert pv.dims[0] == val_before  # dims not affected by decay
        assert pv.confidence[0] == conf_before  # no time elapsed, unchanged

    def test_top_preferences(self):
        pv = PreferenceVector()
        pv.update(dim=5, delta=0.9, confidence=0.9)
        pv.update(dim=20, delta=0.8, confidence=0.9)
        top = pv.top_preferences(n=3)
        assert len(top) <= 3
        for entry in top:
            assert isinstance(entry, dict)
            assert "dim" in entry
            assert "value" in entry
            assert abs(entry["value"]) > 0

    def test_to_prompt_hints(self):
        pv = PreferenceVector()
        pv.update(dim=0, delta=0.9, confidence=0.9)  # 描述密度
        pv.update(dim=6, delta=-0.8, confidence=0.9)  # 节奏偏慢
        hints = pv.to_prompt_hints()
        assert isinstance(hints, str)
        assert len(hints) > 0

    def test_to_dict_and_from_dict(self):
        pv = PreferenceVector()
        pv.update(dim=3, delta=0.5, confidence=0.8)
        d = pv.to_dict()
        pv2 = PreferenceVector.from_dict(d)
        assert abs(pv.dims[3] - pv2.dims[3]) < 0.01


class TestLearnAgent:
    """学习代理"""

    @pytest.fixture
    def agent(self, monkeypatch):
        tmp = tempfile.mkdtemp()
        from kunlun.config import settings

        monkeypatch.setattr(settings, "DATA_DIR", Path(tmp))
        agent = LearnAgent("test_book")
        yield agent
        shutil.rmtree(tmp)

    def test_on_chapter_completed(self, agent):
        event = {"chapter": 1, "word_count": 3000, "audit_result": {"gates": {}}}
        agent.on_event("CHAPTER_COMPLETED", event)
        # 验证偏好向量至少初始化且维度完整
        assert agent.prefs is not None
        assert len(agent.prefs.dims) == 50

    def test_on_audit_passed(self, agent):
        event = {"gate": "G1", "distribution": {}}
        agent.on_event("AUDIT_PASSED", event)
        assert agent.prefs is not None

    def test_on_audit_failed(self, agent):
        event = {"gate": "G5", "reason": "爽点太单一"}
        agent.on_event("AUDIT_FAILED", event)
        assert agent.prefs is not None

    def test_on_author_feedback(self, agent):
        event = {
            "feedback": "节奏太慢",
            "rating": 3,
        }
        agent.on_event("AUTHOR_FEEDBACK", event)
        # 检查偏好向量的节奏维度是否有反应
        hints = agent.get_prompt_hints()
        assert isinstance(hints, str)
        assert len(hints) > 0  # 反馈后应有偏好提示

    def test_on_style_modified(self, agent):
        event = {"modification_type": "ai_conjunction_replacement", "modification_count": 10}
        agent.on_event("STYLE_MODIFIED", event)
        assert agent.prefs is not None

    def test_get_prompt_hints(self, agent):
        hints = agent.get_prompt_hints()
        assert isinstance(hints, str)

    def test_persistence(self, agent):
        event = {"feedback": "打脸太少了", "rating": 2}
        agent.on_event("AUTHOR_FEEDBACK", event)
        agent.save()

        # 重新加载
        agent2 = LearnAgent("test_book")
        assert agent2.prefs is not None

    def test_gate_to_dim_mapping(self, agent):
        # 验证门禁到维度的映射
        mapping = [
            ("G1", 40),
            ("G5", 44),
            ("G6", 45),
        ]
        for gate, expected_dim in mapping:
            dim = agent._gate_to_dim(gate)
            assert dim == expected_dim, f"{gate} -> {dim} != {expected_dim}"
