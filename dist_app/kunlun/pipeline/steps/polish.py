"""
管线步骤：文风润色 (Step 5)

StyleEngineer 风格润色 + 字数治理（扩写/压缩）。
迁移自：Makefile._step_polish()
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

from kunlun.pipeline.steps._base import PipelineStepBase


class PolishStep(PipelineStepBase):
    step_name = "polish"
    required = True
    timeout = 180.0
    retry_count = 1

    async def _execute_impl(self, ctx: Any) -> dict:
        t0 = time.perf_counter()
        await self._report(ctx, "polish_start")

        from kunlun.style.engineer import StyleEngineer

        engineer = StyleEngineer()
        polish_result = await engineer.execute({"draft": ctx.draft})
        ctx.polished_draft = polish_result.get("polished_draft", ctx.draft)
        ctx.result["style_changes"] = polish_result.get("changes", 0)

        duration = time.perf_counter() - t0
        try:
            from kunlun.observability import record_generation_step

            record_generation_step("polisher", duration)
        except Exception as e:
            logger.debug(f"[{ctx.pipeline_id}] 可观测性记录失败 (polisher): {e}")

        # 字数治理
        try:
            from kunlun.config import settings
            from kunlun.length_gov import length_governor

            target = settings.pipeline_default_word_count
            lc = length_governor.check(ctx.polished_draft, target=target)
            if lc.action_needed == "expand":
                ctx.polished_draft = await length_governor.expand(
                    ctx.polished_draft, target=target, book_id=ctx.book_id
                )
                ctx.result["length_action"] = f"expand:{lc.word_count}→{target}"
            elif lc.action_needed == "compress":
                ctx.polished_draft = await length_governor.compress(
                    ctx.polished_draft, target=target
                )
                ctx.result["length_action"] = f"compress:{lc.word_count}→{target}"
        except Exception as e:
            logger.debug(f"[{ctx.pipeline_id}] 字数治理跳过: {e}")

        ctx.result["draft"] = ctx.polished_draft

        await self._report(ctx, "polish_done", {"changes": ctx.result["style_changes"]})

        logger.info(f"[{ctx.pipeline_id}] 润色完成 ({ctx.result['style_changes']}处修改)")
        return {"style_changes": ctx.result["style_changes"]}
