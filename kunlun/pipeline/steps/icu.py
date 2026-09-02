"""
管线步骤：ICU 重症监护 (Step 4.5)

后处理检查和自动修复错别字、语法等硬伤。
迁移自：Makefile._step_icu()
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from kunlun.pipeline.steps._base import PipelineStepBase


class ICUStep(PipelineStepBase):
    step_name = "icu"
    required = False
    timeout = 120.0
    degrade_on_failure = True

    async def _execute_impl(self, ctx: Any) -> dict:
        if ctx.skip_icu:
            logger.info(f"[{ctx.pipeline_id}] 自适应跳过ICU (chapter_type={ctx.chapter_type})")
            return {"skipped": True, "reason": f"chapter_type={ctx.chapter_type}"}

        try:
            from kunlun.audit.icu import icu_system
            from kunlun.token_tracker import token_tracker

            icu_auto_fix = token_tracker.check_budget(ctx.pipeline_id, "icu", 10000)
            if not icu_auto_fix:
                logger.info(f"[{ctx.pipeline_id}] 预算不足，ICU跳过自动修复（仅检查）")

            icu_report, icu_draft = await icu_system.run_full_check(
                ctx.draft, ctx.chapter, chapter_type="normal", auto_fix=icu_auto_fix
            )
            if icu_report.passed:
                ctx.draft = icu_draft
            if not icu_report.passed:
                logger.info(
                    f"[{ctx.pipeline_id}] ICU {icu_report.overall_score:.1f}分 "
                    f"{len(icu_report.critical_issues)}个问题"
                )
                ctx.result["icu_report"] = {
                    "overall_score": icu_report.overall_score,
                    "critical_issues": len(icu_report.critical_issues),
                }
            ctx.result["draft"] = ctx.draft
            return ctx.result.get("icu_report", {"passed": True})
        except Exception as e_icu:
            logger.warning(f"[{ctx.pipeline_id}] ICU 跳过: {e_icu}")
            ctx.result["draft"] = ctx.draft
            return {"skipped": True, "reason": str(e_icu)}
