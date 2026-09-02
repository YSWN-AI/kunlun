"""
管线步骤：内容审计 (Step 3)

33维审计 + 8门禁降级，检查章节质量是否通过。
迁移自：Makefile._step_audit()
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

from kunlun.pipeline.steps._base import PipelineStepBase


class AuditStep(PipelineStepBase):
    step_name = "audit"
    required = True
    timeout = 180.0
    retry_count = 1

    async def _execute_impl(self, ctx: Any) -> dict:
        t0 = time.perf_counter()
        await self._report(ctx, "audit_start")

        ctx.audit_result = {"passed": True, "gates": {}, "details": ""}
        ctx.auditor = None

        draft = ctx.draft or ctx.result.get("draft", "")
        blueprint = ctx.blueprint or ctx.result.get("blueprint", {})

        try:
            from kunlun.audit.audit33 import auditor33

            report33 = auditor33.run_audit(draft, ctx.chapter, blueprint, ctx.book_id)
            ctx.audit_result = {
                "passed": report33.passed,
                "overall_score": report33.overall_score,
                "ai_detection_score": report33.ai_detection_score,
                "fatal_count": report33.fatal_count,
                "warn_count": report33.warn_count,
                "gates": {
                    d.dim_id: {"level": d.level, "score": d.score, "detail": d.detail}
                    for d in report33.dimensions
                },
                "details": report33.summary,
            }
            logger.info(f"[{ctx.pipeline_id}] 33维审计: {report33.summary}")
        except Exception as e33:
            logger.warning(f"[{ctx.pipeline_id}] 33维审计降级到8门禁: {e33}")
            from kunlun.agents.auditor import Auditor

            ctx.auditor = Auditor()
            ctx.audit_result = await ctx.auditor.execute(
                {
                    "draft": draft,
                    "blueprint": blueprint,
                    "kg_snapshot_id": getattr(ctx, "kg_snapshot_id", ""),
                }
            )

        ctx.result["audit_passed"] = ctx.audit_result.get("passed", False)

        duration = time.perf_counter() - t0
        try:
            from kunlun.observability import record_generation_step

            record_generation_step("auditor", duration)
        except Exception as e:
            logger.debug(f"[{ctx.pipeline_id}] 可观测性记录失败 (auditor): {e}")

        await self._report(ctx, "audit_done", {"audit_result": ctx.audit_result})
        await self._publish_msg(ctx, {"passed": ctx.audit_result.get("passed", False)})
        await self._learn(
            ctx,
            "AUDIT_PASSED" if ctx.audit_result.get("passed") else "AUDIT_FAILED",
            {"book_id": ctx.book_id, "chapter": ctx.chapter, "audit": ctx.audit_result},
        )

        return ctx.audit_result
