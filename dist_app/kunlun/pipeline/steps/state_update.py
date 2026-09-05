"""
管线步骤：状态更新 (Step 12)

更新角色情绪状态和位置移动。
迁移自：Makefile._step_state_update()
"""

from __future__ import annotations

from typing import Any

from kunlun.pipeline.steps._base import PipelineStepBase


class StateUpdateStep(PipelineStepBase):
    step_name = "state_update"
    required = False
    timeout = 30.0
    degrade_on_failure = True

    async def _execute_impl(self, ctx: Any) -> dict:
        from kunlun.state.machine import state_machine

        scenes = ctx.blueprint.get("scenes", []) or []
        characters_updated = set()
        for scene in scenes:
            for char_uid in scene.get("characters", []):
                state_machine.get_or_create(char_uid)
                state_machine.update_emotion(
                    char_uid,
                    scene.get("emotion", "neutral"),
                    f"第{ctx.chapter}章剧情推进",
                    ctx.chapter,
                )
                if scene.get("location_uid"):
                    state_machine.move_to(char_uid, scene["location_uid"], ctx.chapter)
                characters_updated.add(char_uid)

        await self._publish_msg(ctx, {"characters_updated": len(characters_updated)})

        return {"characters_updated": len(characters_updated)}
