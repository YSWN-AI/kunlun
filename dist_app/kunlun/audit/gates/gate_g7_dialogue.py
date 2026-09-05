"""
G7: 对话有效性/废话比例

检测对话中废话的比例是否超标。
"""

from __future__ import annotations

import re

from kunlun.audit.gates._base import GateLevel, GateResult
from kunlun.config import settings


class GateG7DialogueEffectiveness:
    """G7: 对话有效性"""

    def run(self, draft: str) -> GateResult:
        dialogue_lines = []
        lines = draft.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('"') or stripped.startswith("「") or stripped.startswith("『"):
                dialogue_lines.append(stripped)

        if not dialogue_lines:
            return GateResult(
                gate_id="G7",
                level=GateLevel.PASS,
                score=0.8,
                detail="无对话内容，跳过检测",
            )

        nonsense_count = 0
        for line in dialogue_lines:
            if self._is_nonsense_dialogue(line):
                nonsense_count += 1

        nonsense_ratio = nonsense_count / len(dialogue_lines) if dialogue_lines else 0
        threshold = settings.audit_dialogue_max_nonsense_pct

        if nonsense_ratio > threshold:
            level = GateLevel.FAIL
            score = 0.3
        elif nonsense_ratio > threshold * 0.7:
            level = GateLevel.WARN
            score = 0.6
        else:
            level = GateLevel.PASS
            score = 0.9 - nonsense_ratio * 2

        detail = f"对话行: {len(dialogue_lines)}, 废话比例: {nonsense_ratio:.1%}"
        return GateResult(
            gate_id="G7",
            level=level,
            score=score,
            detail=detail,
            data={"dialogue_lines": len(dialogue_lines), "nonsense_ratio": nonsense_ratio},
        )

    def _is_nonsense_dialogue(self, line: str) -> bool:
        content = re.sub(r'^["「『]|["」』]$', "", line).strip()

        if len(content) <= 1:
            return True

        exact_waste = {
            "嗯",
            "哦",
            "啊",
            "呃",
            "唔",
            "好吧",
            "好的",
            "行吧",
            "哦哦",
            "嗯嗯",
            "哈哈",
            "呵呵",
            "嘿嘿",
            "哦哦哦",
        }

        if content in exact_waste:
            return True

        partial_waste = {"好吧", "好的", "行吧", "可以", "原来如此", "这样啊", "我知道了"}
        for pattern in partial_waste:
            if content.startswith(pattern):
                rest = content[len(pattern) :].lstrip("，, 。.！!？?；;")
                if rest:
                    return False
                return False

        return bool(len(content) >= 5 and len(set(content)) == 1)
