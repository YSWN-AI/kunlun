"""
管线步骤：学习反思 (Step 14)

对比原始草稿与修正稿，生成改进补丁和规则。
迁移自：Makefile._step_post_reflect()
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from kunlun.pipeline.steps._base import PipelineStepBase


class PostReflectStep(PipelineStepBase):
    step_name = "reflect"
    required = False
    timeout = 60.0
    degrade_on_failure = True

    async def _execute_impl(self, ctx: Any) -> dict:
        try:
            await self._report(ctx, "reflect_start")
            from kunlun.learn.reflector import post_reflect_hook

            reflect_result = post_reflect_hook(
                raw_draft=ctx.draft,
                corrected_draft=ctx.polished_draft,
                pipeline_id=ctx.pipeline_id,
            )
            ctx.result["reflect"] = reflect_result

            await self._report(
                ctx,
                "reflect_done",
                {
                    "patches_generated": reflect_result.get("patches_generated", 0),
                    "new_rules": reflect_result.get("new_rules", 0),
                    "diffs_count": reflect_result.get("diffs_count", 0),
                },
            )

            if reflect_result.get("new_rules", 0) > 0:
                await self._learn(
                    ctx,
                    "REFLECT_RULES_UPDATED",
                    {
                        "book_id": ctx.book_id,
                        "chapter": ctx.chapter,
                        "new_rules": reflect_result.get("new_rules", 0),
                    },
                )
        except ImportError:
            logger.debug(f"[{ctx.pipeline_id}] Reflector 未安装，跳过学习循环")
        except Exception as e_reflect:
            logger.warning(f"[{ctx.pipeline_id}] 学习循环跳过（非阻塞）: {e_reflect}")

        return ctx.result.get("reflect", {})
