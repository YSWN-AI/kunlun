"""
管线步骤：情报同步 (Step 13)

同步伏笔揭示信息到情报追踪器。
迁移自：Makefile._step_intel_sync()
"""

from __future__ import annotations

from typing import Any

from kunlun.pipeline.steps._base import PipelineStepBase


class IntelSyncStep(PipelineStepBase):
    step_name = "intel_sync"
    required = False
    timeout = 30.0
    degrade_on_failure = True

    async def _execute_impl(self, ctx: Any) -> dict:
        from kunlun.intel.tracker import IntelItem, intel_tracker

        fp = ctx.blueprint.get("foreshadowing", {})
        scene_characters = set()
        for scene in ctx.blueprint.get("scenes", []):
            for char in scene.get("characters_involved", []):
                scene_characters.add(char)

        intel_count = 0
        for reveal_name in fp.get("to_reveal", []):
            intel_tracker.add_intel(
                IntelItem(
                    uid=f"intel_{ctx.book_id}_ch{ctx.chapter}_{reveal_name}",
                    content=f"伏笔揭示: {reveal_name}",
                    source_event_uid=f"event_{ctx.book_id}_ch{ctx.chapter}",
                    acquired_chapter=ctx.chapter,
                    classification="公开",
                ),
                known_by=list(scene_characters),
            )
            intel_count += 1

        await self._publish_msg(ctx, {"intel_items": intel_count})

        return {"intel_items": intel_count}
