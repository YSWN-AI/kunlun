"""
管线步骤：KG 知识图谱更新 (Step 6)

章节完成后更新 Neo4j/SQLite 知识图谱。
迁移自：Makefile._step_kg_update()
"""

from __future__ import annotations

from typing import Any

from kunlun.pipeline.steps._base import PipelineStepBase


class KGUpdateStep(PipelineStepBase):
    step_name = "kg_update"
    required = False
    timeout = 60.0
    degrade_on_failure = True

    async def _execute_impl(self, ctx: Any) -> dict:
        kg_result = (
            await self._mf._run_kg_update(
                {
                    "book_id": ctx.book_id,
                    "chapter": ctx.chapter,
                    "blueprint": ctx.blueprint,
                    "draft": ctx.polished_draft,
                }
            )
            if self._mf
            else {"updated": []}
        )

        ctx._kg_result = kg_result
        await self._publish_msg(
            ctx,
            {
                "updated": kg_result.get("updated", []),
            },
        )

        return {"updated": kg_result.get("updated", [])}
