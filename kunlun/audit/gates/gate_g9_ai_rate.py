"""
G9: 综合AI率检测与人类化改写门禁

基于 kunlun.ai_rate 模块的12维度AI率检测，输出0-100分AI率评分，
支持自动人类化改写。与G3（24+维AI特征检测）互补：
  - G3: 细粒度特征扫描，检测具体AI痕迹
  - G9: 综合AI率评分，对标平台AI检测阈值，支持自动改写

门禁等级:
  - PASS: AI率 <= 35
  - WARN: 35 < AI率 <= 50
  - FAIL: AI率 > 50
"""

from __future__ import annotations

from kunlun.audit.gates._base import GateLevel, GateResult


class GateG9AIRate:
    """G9: 综合AI率检测门禁 — 12维度AI率评分 + 自动人类化改写"""

    PASS_THRESHOLD = 35.0
    WARN_THRESHOLD = 50.0

    def run(self, draft: str, auto_humanize: bool = False, aggressive: float = 0.5) -> GateResult:
        """
        执行G9 AI率检测

        Args:
            draft: 正文草稿
            auto_humanize: 是否自动人类化改写
            aggressive: 改写强度 0.0-1.0

        Returns:
            GateResult 对象
        """
        if not draft or len(draft.strip()) < 100:
            return GateResult(
                gate_id="G9",
                level=GateLevel.PASS,
                score=0.9,
                detail="文本过短，跳过AI率检测",
                data={"ai_rate": 0, "skipped": True},
            )

        from kunlun.ai_rate import detect_ai_rate, humanize_text

        # 检测AI率
        report = detect_ai_rate(draft)
        ai_rate = report.total_score

        # 判定等级
        if ai_rate <= self.PASS_THRESHOLD:
            level = GateLevel.PASS
        elif ai_rate <= self.WARN_THRESHOLD:
            level = GateLevel.WARN
        else:
            level = GateLevel.FAIL

        # 构建详情
        detail_parts = [f"AI率: {ai_rate:.1f}/100"]

        if report.high_risk_hits:
            top_words = ", ".join(w for w, _ in report.high_risk_hits[:5])
            detail_parts.append(f"高危词: {top_words}")

        # 主要AI特征维度
        top_dims = sorted(report.dimensions, key=lambda d: d.score, reverse=True)[:3]
        if top_dims:
            dim_str = ", ".join(f"{d.dimension.value}({d.score:.0f})" for d in top_dims)
            detail_parts.append(f"主要特征: {dim_str}")

        data = {
            "ai_rate": ai_rate,
            "high_risk_count": len(report.high_risk_hits),
            "medium_risk_count": len(report.medium_risk_hits),
            "dimension_scores": {d.dimension.value: round(d.score, 1) for d in report.dimensions},
            "auto_humanized": False,
        }

        # 自动人类化改写
        if auto_humanize and level != GateLevel.PASS:
            humanize_result = humanize_text(draft, aggressive=aggressive)
            new_ai_rate = humanize_result.ai_rate_after
            data["auto_humanized"] = True
            data["ai_rate_before"] = ai_rate
            data["ai_rate_after"] = new_ai_rate
            data["humanized_text"] = humanize_result.modified_text
            data["strategies_used"] = humanize_result.strategies_used
            data["changes_count"] = len(humanize_result.changes)

            # 改写后重新判定
            if new_ai_rate <= self.PASS_THRESHOLD:
                level = GateLevel.PASS
                detail_parts.append(f"改写后: {new_ai_rate:.1f} (通过)")
            elif new_ai_rate <= self.WARN_THRESHOLD:
                level = GateLevel.WARN
                detail_parts.append(f"改写后: {new_ai_rate:.1f} (警告)")
            else:
                detail_parts.append(f"改写后: {new_ai_rate:.1f} (仍不通过)")

        # 分数转换: AI率越低，分数越高
        score = max(0.0, min(1.0, 1.0 - ai_rate / 100.0))

        return GateResult(
            gate_id="G9",
            level=level,
            score=round(score, 3),
            detail="; ".join(detail_parts),
            data=data,
        )
