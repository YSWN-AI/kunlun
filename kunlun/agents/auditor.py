"""
昆仑创作引擎 — Auditor (审计门禁)
职责: 对生成正文执行8道门禁检查

从 v0.2 起，所有门禁实现统一在 audit/gates.py。
Auditor 类为纯委托层：execute() → audit_gates() → 格式化结果。
_history: 私有方法仅保留与 gates.py 兼容的委托桩，供测试调用。
"""

from __future__ import annotations

from loguru import logger

from kunlun.agents.base import AgentMessage, BaseAgent
from kunlun.audit.gates import (
    GateG1Arc,
    GateG2InfoRelease,
    GateG3AIDetection,
    GateG4PleasureGap,
    GateG5PleasureDiversity,
    GateG6EmotionConsistency,
    GateG7DialogueEffectiveness,
    GateG8BattleRhythm,
    audit_gates,
)


class Auditor(BaseAgent):
    """
    审计员 — 纯委托层

    所有门禁逻辑在 audit/gates.py，
    Auditor 负责: execute() 委托 → 格式转换 → 结果汇总。
    """

    agent_name = "auditor"
    capabilities = [
        "arc_audit",
        "info_release_audit",
        "ai_detection_audit",
        "pleasure_gap_audit",
        "pleasure_diversity_audit",
        "emotion_consistency_audit",
        "dialogue_quality_audit",
        "battle_audit",
    ]

    # 保留兼容属性（测试可能引用）
    ARC_KEYWORDS = GateG1Arc.HERO_JOURNEY_KEYWORDS
    HUMAN_BASELINE = {
        "sentence_cv": 0.51,
        "conjunction_per_kchar": 1.5,
        "paragraph_cv": 0.68,
        "opening_diversity": 0.62,
    }
    PLEASURE_KEYWORDS = GateG4PleasureGap.PLEASURE_KEYWORDS
    EMOTION_KEYWORDS = {}

    # ─── 主入口 ──────────────────────────────────────

    async def execute(self, task: dict) -> dict:
        """运行全部8道门禁 (委托给 audit.gates.audit_gates)"""
        draft = task.get("draft", "")
        blueprint = task.get("blueprint", {})
        kg_snapshot_id = task.get("kg_snapshot_id", "")

        audit_result = audit_gates(draft, blueprint, kg_snapshot_id)

        gate_key_map = {
            "G1": "G1_arc",
            "G2": "G2_info",
            "G3": "G3_ai",
            "G4": "G4_gap",
            "G5": "G5_diversity",
            "G6": "G6_emotion",
            "G7": "G7_dialogue",
            "G8": "G8_battle",
        }

        results = {}
        for gate_id, gate_result in audit_result.gates.items():
            old_key = gate_key_map.get(gate_id, gate_id)
            results[old_key] = {
                "level": gate_result.level.value,
                "score": gate_result.score,
                "detail": gate_result.detail,
            }

        fatal_count = sum(1 for r in results.values() if r["level"] == "FAIL")
        warn_count = sum(1 for r in results.values() if r["level"] == "WARN")
        passed = audit_result.passed

        logger.info(
            f"Auditor: {'通过' if passed else '驳回'} (FAIL={fatal_count}, WARN={warn_count})"
        )

        return {
            "success": True,
            "passed": passed,
            "fatal_count": fatal_count,
            "warn_count": warn_count,
            "gates": results,
            "score": audit_result.score,
            "summary": audit_result.summary,
        }

    # ─── 委托桩 (兼容测试) ────────────────────────────

    def _audit_arc(self, draft: str, blueprint: dict) -> dict:
        """G1: 弧线位置 → 委托 GateG1Arc"""
        g1 = GateG1Arc()
        r = g1.run(draft, blueprint)
        return {"level": r.level.value, "score": r.score, "detail": r.detail}

    def _audit_info_release(self, draft: str) -> dict:
        """G2: 信息释放 → 委托 GateG2InfoRelease"""
        g2 = GateG2InfoRelease()
        r = g2.run(draft, {}, "")
        return {"level": r.level.value, "score": r.score, "detail": r.detail}

    def _audit_ai_detection(self, draft: str) -> dict:
        """G3: AI味检测 → 委托 GateG3AIDetection"""
        g3 = GateG3AIDetection()
        r = g3.run(draft)
        return {
            "level": r.level.value,
            "score": r.score,
            "detail": r.detail,
            "metrics": r.data if r.data else {},
        }

    def _audit_pleasure_gap(self, draft: str, _blueprint: dict) -> dict:
        """G4: 爽点间隔 → 委托 GateG4PleasureGap"""
        g4 = GateG4PleasureGap()
        r = g4.run(draft, "")
        return {"level": r.level.value, "score": r.score, "detail": r.detail}

    def _audit_pleasure_diversity(self, draft: str) -> dict:
        """G5: 爽点多样性 → 委托 GateG5PleasureDiversity"""
        g5 = GateG5PleasureDiversity()
        r = g5.run(draft)
        result = {"level": r.level.value, "score": r.score, "detail": r.detail}
        if r.data:
            result["distribution"] = r.data.get("type_counts", {})
        return result

    def _audit_emotion(self, draft: str, _blueprint: dict | None = None) -> dict:
        """G6: 情绪一致性 → 委托 GateG6EmotionConsistency"""
        g6 = GateG6EmotionConsistency()
        r = g6.run(draft)
        result = {"level": r.level.value, "score": r.score, "detail": r.detail}
        if r.data:
            result["emotions"] = {
                "start": r.data.get("front", ""),
                "end": r.data.get("back", ""),
            }
        return result

    def _audit_dialogue(self, draft: str) -> dict:
        """G7: 对话质量 → 委托 GateG7DialogueEffectiveness"""
        g7 = GateG7DialogueEffectiveness()
        r = g7.run(draft)
        return {"level": r.level.value, "score": r.score, "detail": r.detail}

    def _audit_battle(self, draft: str, _blueprint: dict) -> dict:
        """G8: 战斗审计 → 委托 GateG8BattleRhythm"""
        g8 = GateG8BattleRhythm()
        r = g8.run(draft)
        return {"level": r.level.value, "score": r.score, "detail": r.detail}

    # ─── 辅助 ─────────────────────────────────────────

    def _emotion_distance(self, e1: str, e2: str) -> int:
        """情感轮距离（保留以兼容旧测试）"""
        order = ["joy", "trust", "fear", "surprise", "sadness", "disgust", "anger", "anticipation"]
        try:
            i1, i2 = order.index(e1), order.index(e2)
            return min(abs(i1 - i2), len(order) - abs(i1 - i2))
        except ValueError:
            return 3

    def _summarize(self, results: dict, passed: bool) -> str:
        """生成审计总结"""
        fatal_gates = [g for g, r in results.items() if r.get("level") == "FAIL"]
        warn_gates = [g for g, r in results.items() if r.get("level") == "WARN"]
        if passed and not warn_gates:
            return "全部8道门禁通过"
        if passed:
            return f"通过({len(warn_gates)}警告: {', '.join(warn_gates)})"
        return f"驳回({len(fatal_gates)}致命: {', '.join(fatal_gates)})"

    # ─── 消息回调 ─────────────────────────────────────

    async def on_message(self, msg: AgentMessage) -> AgentMessage | None:
        if msg.msg_type == "RUN_AUDIT":
            result = await self.execute(msg.payload)
            return AgentMessage(
                from_agent=self.agent_name,
                to_agent=msg.from_agent,
                msg_type="AUDIT_RESULT",
                payload={"audit_result": result},
                correlation_id=msg.correlation_id,
                kg_snapshot_id=msg.kg_snapshot_id,
            )
        return None
