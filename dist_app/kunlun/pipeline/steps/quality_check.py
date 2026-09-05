"""
管线步骤：质量检查 (Step 15)

番茄优化器 + 质量面板 + 趋势追踪。
迁移自：Makefile._step_quality_check()
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from kunlun.pipeline.steps._base import PipelineStepBase


class QualityCheckStep(PipelineStepBase):
    step_name = "quality_check"
    required = False
    timeout = 60.0
    degrade_on_failure = True

    async def _execute_impl(self, ctx: Any) -> dict:
        try:
            from kunlun.audit.fanqie_gates import fanqie_optimizer
            from kunlun.quality import quality_dashboard

            final_draft = ctx.polished_draft or ctx.draft
            fanqie_report = fanqie_optimizer.check_chapter(
                final_draft, chapter=ctx.chapter, is_first_three=(ctx.chapter <= 3)
            )
            quality_report = quality_dashboard.analyze_chapter(final_draft, chapter=ctx.chapter)

            ctx.result["fanqie_check"] = {
                "traffic_rating": fanqie_report.traffic_rating,
                "fanqie_ai_score": fanqie_report.fanqie_ai_score,
                "has_cliffhanger": fanqie_report.has_cliffhanger,
                "hook_strength": fanqie_report.hook_strength,
                "suggestions": fanqie_report.suggestions[:3],
            }
            ctx.result["quality_report"] = {
                "rating": quality_report.quality_rating,
                "overall_score": quality_report.overall_score,
                "ai_score": quality_report.ai_score,
                "issues": quality_report.issues_summary[:3],
                "warnings": quality_report.warnings[:3],
            }

            if fanqie_report.suggestions:
                for s in fanqie_report.suggestions[:2]:
                    logger.info(f"[{ctx.pipeline_id}] [流量建议] {s}")

            logger.info(
                f"[{ctx.pipeline_id}] 质量评级: {quality_report.quality_rating} "
                f"(总分{quality_report.overall_score:.2f}, "
                f"流量评级:{fanqie_report.traffic_rating})"
            )

            # 趋势追踪
            try:
                from kunlun.quality.tracker import QualityTracker

                qt = QualityTracker(ctx.book_id)
                qt.record_from_report(ctx.chapter, quality_report, fanqie_report)
                trend = qt.get_trend()
                if trend.direction == "declining":
                    logger.warning(
                        f"[{ctx.pipeline_id}] 质量呈下降趋势({trend.slope:.3f})，"
                        f"近{trend.chapters_analyzed}章均分{trend.avg_score:.2f}"
                    )
                    for s in trend.suggestions:
                        logger.info(f"[{ctx.pipeline_id}] [质量建议] {s}")
            except Exception as e_t:
                logger.debug(f"[{ctx.pipeline_id}] 质量趋势记录跳过: {e_t}")
        except Exception as e_q:
            logger.debug(f"[{ctx.pipeline_id}] 质量检查跳过: {e_q}")

        return {
            "fanqie": ctx.result.get("fanqie_check", {}),
            "quality": ctx.result.get("quality_report", {}),
        }
