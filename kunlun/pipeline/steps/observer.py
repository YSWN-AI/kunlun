"""
管线步骤：Observer 观测 (Step 7)

观测章节内容，提取角色变化、事件、伏笔、新实体。
迁移自：Makefile._step_observer()
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from kunlun.pipeline.steps._base import PipelineStepBase


class ObserverStep(PipelineStepBase):
    step_name = "observer"
    required = False
    timeout = 60.0
    degrade_on_failure = True

    async def _execute_impl(self, ctx: Any) -> dict:
        try:
            await self._report(ctx, "observer_start")
            from kunlun.agents.observer import observer

            known_characters = ctx.blueprint.get("key_characters", []) if ctx.blueprint else []
            observer_report = observer.observe(
                ctx.polished_draft,
                chapter=ctx.chapter,
                book_id=ctx.book_id,
                blueprint=ctx.blueprint,
                known_characters=known_characters,
            )
            ctx.result["observer_report"] = {
                "character_changes": len(observer_report.character_changes),
                "events": len(observer_report.events),
                "foreshadowing_planted": len(observer_report.foreshadowing.planted),
                "foreshadowing_revealed": len(observer_report.foreshadowing.revealed),
                "new_entities": sum(len(v) for v in observer_report.new_entities.values()),
                "key_plot_points": len(observer_report.key_plot_points),
            }
            await self._report(ctx, "observer_done", ctx.result["observer_report"])
            logger.info(f"[{ctx.pipeline_id}] Observer: {ctx.result['observer_report']}")
        except Exception as e_obs:
            logger.warning(f"[{ctx.pipeline_id}] Observer 跳过（非阻塞）: {e_obs}")

        return ctx.result.get("observer_report", {})
