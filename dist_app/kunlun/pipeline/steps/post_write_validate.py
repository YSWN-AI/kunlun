"""
管线步骤：后写验证 (Step 2.5)

草稿生成后立即校验内容质量，检测严重问题和警告。
迁移自：Makefile._step_post_write_validate()
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from kunlun.pipeline.steps._base import PipelineStepBase


class PostWriteValidateStep(PipelineStepBase):
    step_name = "post_write_validate"
    required = False
    timeout = 60.0
    degrade_on_failure = True

    async def _execute_impl(self, ctx: Any) -> dict:
        try:
            from kunlun.audit.post_write_validator import post_write_validator

            pw_report = post_write_validator.validate(
                ctx.draft or ctx.result.get("draft", ""), ctx.chapter
            )
            if pw_report.critical_issues:
                logger.info(
                    f"[{ctx.pipeline_id}] 后写验证: {len(pw_report.critical_issues)}个严重问题, "
                    f"{len(pw_report.warnings)}个警告 (得分 {pw_report.overall_score:.2f})"
                )
                for issue in pw_report.critical_issues:
                    logger.warning(f"[{ctx.pipeline_id}]   ⚠ {issue}")
            ctx.result["post_write_check"] = {
                "score": pw_report.overall_score,
                "critical_count": len(pw_report.critical_issues),
                "warning_count": len(pw_report.warnings),
            }
            return ctx.result["post_write_check"]
        except Exception as e:
            logger.debug(f"[{ctx.pipeline_id}] 后写验证跳过: {e}")
            return {"skipped": True, "reason": str(e)}
