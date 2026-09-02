"""
管线步骤：真相与指纹 (Step 9)

更新真相文件 + 加载文风指纹。
迁移自：Makefile._step_truth_and_fingerprint()
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from kunlun.pipeline.steps._base import PipelineStepBase


class TruthAndFingerprintStep(PipelineStepBase):
    step_name = "truth_and_fingerprint"
    required = False
    timeout = 30.0
    degrade_on_failure = True

    async def _execute_impl(self, ctx: Any) -> dict:
        result = {}
        # 真相文件更新
        try:
            from kunlun.truth import get_truth_manager

            tm = get_truth_manager(ctx.book_id)
            tm.add_chapter_summary(
                ctx.chapter,
                ctx.polished_draft[:200] if ctx.polished_draft else "",
                ctx.blueprint.get("scenes", []),
                [],
                [],
            )
            result["truth_updated"] = True
            logger.debug(f"[{ctx.pipeline_id}] 真相文件已更新")
        except Exception as e_truth:
            logger.debug(f"[{ctx.pipeline_id}] 真相文件更新跳过: {e_truth}")

        # 文风指纹加载
        try:
            from kunlun.style.fingerprint import style_analyzer

            fp = style_analyzer.load_fingerprint(ctx.book_id)
            if fp:
                result["fingerprint_loaded"] = fp.name
                logger.info(f"[{ctx.pipeline_id}] 文风指纹已加载: {fp.name}")
        except Exception as e:
            logger.debug(f"[{ctx.pipeline_id}] 文风指纹加载跳过: {e}")

        return result
