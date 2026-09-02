"""
测试: Audit Gates 8道门禁独立测试
"""

import pytest

pytestmark = pytest.mark.unit

from kunlun.audit.gates import (
    AuditResult,
    GateG1Arc,
    GateG2InfoRelease,
    GateG3AIDetection,
    GateG4PleasureGap,
    GateG5PleasureDiversity,
    GateG6EmotionConsistency,
    GateG7DialogueEffectiveness,
    GateG8BattleRhythm,
    GateLevel,
    GateResult,
    audit_gates,
)


class TestGateResult:
    """门禁结果"""

    def test_gate_result_pass(self):
        result = GateResult(gate_id="G1", level=GateLevel.PASS, score=0.9, detail="测试")
        assert result.gate_id == "G1"
        assert result.level == GateLevel.PASS
        assert result.score == 0.9

    def test_gate_result_fail(self):
        result = GateResult(gate_id="G3", level=GateLevel.FAIL, score=0.3, detail="AI味浓")
        assert result.level == GateLevel.FAIL

    def test_gate_result_warn(self):
        result = GateResult(gate_id="G2", level=GateLevel.WARN, score=0.55, detail="信息较多")
        assert result.level == GateLevel.WARN


class TestAuditResult:
    """审计结果"""

    def test_audit_result_pass(self):
        result = AuditResult(
            passed=True,
            gates={},
            score=0.85,
            summary="通过",
        )
        assert result.passed is True
        assert result.score == 0.85

    def test_audit_result_fail(self):
        result = AuditResult(
            passed=False,
            gates={},
            score=0.35,
            summary="未通过",
        )
        assert result.passed is False


class TestIndividualGates:
    """每道门禁独立测试"""

    def test_g1_arc_gate_basic(self):
        gate = GateG1Arc()
        result = gate.run("测试正文内容。这是网文的一章。", blueprint={})
        assert isinstance(result, GateResult)
        assert result.gate_id == "G1"
        assert 0.0 <= result.score <= 1.0  # 分数在有效范围内
        assert result.level in (GateLevel.PASS, GateLevel.WARN, GateLevel.FAIL)

    def test_g2_info_release_basic(self):
        gate = GateG2InfoRelease()
        result = gate.run("这是一段普通网文正文，信息密度正常。", _blueprint={}, kg_snapshot_id="")
        assert isinstance(result, GateResult)
        assert result.gate_id == "G2"

    def test_g3_ai_detection_human_text(self):
        gate = GateG3AIDetection()
        text = "他蹲下。手摸到门把。冰凉的。推开门，走廊尽头有光。"
        result = gate.run(text)
        assert isinstance(result, GateResult)
        assert result.gate_id == "G3"

    def test_g3_ai_detection_ai_text(self):
        gate = GateG3AIDetection()
        text = "然而，他面临着多重挑战。此外，他需要做出选择。因此，他决定行动。"
        result = gate.run(text)
        assert isinstance(result, GateResult)
        assert result.gate_id == "G3"

    def test_g4_pleasure_gap_basic(self):
        gate = GateG4PleasureGap()
        result = gate.run("正文。段落二。段落三。段落四。段落五。段落六。", kg_snapshot_id="")
        assert isinstance(result, GateResult)
        assert result.gate_id == "G4"

    def test_g5_pleasure_diversity_basic(self):
        gate = GateG5PleasureDiversity()
        result = gate.run("正文包含多种爽点类型。打脸。升级。机缘。")
        assert isinstance(result, GateResult)
        assert result.gate_id == "G5"

    def test_g6_emotion_consistency_basic(self):
        gate = GateG6EmotionConsistency()
        result = gate.run("正文。情绪在这里发生了变化。有起伏也是正常的。")
        assert isinstance(result, GateResult)
        assert result.gate_id == "G6"

    def test_g7_dialog_effectiveness_basic(self):
        gate = GateG7DialogueEffectiveness()
        result = gate.run(
            '"你来这里做什么？"他问。\n\n'
            '"与你无关。"对方冷冷道。\n\n'
            "两人对视，空气中弥漫着紧张的气息。",
        )
        assert isinstance(result, GateResult)
        assert result.gate_id == "G7"

    def test_g8_battle_rhythm_basic(self):
        gate = GateG8BattleRhythm()
        result = gate.run("打斗段落。动作描写。节奏感。")
        assert isinstance(result, GateResult)
        assert result.gate_id == "G8"


class TestAuditGatesFunction:
    """audit_gates 顶层函数"""

    def test_audit_gates_full_run(self):
        """8道门禁全部运行不崩溃"""
        text = (
            "第一章正文。主角推开石门，走入秘境。四周氛围压抑。\n\n"
            '"你终于来了。"声音从阴影中传来。\n\n'
            "主角回头，看到一个老者坐在角落。他走上前去，"
            "发现老者面前摆着棋盘。棋局正到中盘，黑白交错。"
        )
        result = audit_gates(draft=text, blueprint={})
        assert isinstance(result, AuditResult)
        assert len(result.gates) == 8
        for gate_id in ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"]:
            assert gate_id in result.gates
        assert 0 <= result.score <= 1

    def test_audit_gates_empty_text(self):
        """空文本不崩溃"""
        result = audit_gates(draft="", blueprint={})
        assert isinstance(result, AuditResult)
        assert len(result.gates) == 8
        assert 0 <= result.score <= 1

    def test_audit_gates_scores_in_range(self):
        """所有门禁分数在合理范围"""
        text = "一段中等长度的网文正文。" * 20
        result = audit_gates(draft=text, blueprint={})
        for gate_result in result.gates.values():
            assert 0 <= gate_result.score <= 1

    def test_audit_gates_weighted_total(self):
        """加权总分计算"""
        text = "高质量正文。" * 30
        result = audit_gates(draft=text, blueprint={})
        assert 0 <= result.score <= 1
