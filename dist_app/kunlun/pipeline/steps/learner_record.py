"""
管线步骤：学习记录 (Step 11)

记录章节完成事件、冷却矩阵、反向刹车、大纲配额。
迁移自：Makefile._step_learner_record()
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from loguru import logger

from kunlun.pipeline.steps._base import PipelineStepBase


class LearnerRecordStep(PipelineStepBase):
    step_name = "learner_record"
    required = False
    timeout = 30.0
    degrade_on_failure = True

    async def _execute_impl(self, ctx: Any) -> dict:
        await self._learn(
            ctx,
            "CHAPTER_COMPLETED",
            {
                "book_id": ctx.book_id,
                "chapter": ctx.chapter,
                "word_count": len(ctx.polished_draft or ""),
            },
        )
        await self._learn(
            ctx,
            "CHAPTER_PUBLISHED",
            {
                "book_id": ctx.book_id,
                "chapter": ctx.chapter,
                "path": ctx.result.get("published_path", ""),
                "published_at": datetime.now().isoformat(),
            },
        )

        # 事件冷却记录
        try:
            from kunlun.cooldown import get_cooldown_matrix

            cm = get_cooldown_matrix(ctx.book_id)
            cm.record_event(
                f"chapter_{ctx.chapter_type}",
                ctx.chapter,
                description=ctx.blueprint.get("title", f"第{ctx.chapter}章"),
            )
        except Exception as e:
            logger.debug(f"[Pipeline] 冷却记录跳过: {e}")

        # 反向刹车检查
        try:
            from kunlun.brake import reverse_brake

            brake_result = reverse_brake.check_chapter_end(
                ctx.polished_draft, ctx.chapter, total_chapters=0, is_final=False
            )
            for w in brake_result.warnings:
                logger.info(f"[Brake] ch{ctx.chapter}: {w}")
        except Exception as e:
            logger.debug(f"[Pipeline] 刹车检查跳过: {e}")

        # 大纲配额验证
        try:
            from kunlun.outline_anchor import get_outline_anchor

            anchor = get_outline_anchor(ctx.book_id)
            if anchor.total_chapters > 0:
                qw = anchor.validate_chapter(ctx.chapter, 1.0 / max(anchor.total_chapters, 1))
                for w in qw:
                    logger.info(f"[Quota] ch{ctx.chapter}: {w}")
        except Exception as e:
            logger.debug(f"[Pipeline] 配额验证跳过: {e}")

        return {"chapter_completed": ctx.chapter}
