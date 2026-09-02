"""
管线步骤：发布 (Step 10)

将最终定稿写入输出目录。
迁移自：Makefile._step_publish()
"""

from __future__ import annotations

import asyncio
from typing import Any

from kunlun.pipeline.steps._base import PipelineStepBase


class PublishStep(PipelineStepBase):
    step_name = "publish"
    required = True
    timeout = 30.0

    async def _execute_impl(self, ctx: Any) -> dict:
        pub_result = await self._mf._do_publish(ctx) if self._mf else {}
        await asyncio.sleep(ctx._yield_interval)

        return pub_result
