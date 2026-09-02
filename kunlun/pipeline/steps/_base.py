"""
管线步骤基类 — 为 Makefile 管线步骤提供统一的回调注入

所有从 Makefile._step_* 提取的步骤类继承 PipelineStepBase，
通过 makefile 引用获取进度上报、检查点保存、消息总线等能力。

用法：
    class BlueprintStep(PipelineStepBase):
        step_name = "blueprint"
        async def _execute_impl(self, ctx):
            ...
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from kunlun.agents.message_bus import message_bus
from kunlun.pipeline.step_base import BaseStep

if TYPE_CHECKING:
    from kunlun.agents.makefile import Makefile, _PipelineContext


class PipelineStepBase(BaseStep):
    """带 Makefile 回调注入的管线步骤基类"""

    def __init__(self, makefile: Makefile | None = None, **kwargs: Any):
        super().__init__(**kwargs)
        self._mf = makefile

    async def _report(self, ctx: _PipelineContext, step: str, data: Any = None) -> None:
        """上报进度（非阻塞）"""
        if self._mf:
            await self._mf._report(ctx, step, data)

    async def _learn(self, ctx: _PipelineContext, event_type: str, data: Any = None) -> None:
        """学习记录（非阻塞）"""
        if self._mf:
            await self._mf._learn(ctx, event_type, data)

    async def _save_checkpoint(self, ctx: _PipelineContext, **overrides: Any) -> None:
        """保存步骤检查点"""
        if self._mf:
            await self._mf._save_step_checkpoint(ctx, self.step_name, **overrides)

    async def _publish_msg(self, ctx: _PipelineContext, data: dict) -> None:
        """发布消息总线事件（非阻塞）"""
        try:
            await message_bus.publish(
                f"kunlun.pipeline.{ctx.pipeline_id}.step",
                {
                    "pipeline_id": ctx.pipeline_id,
                    "step": self.step_name,
                    "status": "done",
                    "data": data,
                },
            )
        except Exception as e:
            logger.debug(f"[{self.step_name}] message_bus 发布失败: {e}")

    async def _on_step_done(self, ctx: Any, _result: Any) -> None:
        """步骤完成：标记 completed_steps + 追加 steps 列表"""
        if hasattr(ctx, "completed_steps"):
            ctx.completed_steps.add(self.step_name)
        if hasattr(ctx, "result") and isinstance(ctx.result, dict) and "steps" in ctx.result:
            ctx.result["steps"].append(self.step_name)
