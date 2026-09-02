"""
管线步骤：蓝图生成 (Step 1)

Architect 生成章节蓝图，含标题、场景、关键角色等。
迁移自：Makefile._step_blueprint()
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

from kunlun.pipeline.steps._base import PipelineStepBase


class BlueprintStep(PipelineStepBase):
    step_name = "blueprint"
    required = True
    timeout = 180.0
    retry_count = 1

    async def _execute_impl(self, ctx: Any) -> dict:
        t0 = time.perf_counter()
        await self._report(ctx, "blueprint_start")

        from kunlun.agents.architect import Architect
        from kunlun.kg.snapshot import snapshot_manager

        snapshot = snapshot_manager.create_snapshot(ctx.book_id, ctx.chapter)
        architect = Architect()
        arch_result = await architect.execute(
            {
                "book_id": ctx.book_id,
                "chapter": ctx.chapter,
                "kg_snapshot_id": getattr(ctx, "kg_snapshot_id", ""),
                "kg_summary": snapshot.to_summary(),
            }
        )

        ctx.blueprint = arch_result.get("blueprint", {})
        ctx.result["blueprint"] = ctx.blueprint

        duration = time.perf_counter() - t0
        try:
            from kunlun.observability import record_generation_step

            record_generation_step("architect", duration)
        except Exception as e:
            logger.debug(f"[{ctx.pipeline_id}] 可观测性记录失败 (architect): {e}")

        await self._report(ctx, "blueprint_done", {"blueprint": ctx.blueprint})
        await self._publish_msg(ctx, {"chapter": ctx.chapter})

        logger.info(f"[{ctx.pipeline_id}] 蓝图生成完成 (ch{ctx.chapter})")
        return {"blueprint": ctx.blueprint, "duration": duration}
