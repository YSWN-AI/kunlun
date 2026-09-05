"""
管线步骤：修订循环 (Step 4)

审计不通过时循环修订（最多3轮）。
迁移自：Makefile._step_revise_loop()
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from kunlun.pipeline.steps._base import PipelineStepBase


class ReviseLoopStep(PipelineStepBase):
    step_name = "revise"
    required = False
    timeout = 600.0  # 多轮修订可能耗时较长
    degrade_on_failure = True

    async def _execute_impl(self, ctx: Any) -> dict:
        if ctx.skip_revise:
            logger.info(f"[{ctx.pipeline_id}] 自适应跳过修订循环 (chapter_type={ctx.chapter_type})")
            ctx.result["revisions"] = ctx.revision_count
            return {"skipped": True, "reason": f"chapter_type={ctx.chapter_type}"}

        if not ctx.audit_result.get("passed"):
            if ctx.auditor is None:
                from kunlun.agents.auditor import Auditor

                ctx.auditor = Auditor()
            from kunlun.agents.writer import Writer

            writer = Writer()

            while (
                not ctx.audit_result.get("passed")
                and ctx.revision_count < 3
                and ctx.auditor is not None
            ):
                ctx.revision_count += 1
                await asyncio.sleep(ctx._yield_interval)

                await self._report(ctx, "revise_start", {"round": ctx.revision_count})
                revision_result = await writer._revise(
                    {
                        "draft": ctx.draft,
                        "audit_report": ctx.audit_result,
                        "book_id": ctx.book_id,
                    }
                )
                ctx.draft = revision_result.get("draft", ctx.draft)
                ctx.audit_result = await ctx.auditor.execute(
                    {
                        "draft": ctx.draft,
                        "blueprint": ctx.blueprint,
                        "kg_snapshot_id": getattr(ctx, "kg_snapshot_id", ""),
                    }
                )
                await self._report(
                    ctx,
                    "revise_done",
                    {
                        "round": ctx.revision_count,
                        "audit": ctx.audit_result,
                    },
                )
                await self._learn(
                    ctx,
                    "REVISION_APPLIED",
                    {
                        "book_id": ctx.book_id,
                        "chapter": ctx.chapter,
                        "round": ctx.revision_count,
                    },
                )

        ctx.result["revisions"] = ctx.revision_count
        ctx.result["draft"] = ctx.draft
        ctx.result["audit_passed"] = ctx.audit_result.get("passed", False)

        await self._publish_msg(
            ctx,
            {
                "rounds": ctx.revision_count,
                "passed": ctx.audit_result.get("passed", False),
            },
        )

        logger.info(f"[{ctx.pipeline_id}] 修订循环完成 ({ctx.revision_count}轮)")
        return {"revisions": ctx.revision_count, "passed": ctx.audit_result.get("passed", False)}
