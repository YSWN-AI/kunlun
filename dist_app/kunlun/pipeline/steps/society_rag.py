"""
管线步骤：社会推演 (Step 1.5)

对蓝图进行社会RAG召回和剧情逻辑推演。
迁移自：Makefile._step_society_rag()
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from kunlun.pipeline.steps._base import PipelineStepBase


class SocietyRAGStep(PipelineStepBase):
    step_name = "society"
    required = False
    timeout = 120.0
    degrade_on_failure = True

    async def _execute_impl(self, ctx: Any) -> dict:
        bp_out = ctx.result.get("blueprint", {})

        if ctx.skip_society:
            logger.info(f"[{ctx.pipeline_id}] 自适应跳过推演 (chapter_type={ctx.chapter_type})")
            ctx.result["blueprint"] = bp_out
            return {"skipped": True, "reason": f"chapter_type={ctx.chapter_type}"}

        try:
            from kunlun.agents.sociologist import sociologist
            from kunlun.gacha.engine import gacha_engine
            from kunlun.token_tracker import token_tracker

            rag_query = ctx.blueprint.get("title", "") + " "
            rag_query += " ".join(
                s.get("description", "") for s in ctx.blueprint.get("scenes", [])[:3]
            )
            rag_query += " " + " ".join(ctx.blueprint.get("key_characters", []))

            if rag_query.strip():
                ctx.society_insights["rag_context"] = await sociologist.query_society_rag(
                    ctx.book_id, rag_query[:200], top_k=5
                )

            plot_prompt = (
                f"为以下章节做剧情逻辑推演:\n"
                f"章节: {ctx.blueprint.get('title', f'第{ctx.chapter}章')}\n"
                f"类型: {ctx.chapter_type}\n"
                f"场景: {ctx.blueprint.get('scenes', [])}\n"
                f"关键角色: {ctx.blueprint.get('key_characters', [])}\n\n"
                f"请分析: 1)剧情驱动力 2)冲突焦点 3)角色动机 "
                f"4)可能的情节陷阱 5)读者预期管理\n"
                f"输出为简洁的5点分析，每点1-2句话。"
            )

            if token_tracker.check_budget(ctx.pipeline_id, "sociologist", 10000):
                plot_result = await gacha_engine.generate(
                    plot_prompt, mode="single_fix", agent="sociologist"
                )
                ctx.society_insights["plot_deduction"] = plot_result.get("best_text", "")
            else:
                logger.info(f"[{ctx.pipeline_id}] 预算不足，跳过剧情推演")

            bp_out["society_insights"] = ctx.society_insights
            logger.info("[Pipeline] 推演RAG召回+剧情推演完成 (1次LLM调用)")
        except ImportError:
            logger.warning("[Pipeline] Sociologist 未安装")
        except Exception as e:
            logger.warning(f"[Pipeline] 推演跳过: {e}")

        ctx.result["blueprint"] = bp_out

        return {"society_insights": ctx.society_insights}
