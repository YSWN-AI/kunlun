"""
G3: AI味检测/AI痕迹

24+维 AI 特征库扫描 + 段落CV + 连词密度检测。
"""

from __future__ import annotations

import re

from kunlun.audit.gates._base import GateLevel, GateResult


class GateG3AIDetection:
    """G3: AI味检测 — 24+ 维 AI 特征库检测（Humanizer + Prosetheus + InkOS）"""

    AI_CONJUNCTIONS = [
        "然而，",
        "此外，",
        "因此，",
        "与此同时，",
        "值得注意的是，",
        "实际上，",
        "换句话说，",
        "综上所述，",
        "总而言之，",
    ]

    def run(self, draft: str) -> GateResult:
        sentences = re.split(r"[。！？!?]", draft)
        paragraphs = [p for p in draft.split("\n\n") if len(p.strip()) > 20]

        if len(sentences) < 3 or len(paragraphs) < 2:
            return GateResult(
                gate_id="G3", level=GateLevel.PASS, score=0.8, detail="文本过短，跳过AI味检测"
            )

        from kunlun.audit.ai_features import calculate_ai_score, scan_text

        feature_hits = scan_text(draft)
        ai_score = calculate_ai_score(draft)

        high_severity_hits = [h for h in feature_hits if h["severity"] >= 0.6 and h["score"] > 0.5]
        medium_hits = [h for h in feature_hits if h["severity"] >= 0.4 and h["score"] > 0.5]

        para_lens = [len(p) for p in paragraphs]
        avg_len = sum(para_lens) / max(len(para_lens), 1)
        if avg_len > 0:
            variance = sum((v - avg_len) ** 2 for v in para_lens) / len(para_lens)
            para_cv = (variance**0.5) / avg_len
        else:
            para_cv = 1.0
        cv_score = min(1.0, para_cv / 0.3) if para_cv < 0.3 else 1.0

        avg_score = (ai_score + cv_score) / 2

        issues = []
        if cv_score < 0.6:
            issues.append("段落长度过于均匀")
        issues.extend(f"{h['name']}({h['count']}处)" for h in high_severity_hits[:3])
        issues.extend(f"{h['name']}({h['count']}处)" for h in medium_hits[:2])

        if avg_score < 0.5 or len(high_severity_hits) >= 3:
            level = GateLevel.FAIL
        elif avg_score < 0.7 or len(high_severity_hits) >= 1:
            level = GateLevel.WARN
        else:
            level = GateLevel.PASS

        detail_parts = [f"AI特征得分: {ai_score:.2f}"]
        if issues:
            detail_parts.append("触发: " + ", ".join(issues))
        else:
            detail_parts.append("24+特征检测均通过")

        return GateResult(
            gate_id="G3",
            level=level,
            score=round(avg_score, 2),
            detail="; ".join(detail_parts),
            data={
                "ai_score": ai_score,
                "cv_score": cv_score,
                "triggered_features": len(high_severity_hits) + len(medium_hits),
                "high_severity": len(high_severity_hits),
            },
        )
