"""
管线步骤：Reflector 反写 (Step 8)

将观测结果反写回 KG 并更新快照。
迁移自：Makefile._step_reflector()
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from kunlun.pipeline.steps._base import PipelineStepBase


class ReflectorStep(PipelineStepBase):
    step_name = "reflector"
    required = False
    timeout = 60.0
    degrade_on_failure = True
    skip_conditions: list = ["skip_reflector"]

    async def _execute_impl(self, ctx: Any) -> dict:
        if "observer_report" not in ctx.result:
            return {"skipped": True, "reason": "no_observer_report"}

        try:
            await self._report(ctx, "reflector_start")
            from kunlun.agents.observer import observer
            from kunlun.agents.reflector_agent import reflector

            known_characters = ctx.blueprint.get("key_characters", []) if ctx.blueprint else []
            observer_report = observer.observe(
                ctx.polished_draft,
                chapter=ctx.chapter,
                book_id=ctx.book_id,
                blueprint=ctx.blueprint,
                known_characters=known_characters,
            )
            if observer_report:
                reflector_result = reflector.write(observer_report, book_id=ctx.book_id)
                ctx.result["reflector_result"] = {
                    "snapshot_version_id": reflector_result.snapshot_version_id,
                    "characters_updated": reflector_result.characters_updated,
                    "events_recorded": reflector_result.events_recorded,
                    "foreshadowing_updated": reflector_result.foreshadowing_updated,
                    "entities_indexed": reflector_result.entities_indexed,
                    "success": reflector_result.success,
                }
                await self._report(ctx, "reflector_done", ctx.result["reflector_result"])
                logger.info(f"[{ctx.pipeline_id}] Reflector: {ctx.result['reflector_result']}")
        except Exception as e_ref:
            logger.warning(f"[{ctx.pipeline_id}] Reflector 跳过（非阻塞）: {e_ref}")

        return ctx.result.get("reflector_result", {})
