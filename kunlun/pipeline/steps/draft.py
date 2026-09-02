"""
管线步骤：草稿生成 (Step 2)

Writer 多模型抽卡生成章节草稿。
迁移自：Makefile._step_draft()
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

from kunlun.pipeline.steps._base import PipelineStepBase


class DraftStep(PipelineStepBase):
    step_name = "draft"
    required = True
    timeout = 300.0
    retry_count = 1

    async def _execute_impl(self, ctx: Any) -> dict:
        t0 = time.perf_counter()
        await self._report(ctx, "draft_start")

        from kunlun.agents.writer import Writer
        from kunlun.gacha.engine import gacha_engine
        from kunlun.token_tracker import token_tracker

        writer = Writer()
        effective_mode = ctx.mode

        if not token_tracker.check_budget(ctx.pipeline_id, "writer", 50000):
            downgrade_map = {
                "gacha_ultimate_5": "gacha_parallel_3",
                "gacha_parallel_3": "gacha_cheap_2",
            }
            effective_mode = downgrade_map.get(ctx.mode, "single_fix")
            logger.info(
                f"[{ctx.pipeline_id}] 预算不足，生成模式降级: {ctx.mode} → {effective_mode}"
            )

        writer_result = await writer._generate(
            {
                "blueprint": ctx.blueprint,
                "mode": effective_mode,
                "kg_snapshot_id": getattr(ctx, "kg_snapshot_id", ""),
            }
        )

        ctx.draft = writer_result.get("draft", "")
        best_model = writer_result.get("model_used") or (
            gacha_engine.last_best_model if hasattr(gacha_engine, "last_best_model") else ctx.mode
        )
        ctx.result["draft"] = ctx.draft
        ctx.result["gacha_best_model"] = best_model

        duration = time.perf_counter() - t0
        try:
            from kunlun.observability import record_generation_step

            record_generation_step("writer", duration)
        except Exception as e:
            logger.debug(f"[{ctx.pipeline_id}] 可观测性记录失败 (writer): {e}")

        await self._report(
            ctx,
            "draft_done",
            {
                "draft_preview": ctx.draft[:200],
                "word_count": len(ctx.draft),
                "best_model": best_model,
            },
        )
        await self._publish_msg(
            ctx,
            {
                "word_count": len(ctx.draft),
                "best_model": best_model,
            },
        )

        logger.info(f"[{ctx.pipeline_id}] 草稿生成完成 ({len(ctx.draft)}字, {best_model})")
        return {"draft": ctx.draft, "word_count": len(ctx.draft), "best_model": best_model}
