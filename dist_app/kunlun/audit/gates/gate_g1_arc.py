"""
G1: 英雄之旅弧线位置偏差

检测正文是否处于预期弧线阶段。
"""

from __future__ import annotations

from kunlun.audit.gates._base import GateLevel, GateResult


class GateG1Arc:
    """G1: 英雄之旅弧线位置偏差"""

    HERO_JOURNEY_KEYWORDS = {
        "ordinary_world": ["平凡", "日常", "平静", "普通"],
        "call_to_adventure": ["召唤", "邀请", "信件", "消息", "变故"],
        "refusal_of_call": ["拒绝", "犹豫", "害怕", "退缩"],
        "meeting_mentor": ["导师", "师傅", "前辈", "指点"],
        "crossing_threshold": ["进入", "穿越", "踏入", "边界", "门槛"],
        "tests_allies_enemies": ["考验", "试炼", "盟友", "敌人", "战斗"],
        "approach_inmost_cave": ["深入", "洞穴", "核心", "接近"],
        "ordeal": ["磨难", "死亡", "最低点", "危机"],
        "reward": ["奖励", "宝物", "力量", "领悟"],
        "road_back": ["返回", "归途", "回家", "路上"],
        "resurrection": ["复活", "重生", "蜕变", "觉醒"],
        "return_with_elixir": ["归来", "带回", "分享", "结局"],
    }

    def __init__(self):
        self.stage_order = list(self.HERO_JOURNEY_KEYWORDS.keys())

    def run(self, draft: str, blueprint: dict) -> GateResult:
        expected_stage = blueprint.get("arc_stage", "")
        if not expected_stage:
            return GateResult(
                gate_id="G1",
                level=GateLevel.PASS,
                score=0.8,
                detail="蓝图未指定弧线阶段，跳过检测",
            )

        detected_stage = self._detect_stage(draft)
        if not detected_stage:
            return GateResult(
                gate_id="G1",
                level=GateLevel.WARN,
                score=0.6,
                detail="未检测到明显的英雄之旅阶段关键词",
            )

        expected_idx = (
            self.stage_order.index(expected_stage) if expected_stage in self.stage_order else -1
        )
        detected_idx = (
            self.stage_order.index(detected_stage) if detected_stage in self.stage_order else -1
        )
        if expected_idx == -1 or detected_idx == -1:
            return GateResult(
                gate_id="G1",
                level=GateLevel.WARN,
                score=0.7,
                detail=f"阶段识别异常: 预期={expected_stage}, 检测={detected_stage}",
            )

        deviation = abs(expected_idx - detected_idx)

        if deviation <= 1:
            level = GateLevel.PASS
            score = 0.9 - deviation * 0.1
        elif deviation <= 2:
            level = GateLevel.WARN
            score = 0.7
        else:
            level = GateLevel.FAIL
            score = 0.4

        return GateResult(
            gate_id="G1",
            level=level,
            score=score,
            detail=f"预期阶段: {expected_stage}, 检测阶段: {detected_stage}, 偏差阶数: {deviation}",
            data={"expected": expected_stage, "detected": detected_stage, "deviation": deviation},
        )

    def _detect_stage(self, draft: str) -> str | None:
        draft_lower = draft.lower()
        stage_scores = {}

        for stage, keywords in self.HERO_JOURNEY_KEYWORDS.items():
            score = 0
            for kw in keywords:
                if kw in draft_lower:
                    score += 1
            if score > 0:
                stage_scores[stage] = score

        if not stage_scores:
            return None

        return max(stage_scores.items(), key=lambda x: x[1])[0]
