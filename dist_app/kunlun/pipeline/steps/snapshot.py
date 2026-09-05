"""
管线步骤：KG 快照拍摄 (Step 0)

每次章节开始前拍摄 KG 快照，记录当前所有角色、物品、
地点、伏笔状态、关系图等，作为后续生成步骤的上下文输入。

迁移自：Makefile._step_snapshot()
用法示例：
    step = SnapshotStep()
    result = await step.execute(pipeline_context)
    # result.data 包含: {"snapshot_id": "xxx", "kg_summary": {...}}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger

from kunlun.kg.snapshot import snapshot_manager
from kunlun.pipeline.steps._base import PipelineStepBase


@dataclass
class SnapshotStepResult:
    """快照步骤的返回结构（供类型标注使用）"""

    snapshot_id: str
    kg_summary: dict[str, Any]
    entities_count: int = 0
    relationships_count: int = 0


class SnapshotStep(PipelineStepBase):
    """
    管线步骤：KG 快照拍摄

    - 从 Neo4j / SQLite 图提取当前作品的所有实体和关系
    - 生成不可变快照（json 序列化到 DATA_DIR/snapshots/）
    - 将 snapshot_id 和 kg_summary 注入管线上下文
    - 所有后续步骤依赖快照作为跨章一致性基线

    属性覆盖：
        step_name = "snapshot"     # 与 PipelineStep.SNAPSHOT 对应
        required = True            # 快照失败则管线中止
        timeout = 30.0             # 快照不应超过 30s
        retry_count = 2            # KG 连接不稳定时可重试 2 次
    """

    step_name = "snapshot"
    required = True
    timeout = 30.0
    retry_count = 2
    retry_delay = 1.5
    degrade_on_failure = False  # 快照不可或缺，失败后应中止管线

    async def _execute_impl(self, ctx: Any) -> dict:
        """
        拍摄 KG 快照。

        Args:
            ctx: 管线上下文，需包含 book_id 和 chapter 属性。

        Returns:
            {"snapshot_id": str, "kg_summary": dict, ...}

        Raises:
            KGConnectionError: KG 存储不可用时抛出（可重试）
        """
        book_id: str = getattr(ctx, "book_id", "")
        chapter: int = getattr(ctx, "chapter", 0)

        if not book_id:
            raise ValueError("Pipeline 上下文中缺少 book_id")

        logger.debug(f"[snapshot] 拍摄 KG 快照: book={book_id}, ch={chapter}")
        snapshot = snapshot_manager.create_snapshot(book_id, chapter)

        summary = snapshot.to_summary()
        total_entities = (
            len(snapshot.characters)
            + len(snapshot.items)
            + len(snapshot.locations)
            + len(snapshot.skills)
            + len(snapshot.events)
            + len(snapshot.organizations)
        )

        logger.info(
            f"[snapshot] 快照完成: {snapshot.snapshot_id}, "
            f"实体={total_entities}, 关系={len(snapshot.relationships)}"
        )

        # 注入到管线上下文（桥接模式下 _on_step_done 不会被调用，在此处理）
        if hasattr(ctx, "kg_snapshot_id"):
            ctx.kg_snapshot_id = snapshot.snapshot_id
        if hasattr(ctx, "result") and isinstance(ctx.result, dict):
            ctx.result["kg_snapshot_id"] = snapshot.snapshot_id

        await self._publish_msg(ctx, {"snapshot_id": snapshot.snapshot_id})

        return {
            "snapshot_id": snapshot.snapshot_id,
            "kg_summary": summary,
            "entities_count": total_entities,
            "relationships_count": len(snapshot.relationships),
            "characters_count": len(snapshot.characters),
            "foreshadowing_count": len(snapshot.foreshadowing_planted)
            + len(snapshot.foreshadowing_revealed),
        }

    async def _on_step_done(self, ctx: Any, result: Any) -> None:
        """
        步骤完成后：注入快照数据到管线上下文。

        这是 BaseStep 的钩子方法覆盖，Makefile 中原来分散在
        _step_snapshot 里的 ctx 注入逻辑集中在此处。
        """
        await super()._on_step_done(ctx, result)

        data = result.data if hasattr(result, "data") else result
        snapshot_id = data.get("snapshot_id", "")

        # 注入到管线上下文
        if hasattr(ctx, "kg_snapshot_id"):
            ctx.kg_snapshot_id = snapshot_id

        # 更新结果字典
        if hasattr(ctx, "result") and isinstance(ctx.result, dict):
            ctx.result["kg_snapshot_id"] = snapshot_id

        # 发布消息
        await self._publish_msg(ctx, {"snapshot_id": snapshot_id})
