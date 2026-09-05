"""
审计门禁模块 — 9道门禁

G1: 英雄之旅弧线位置偏差
G2: 信息释放节奏
G3: AI味检测（24+维特征扫描）
G4: 爽点间隔检测
G5: 爽点类型多样性
G6: 情绪一致性
G7: 对话有效性
G8: 战斗场景节奏
G9: 综合AI率检测（12维度评分 + 自动人类化改写）

使用方式:
  from kunlun.audit.gates import audit_gates, AuditResult
  result = audit_gates(draft="...", blueprint={}, kg_snapshot_id="...")
"""

from __future__ import annotations

from kunlun.audit.gates._base import AuditResult, GateLevel, GateResult
from kunlun.audit.gates.gate_g1_arc import GateG1Arc
from kunlun.audit.gates.gate_g2_info import GateG2InfoRelease
from kunlun.audit.gates.gate_g3_ai import GateG3AIDetection
from kunlun.audit.gates.gate_g4_pleasure_interval import GateG4PleasureGap
from kunlun.audit.gates.gate_g5_pleasure_diversity import GateG5PleasureDiversity
from kunlun.audit.gates.gate_g6_emotion import GateG6EmotionConsistency
from kunlun.audit.gates.gate_g7_dialogue import GateG7DialogueEffectiveness
from kunlun.audit.gates.gate_g8_battle import GateG8BattleRhythm
from kunlun.audit.gates.gate_g9_ai_rate import GateG9AIRate

__all__ = [
    "AUDIT_GATES",
    "GATE_WEIGHTS",
    "AuditResult",
    "GateG1Arc",
    "GateG2InfoRelease",
    "GateG3AIDetection",
    "GateG4PleasureGap",
    "GateG5PleasureDiversity",
    "GateG6EmotionConsistency",
    "GateG7DialogueEffectiveness",
    "GateG8BattleRhythm",
    "GateG9AIRate",
    "GateLevel",
    "GateResult",
    "audit_gates",
]

# ─── 权重配置 ─────────────────────────────────────

GATE_WEIGHTS = {
    "G1": 0.10,
    "G2": 0.15,
    "G3": 0.15,
    "G4": 0.10,
    "G5": 0.10,
    "G6": 0.10,
    "G7": 0.10,
    "G8": 0.10,
    "G9": 0.10,
}

AUDIT_GATES = [
    {"id": "G1", "name": "弧线位置偏差"},
    {"id": "G2", "name": "信息释放节奏"},
    {"id": "G3", "name": "AI味检测"},
    {"id": "G4", "name": "爽点间隔"},
    {"id": "G5", "name": "爽点多样性"},
    {"id": "G6", "name": "情绪一致性"},
    {"id": "G7", "name": "对话有效性"},
    {"id": "G8", "name": "战斗节奏"},
    {"id": "G9", "name": "综合AI率"},
]


# ─── 门禁管理器 ─────────────────────────────────────


def audit_gates(
    draft: str, blueprint: dict, kg_snapshot_id: str = "", auto_humanize_g9: bool = False
) -> AuditResult:
    """
    执行9道门禁审计

    Args:
        draft: 正文草稿
        blueprint: 蓝图字典 (至少包含 chapter, chapter_type, arc_stage)
        kg_snapshot_id: KG快照ID (可选)
        auto_humanize_g9: G9是否自动人类化改写 (默认False)

    Returns:
        AuditResult 对象
    """
    gates = {}

    g1 = GateG1Arc()
    gates["G1"] = g1.run(draft, blueprint)

    g2 = GateG2InfoRelease()
    gates["G2"] = g2.run(draft, blueprint, kg_snapshot_id)

    g3 = GateG3AIDetection()
    gates["G3"] = g3.run(draft)

    g4 = GateG4PleasureGap()
    gates["G4"] = g4.run(draft, kg_snapshot_id)

    g5 = GateG5PleasureDiversity()
    gates["G5"] = g5.run(draft)

    g6 = GateG6EmotionConsistency()
    gates["G6"] = g6.run(draft)

    g7 = GateG7DialogueEffectiveness()
    gates["G7"] = g7.run(draft)

    g8 = GateG8BattleRhythm()
    gates["G8"] = g8.run(draft)

    g9 = GateG9AIRate()
    gates["G9"] = g9.run(draft, auto_humanize=auto_humanize_g9)

    total_score = 0.0
    for gate_id, result in gates.items():
        weight = GATE_WEIGHTS.get(gate_id, 0.1)
        total_score += result.score * weight

    fail_count = sum(1 for r in gates.values() if r.level == GateLevel.FAIL)
    critical_fail = any(
        gate_id in ["G1", "G3", "G9"] and gates[gate_id].level == GateLevel.FAIL
        for gate_id in gates
    )

    passed = (fail_count <= 1) and not critical_fail

    summary_parts = []
    positive_feedback = []
    compliments = {
        "G1": "弧线节奏处理得当，剧情推进自然",
        "G2": "信息释放节奏控制合理，不拖沓不轰炸",
        "G3": "文笔自然流畅，无明显AI痕迹",
        "G4": "爽点间隔恰到好处，阅读体验佳",
        "G5": "爽点类型丰富多样，不单调",
        "G6": "情绪过渡自然，情感线连贯流畅",
        "G7": "对话精炼有效，角色鲜活",
        "G8": "战斗节奏张弛有度，画面感强",
        "G9": "AI率低，人类风格自然，平台检测安全",
    }
    for gate_id in sorted(gates.keys()):
        result = gates[gate_id]
        summary_parts.append(f"{gate_id}:{result.level.value}({result.score:.2f})")
        if result.level == GateLevel.PASS and result.score >= 0.8:
            comp = compliments.get(gate_id)
            if comp:
                positive_feedback.append(comp)

    summary = f"总分: {total_score:.3f} | " + " ".join(summary_parts)
    if positive_feedback:
        summary += "\n✨ " + " | ".join(positive_feedback)

    return AuditResult(
        passed=passed,
        gates=gates,
        score=total_score,
        summary=summary,
    )
