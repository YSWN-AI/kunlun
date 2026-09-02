"""
昆仑创作引擎 — Makefile 调度员

负责整个章节创作流程的编排：
Snapshot → Architect → Writer → Auditor → (Revise) → Polish → KG Update → Publish

所有步骤实现已迁移到 kunlun/pipeline/steps/ (21 个步骤类)。
Makefile 保留为薄调度层：上下文初始化、检查点管理、步骤编排、NATS 事件驱动管线。
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from loguru import logger

from kunlun.agents.base import AgentMessage, BaseAgent
from kunlun.agents.message_bus import message_bus
from kunlun.audit.gates import GateG4PleasureGap
from kunlun.config import settings
from kunlun.kg.client import kg_client
from kunlun.kg.snapshot import snapshot_manager
from kunlun.pipeline import NodeStatus, pipeline_intervention
from kunlun.pipeline.steps import (
    AuditStep,
    BlueprintStep,
    DraftStep,
    ICUStep,
    IntelSyncStep,
    KGUpdateStep,
    LearnerRecordStep,
    ObserverStep,
    PolishStep,
    PostReflectStep,
    PostWriteValidateStep,
    PublishStep,
    QualityCheckStep,
    ReflectorStep,
    ReviseLoopStep,
    SnapshotStep,
    SocietyRAGStep,
    StateUpdateStep,
    StyleDriftStep,
    TruthAndFingerprintStep,
)
from kunlun.token_tracker import token_tracker


class PipelineStep(StrEnum):
    """旧调度员步骤 — 共 10 步。

    注意：此枚举用于 Makefile 调度员的旧管线（10 步）和 NATS 事件驱动路径。
    新管线请使用 kunlun.pipeline.novel_pipeline.PipelineStep（17 步）。
    """

    BLUEPRINT = "blueprint"
    DRAFT = "draft"
    AUDIT = "audit"
    REVISE = "revise"
    POLISH = "polish"
    USER_REVIEW = "user_review"
    KG_UPDATE = "kg_update"
    PUBLISH = "publish"
    DONE = "done"
    FAILED = "failed"


@dataclass
class PipelineState:
    book_id: str = ""
    chapter_number: int = 0
    current_step: PipelineStep = PipelineStep.BLUEPRINT
    pipeline_id: str = ""
    kg_snapshot_id: str = ""
    blueprint: dict | None = None
    draft: str = ""
    audit_result: dict | None = None
    polished_draft: str = ""
    revision_count: int = 0
    max_revisions: int = 3
    mode: str = "gacha_parallel_3"
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineCheckpoint:
    """管线检查点：持久化中间结果，支持断点续跑"""

    pipeline_id: str
    book_id: str
    chapter: int
    last_completed_step: str = ""
    intermediate_results: dict = field(default_factory=dict)
    timestamp: float = 0.0

    kg_snapshot_id: str = ""
    blueprint: dict | None = None
    draft: str = ""
    audit_result: dict | None = None
    polished_draft: str = ""
    revision_count: int = 0
    society_insights: dict | None = None

    skip_society: bool = False
    skip_icu: bool = False
    skip_revise: bool = False
    chapter_type: str = "normal"
    mode: str = "gacha_parallel_3"
    budget_tier: str = ""


@dataclass
class _PipelineContext:
    """流水线共享状态，减少步骤方法间参数传递"""

    book_id: str
    chapter: int
    mode: str
    pipeline_id: str
    _yield_interval: float
    chapter_type: str
    budget_tier: str
    skip_society: bool
    skip_icu: bool
    skip_revise: bool
    result: dict
    completed_steps: set
    kg_snapshot_id: str = ""
    blueprint: dict = field(default_factory=dict)
    draft: str = ""
    polished_draft: str = ""
    revision_count: int = 0
    audit_result: dict = field(default_factory=dict)
    society_insights: dict = field(default_factory=dict)
    progress_cb: object = None
    learner_cb: object = None
    auditor: object = None


class Makefile(BaseAgent):
    """
    调度员 (Makefile)

    职责: Agent 调度 + 流程控制 + 失败重试 + 进度上报
    创作逻辑全部委托给各专业 Agent 和 pipeline/steps/ 步骤类。
    """

    agent_name = "makefile"
    capabilities = [
        "pipeline_orchestration",
        "chapter_generation_flow",
        "audit_retry_loop",
        "book_creation_flow",
        "book_audit_flow",
        "progress_reporting",
        "pipeline_checkpoint_resume",
    ]

    CHECKPOINT_DIR_NAME = "pipeline_checkpoints"

    def __init__(self, nats_client=None):
        super().__init__(nats_client)
        self._active_pipelines: dict[str, PipelineState] = {}

    @property
    def _checkpoint_dir(self) -> Path:
        p = settings.DATA_DIR / self.CHECKPOINT_DIR_NAME
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _get_checkpoint_path(self, pipeline_id: str) -> Path:
        return self._checkpoint_dir / f"{pipeline_id}.json"

    async def _save_checkpoint(self, pipeline_id: str, step: str, **extra) -> None:
        cp = PipelineCheckpoint(
            pipeline_id=pipeline_id,
            last_completed_step=step,
            timestamp=time.time(),
            **extra,
        )
        try:
            cp_path = self._get_checkpoint_path(pipeline_id)

            def _write():
                cp_path.write_text(
                    json.dumps(cp.__dict__, ensure_ascii=False, default=str),
                    encoding="utf-8",
                )

            await asyncio.to_thread(_write)
            logger.debug(f"[{pipeline_id}] 检查点已保存: {step}")
        except Exception as e:
            logger.exception(f"[{pipeline_id}] 检查点保存失败（非阻塞）: {e}")
            logger.warning(f"[{pipeline_id}] 检查点保存失败（非阻塞）: {e}")

    async def _load_checkpoint(self, pipeline_id: str) -> PipelineCheckpoint | None:
        cp_path = self._get_checkpoint_path(pipeline_id)
        exists = await asyncio.to_thread(cp_path.exists)
        if not exists:
            return None
        try:
            data = await asyncio.to_thread(lambda: json.loads(cp_path.read_text(encoding="utf-8")))
            cp = PipelineCheckpoint(**data)
            if time.time() - cp.timestamp > settings.pipeline_checkpoint_ttl:
                logger.info(f"[{pipeline_id}] 检查点已过期（{cp.last_completed_step}），重新开始")
                await asyncio.to_thread(lambda: cp_path.unlink(missing_ok=True))
                return None
            logger.info(f"[{pipeline_id}] 从检查点恢复: {cp.last_completed_step}")
            return cp
        except Exception as e:
            logger.exception(f"[{pipeline_id}] 检查点加载失败: {e}")
            logger.warning(f"[{pipeline_id}] 检查点加载失败: {e}")
            await asyncio.to_thread(lambda: cp_path.unlink(missing_ok=True))
            return None

    async def _clear_checkpoint(self, pipeline_id: str) -> None:
        cp_path = self._get_checkpoint_path(pipeline_id)
        await asyncio.to_thread(lambda: cp_path.unlink(missing_ok=True))

    async def execute(self, task: dict) -> dict:
        action = task.get("action", "generate_chapter")

        if action == "generate_chapter":
            return await self._run_chapter_pipeline(task)
        if action == "generate_chapter_sync":
            return await self._run_chapter_pipeline_sync(task)
        if action == "generate_chapter_async":
            return await self._run_chapter_pipeline_async(task)
        if action == "resume_chapter_pipeline":
            return await self._run_chapter_pipeline_async(task, resume=True)
        if action == "generate_book":
            return await self._run_book_creation(task)
        if action == "audit_book":
            return await self._run_book_audit(task)
        if action == "publish_chapter":
            return await self._run_publish(task)
        if action == "kg_update_chapter":
            return await self._run_kg_update(task)
        return {"success": False, "error": f"未知动作: {action}"}

    # ─── 单章创作流水线 (NATS 事件驱动入口) ──────────

    async def _run_chapter_pipeline(self, task: dict) -> dict:
        book_id = task["book_id"]
        chapter = task["chapter_number"]
        mode = task.get("mode", "gacha_parallel_3")
        pipeline_id = f"{book_id}_ch{chapter}"

        state = PipelineState(
            book_id=book_id,
            chapter_number=chapter,
            pipeline_id=pipeline_id,
            mode=mode,
        )
        self._active_pipelines[pipeline_id] = state
        logger.info(f"[{pipeline_id}] 流水线启动 (mode={mode})")

        try:
            snapshot = snapshot_manager.create_snapshot(book_id, chapter)
            state.kg_snapshot_id = snapshot.snapshot_id
            logger.info(f"[{pipeline_id}] KG 快照: {state.kg_snapshot_id}")

            state.current_step = PipelineStep.BLUEPRINT
            await self.post_message(
                "architect",
                "GENERATE_BLUEPRINT",
                {
                    "book_id": book_id,
                    "chapter": chapter,
                    "kg_snapshot_id": state.kg_snapshot_id,
                    "kg_summary": snapshot.to_summary(),
                },
                correlation_id=pipeline_id,
                kg_snapshot_id=state.kg_snapshot_id,
            )

            return {
                "success": True,
                "pipeline_id": pipeline_id,
                "status": "running",
                "current_step": state.current_step.value,
            }
        except Exception as e:
            logger.exception(f"[{pipeline_id}] 流水线异常: {e}")
            logger.error(f"[{pipeline_id}] 流水线异常: {e}")
            state.errors.append(str(e))
            state.current_step = PipelineStep.FAILED
            return {"success": False, "error": str(e), "pipeline_id": pipeline_id}

    # ─── 同步单章创作流水线 (供 API 直接调用) ──────────

    async def _run_chapter_pipeline_sync(self, task: dict) -> dict:
        task["_yield_interval"] = 0.001
        return await self._run_chapter_pipeline_async(task)

    # ─── 异步单章创作流水线 (完整 20 步) ──────────────

    # 按执行顺序排列的步骤类列表
    _PIPELINE_STEP_CLASSES: tuple[type, ...] = (
        SnapshotStep,
        BlueprintStep,
        SocietyRAGStep,
        DraftStep,
        PostWriteValidateStep,
        AuditStep,
        ReviseLoopStep,
        ICUStep,
        PolishStep,
        KGUpdateStep,
        ObserverStep,
        ReflectorStep,
        TruthAndFingerprintStep,
        PublishStep,
        LearnerRecordStep,
        StateUpdateStep,
        IntelSyncStep,
        PostReflectStep,
        QualityCheckStep,
        StyleDriftStep,
    )

    async def _run_chapter_pipeline_async(self, task: dict, resume: bool = False) -> dict:
        ctx = await self._init_pipeline_context(task, resume)
        if not ctx:
            return {"success": False, "error": "流水线初始化失败"}

        try:
            for step_cls in self._PIPELINE_STEP_CLASSES:
                ctx = await self._run_step_instance(ctx, step_cls)

            ctx.result["success"] = True
        except Exception as e:
            ctx.result["success"] = False
            ctx.result["error"] = str(e)
            ctx.result["traceback"] = traceback.format_exc()
            logger.error(f"[{ctx.pipeline_id}] 异步流水线异常: {e}\n{traceback.format_exc()}")
            await self._report(ctx, "error", {"error": str(e), "traceback": traceback.format_exc()})
            await message_bus.publish(
                f"kunlun.pipeline.{ctx.pipeline_id}.step",
                {
                    "pipeline_id": ctx.pipeline_id,
                    "step": ctx.result.get("steps", [""])[-1]
                    if ctx.result.get("steps")
                    else "unknown",
                    "status": "error",
                    "data": {"error": str(e)},
                },
            )
            await message_bus.publish(
                f"kunlun.pipeline.{ctx.pipeline_id}.complete",
                {"pipeline_id": ctx.pipeline_id, "status": "error", "data": {"error": str(e)}},
            )

        await self._finalize_pipeline(ctx)
        return ctx.result

    # ── 流水线上下文初始化 ──

    @staticmethod
    def _build_initial_result(
        pipeline_id: str,
        book_id: str,
        chapter: int,
        checkpoint: PipelineCheckpoint | None = None,
    ) -> tuple[dict, str, dict, str, str, int, dict, dict]:
        default_audit = {"passed": True, "gates": {}, "details": ""}
        if checkpoint:
            r = checkpoint.intermediate_results.copy() if checkpoint.intermediate_results else {}
            r.update(success=False)
            for key, default in [
                ("pipeline_id", pipeline_id),
                ("book_id", book_id),
                ("chapter", chapter),
                ("draft", checkpoint.draft or ""),
                ("blueprint", checkpoint.blueprint or {}),
                ("audit_passed", False),
                ("revisions", checkpoint.revision_count),
                ("style_changes", 0),
                (
                    "steps",
                    checkpoint.intermediate_results.get("steps", [])
                    if checkpoint.intermediate_results
                    else [],
                ),
            ]:
                r.setdefault(key, default)
            return (
                r,
                checkpoint.kg_snapshot_id,
                checkpoint.blueprint or {},
                checkpoint.draft or "",
                checkpoint.polished_draft or "",
                checkpoint.revision_count,
                checkpoint.audit_result or default_audit,
                checkpoint.society_insights or {},
            )
        result = {
            "success": False,
            "pipeline_id": pipeline_id,
            "book_id": book_id,
            "chapter": chapter,
            "draft": "",
            "blueprint": {},
            "audit_passed": False,
            "revisions": 0,
            "style_changes": 0,
            "steps": [],
        }
        return (result, "", {}, "", "", 0, default_audit, {})

    async def _init_pipeline_context(self, task: dict, resume: bool) -> _PipelineContext | None:
        book_id = task["book_id"]
        chapter = task["chapter_number"]
        mode = task.get("mode", "gacha_parallel_3")
        pipeline_id = f"{book_id}_ch{chapter}"
        _yield_interval = task.get("_yield_interval", 0.001)
        chapter_type = task.get("chapter_type", "normal")

        checkpoint = None
        completed_steps: set = set()
        if resume:
            checkpoint = await self._load_checkpoint(pipeline_id)
            if checkpoint:
                completed_steps = set(checkpoint.intermediate_results.get("steps", []))
                logger.info(f"[{pipeline_id}] 恢复已完成的步骤: {sorted(completed_steps)}")

        budget_tier = (
            checkpoint.budget_tier
            if checkpoint
            else token_tracker.suggest_tier(mode, chapter_type, is_first_chapter=(chapter == 1))
        )
        token_tracker.init_chapter_budget(pipeline_id, tier=budget_tier)
        logger.info(f"[{pipeline_id}] 预算等级: {budget_tier}")

        if not resume or checkpoint is None:
            try:
                pipeline_intervention.create_pipeline(pipeline_id, book_id, chapter)
            except Exception as e:
                logger.exception(f"[{pipeline_id}] 管线干预初始化跳过: {e}")
                logger.debug(f"[{pipeline_id}] 管线干预初始化跳过: {e}")

        if checkpoint:
            skip_society = checkpoint.skip_society
            skip_icu = checkpoint.skip_icu
            skip_revise = checkpoint.skip_revise
        else:
            skip_society = chapter_type in ("transition",)
            skip_icu = chapter_type in ("transition",)
            skip_revise = chapter_type in ("transition",)

        (
            result,
            kg_snapshot_id,
            blueprint,
            draft,
            polished_draft,
            revision_count,
            audit_result,
            society_insights,
        ) = self._build_initial_result(
            pipeline_id,
            book_id,
            chapter,
            checkpoint,
        )

        await self._save_checkpoint(
            pipeline_id,
            "init",
            book_id=book_id,
            chapter=chapter,
            skip_society=skip_society,
            skip_icu=skip_icu,
            skip_revise=skip_revise,
            chapter_type=chapter_type,
            mode=mode,
            budget_tier=budget_tier,
            intermediate_results=result,
        )

        return _PipelineContext(
            book_id=book_id,
            chapter=chapter,
            mode=mode,
            pipeline_id=pipeline_id,
            _yield_interval=_yield_interval,
            chapter_type=chapter_type,
            budget_tier=budget_tier,
            skip_society=skip_society,
            skip_icu=skip_icu,
            skip_revise=skip_revise,
            result=result,
            completed_steps=completed_steps,
            kg_snapshot_id=kg_snapshot_id,
            blueprint=blueprint,
            draft=draft,
            polished_draft=polished_draft,
            revision_count=revision_count,
            audit_result=audit_result,
            society_insights=society_insights,
            progress_cb=task.get("progress_callback"),
            learner_cb=task.get("learner_callback"),
        )

    # ── 步骤运行器 ──

    async def _run_step_instance(
        self, ctx: _PipelineContext, step_cls: type, **overrides: Any
    ) -> _PipelineContext:
        """实例化步骤类并执行，委托给 pipeline/steps/ 中的实现。

        步骤类自行处理检查点跳过、计时、进度上报、错误恢复。
        Makefile 仅负责保存检查点和事件循环 yield。
        """
        step = step_cls(makefile=self)
        name = step.step_name

        if name in ctx.completed_steps:
            logger.info(f"[{ctx.pipeline_id}] 跳过{name}（已从检查点恢复）")
            await asyncio.sleep(ctx._yield_interval)
            return ctx

        await self._report(ctx, f"{name}_start")
        await step.execute(ctx)
        await self._report(ctx, f"{name}_done")

        await self._save_step_checkpoint(ctx, name, **overrides)
        await asyncio.sleep(ctx._yield_interval)
        return ctx

    # ── 步骤保存辅助 ──

    async def _save_step_checkpoint(self, ctx: _PipelineContext, step: str, **overrides) -> None:
        kwargs = {
            "book_id": ctx.book_id,
            "chapter": ctx.chapter,
            "kg_snapshot_id": ctx.kg_snapshot_id,
            "blueprint": ctx.result.get("blueprint", {}),
            "draft": ctx.polished_draft or ctx.draft,
            "polished_draft": ctx.polished_draft,
            "audit_result": ctx.audit_result,
            "revision_count": ctx.revision_count,
            "skip_society": ctx.skip_society,
            "skip_icu": ctx.skip_icu,
            "skip_revise": ctx.skip_revise,
            "chapter_type": ctx.chapter_type,
            "mode": ctx.mode,
            "budget_tier": ctx.budget_tier,
            "intermediate_results": ctx.result,
            "society_insights": ctx.society_insights,
        }
        kwargs.update(overrides)
        await self._save_checkpoint(ctx.pipeline_id, step, **kwargs)

    async def _report(self, ctx: _PipelineContext, step: str, data=None) -> None:
        if ctx.progress_cb:
            await ctx.progress_cb(step, data)

    async def _learn(self, ctx: _PipelineContext, event_type: str, data=None) -> None:
        if ctx.learner_cb:
            await ctx.learner_cb(event_type, data)

    async def _do_publish(self, ctx: _PipelineContext) -> dict:
        await self._report(ctx, "publish_start")
        pub_result = await self._run_publish(
            {
                "book_id": ctx.book_id,
                "chapter": ctx.chapter,
                "draft": ctx.polished_draft,
            }
        )
        path = pub_result.get("path", "")
        ctx.result["published_path"] = path
        ctx.result["word_count"] = len(ctx.polished_draft)
        ctx.result["success"] = True
        await self._report(ctx, "publish_done", {"path": path})
        await message_bus.publish(
            f"kunlun.pipeline.{ctx.pipeline_id}.step",
            {
                "pipeline_id": ctx.pipeline_id,
                "step": "publish",
                "status": "done",
                "data": {"path": path, "word_count": len(ctx.polished_draft)},
            },
        )
        await message_bus.publish(
            f"kunlun.pipeline.{ctx.pipeline_id}.complete",
            {
                "pipeline_id": ctx.pipeline_id,
                "status": "done",
                "data": {"word_count": len(ctx.polished_draft), "path": path},
            },
        )
        return pub_result

    async def _finalize_pipeline(self, ctx: _PipelineContext) -> None:
        with contextlib.suppress(Exception):
            token_tracker.close_budget(ctx.pipeline_id)
        try:
            pipeline_intervention.advance_node(
                ctx.pipeline_id,
                f"{ctx.pipeline_id}_publish",
                NodeStatus.SUCCESS if ctx.result.get("success") else NodeStatus.FAILED,
                {"result": ctx.result},
            )
        except Exception as e_pi:
            logger.exception(f"[{ctx.pipeline_id}] 管线干预结束失败（非阻塞）: {e_pi}")
            logger.debug(f"[{ctx.pipeline_id}] 管线干预结束失败（非阻塞）: {e_pi}")
        if ctx.result.get("success"):
            await self._clear_checkpoint(ctx.pipeline_id)
        else:
            logger.info(f"[{ctx.pipeline_id}] 流水线未完成，检查点已保留（供断点续跑）")

    # ─── 建书流程 ─────────────────────────────────────

    async def _run_book_creation(self, task: dict) -> dict:
        book_id = task["book_id"]
        seed = task.get("seed", {})
        results = {}

        try:
            title = seed.get("title", book_id)
            worldview = seed.get("worldview", "")

            kg_client.query_cypher(
                "CREATE (b:Book {uid: $id, title: $title, "
                "worldview: $worldview, createdAt: datetime()})",
                {"id": book_id, "title": title, "worldview": worldview},
            )

            for char in seed.get("characters", []):
                kg_client.query_cypher(
                    """CREATE (c:Character {
                        uid: $uid, name: $name, type: $type,
                        description: $description, status: 'alive'
                    })
                    WITH c
                    MATCH (b:Book {uid: $book_id})
                    CREATE (b)-[:HAS_CHARACTER]->(c)
                    """,
                    {
                        "uid": f"{book_id}_{char['name']}",
                        "name": char["name"],
                        "type": char.get("type", "supporting"),
                        "description": char.get("description", ""),
                        "book_id": book_id,
                    },
                )

            for i, outline in enumerate(seed.get("outline", [])):
                kg_client.query_cypher(
                    """CREATE (ch:Chapter {uid: $uid, chapterNumber: $num,
                    outline: $outline, status: 'planned'})
                    WITH ch
                    MATCH (b:Book {uid: $book_id})
                    CREATE (b)-[:HAS_CHAPTER]->(ch)
                    """,
                    {
                        "uid": f"{book_id}_ch{i + 1}",
                        "num": i + 1,
                        "outline": outline,
                        "book_id": book_id,
                    },
                )
            results["chapters_created"] = len(seed.get("outline", []))

            results["success"] = True
            results["message"] = f"建书完成: {title}"
            logger.info(f"建书完成: {book_id}")
        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            logger.exception(f"[Makefile] 建书失败: {e}")
            logger.error(f"建书失败: {e}")

        return results

    # ─── 全书审计 ─────────────────────────────────────

    async def _run_book_audit(self, task: dict) -> dict:
        book_id = task["book_id"]
        results = {"book_id": book_id, "issues": []}

        try:
            overdue = kg_client.query_cypher(
                """
                MATCH (f:Foreshadowing)
                WHERE f.status = 'planted' AND f.book_id = $book_id
                RETURN f.name AS name, f.expectedRevealChapter AS expected,
                       f.priority AS priority, f.chapterCreated AS created
                ORDER BY f.priority DESC
                """,
                {"book_id": book_id},
            )
            if overdue:
                results["issues"].append(
                    {
                        "type": "overdue_foreshadowing",
                        "count": len(overdue),
                        "details": overdue,
                    }
                )

            all_characters = kg_client.query_cypher(
                """
                MATCH (b:Book {uid: $book_id})-[:HAS_CHARACTER]->(c:Character)
                OPTIONAL MATCH (c)-[r:APPEARS_IN]->(ch:Chapter)
                WITH c, count(r) AS appearance_count
                RETURN c.name AS name, c.type AS type, appearance_count
                ORDER BY appearance_count ASC
                """,
                {"book_id": book_id},
            )
            unused = [c for c in all_characters if c["appearance_count"] == 0]
            if unused:
                results["issues"].append(
                    {
                        "type": "unused_characters",
                        "count": len(unused),
                        "characters": [c["name"] for c in unused],
                    }
                )

            chapter_count = kg_client.query_cypher(
                "MATCH (b:Book {uid: $book_id})"
                "-[:HAS_CHAPTER]->(ch:Chapter) "
                "RETURN count(ch) AS count",
                {"book_id": book_id},
            )
            results["chapter_count"] = chapter_count[0]["count"] if chapter_count else 0

            results["success"] = True
            results["message"] = f"全书审计完成 (发现 {len(results['issues'])} 类问题)"
        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            logger.exception(f"[Makefile] 全书审计失败: {e}")

        return results

    # ─── KG 更新 ──────────────────────────────────────

    async def _run_kg_update(self, task: dict) -> dict:
        book_id = task["book_id"]
        chapter = task.get("chapter", 0)
        blueprint = task.get("blueprint", {})
        draft = task.get("draft", "")

        results = {"updated": []}

        try:
            kg_client.query_cypher(
                """MERGE (ch:Chapter {uid: $uid})
                SET ch.status = 'written',
                    ch.contentPreview = $preview,
                    ch.wordCount = $wc,
                    ch.writtenAt = datetime()
                """,
                {
                    "uid": f"{book_id}_ch{chapter}",
                    "preview": draft[:200] if draft else "",
                    "wc": len(draft) if draft else 0,
                },
            )
            results["updated"].append("chapter_status")

            fp = blueprint.get("foreshadowing", {})
            for reveal_name in fp.get("to_reveal", []):
                kg_client.query_cypher(
                    "MATCH (f:Foreshadowing {name: $name}) "
                    "SET f.status = 'revealed', f.revealedChapter = $chapter",
                    {"name": reveal_name, "chapter": chapter},
                )
                results["updated"].append(f"foreshadowing_revealed:{reveal_name}")
            for plant_name in fp.get("to_plant", []):
                kg_client.query_cypher(
                    """CREATE (f:Foreshadowing {
                        uid: $uid, name: $name, status: 'planted',
                        chapterCreated: $chapter, book_id: $book_id, priority: 'medium'
                    })""",
                    {
                        "uid": f"{book_id}_fp_{plant_name}",
                        "name": plant_name,
                        "chapter": chapter,
                        "book_id": book_id,
                    },
                )
                results["updated"].append(f"foreshadowing_planted:{plant_name}")

            if draft:
                kg_client.index_chapter_vector(book_id, chapter, draft)
                results["updated"].append("vector_index")

            try:
                g4 = GateG4PleasureGap()
                all_kw = [kw for sublist in g4.PLEASURE_KEYWORDS.values() for kw in sublist]
                pleasure_found = [kw for kw in all_kw if kw in draft]
                if pleasure_found:
                    for kw in pleasure_found[:5]:
                        pp_uid = f"{book_id}_ch{chapter}_pleasure_{kw}"
                        kg_client.query_cypher(
                            """MERGE (pp:PleasurePoint {uid: $uid})
                            SET pp.keyword = $kw, pp.chapter = $chapter,
                                pp.book_id = $book_id, pp.createdAt = datetime()
                            """,
                            {"uid": pp_uid, "kw": kw, "chapter": chapter, "book_id": book_id},
                        )
                    results["updated"].append(f"pleasure_points:{len(pleasure_found)}")
            except Exception as e:
                logger.exception(f"[KG] PleasurePoint 创建失败: {e}")
                logger.warning(f"[KG] PleasurePoint 创建失败: {e}")

            results["success"] = True
            logger.info(f"KG 更新完成: ch{chapter} ({len(results['updated'])} 项)")
        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            logger.exception(f"[KG] KG更新失败: {e}")
            logger.error(f"KG 更新失败: {e}")

        return results

    # ─── 发布 ─────────────────────────────────────────

    async def _run_publish(self, task: dict) -> dict:
        book_id = task["book_id"]
        chapter = task.get("chapter", 0)
        draft = task.get("draft", "")

        output_dir = settings.DATA_DIR / "published" / book_id
        fname = output_dir / f"ch{chapter:04d}.txt"

        def _write_publish():
            output_dir.mkdir(parents=True, exist_ok=True)
            fname.write_text(draft, encoding="utf-8")

        await asyncio.to_thread(_write_publish)

        logger.info(f"发布完成: {fname}")
        return {
            "success": True,
            "path": str(fname),
            "chapter": chapter,
            "word_count": len(draft),
        }

    # ─── NATS 事件驱动管线回调 ────────────────────────

    async def _handle_blueprint_ready(
        self,
        state: PipelineState,
        msg: AgentMessage,
        pipeline_id: str,
    ) -> None:
        state.blueprint = msg.payload.get("blueprint")
        state.current_step = PipelineStep.DRAFT
        await self.post_message(
            "writer",
            "GENERATE_DRAFT",
            {
                "book_id": state.book_id,
                "chapter": state.chapter_number,
                "blueprint": state.blueprint,
                "mode": state.mode,
                "kg_snapshot_id": state.kg_snapshot_id,
            },
            correlation_id=pipeline_id,
            kg_snapshot_id=state.kg_snapshot_id,
        )

    async def _handle_draft_ready(
        self,
        state: PipelineState,
        msg: AgentMessage,
        pipeline_id: str,
    ) -> None:
        state.draft = msg.payload.get("draft", "")
        state.current_step = PipelineStep.AUDIT
        await self.post_message(
            "auditor",
            "RUN_AUDIT",
            {
                "draft": state.draft,
                "blueprint": {"chapter": state.chapter_number},
                "kg_snapshot_id": state.kg_snapshot_id,
            },
            correlation_id=pipeline_id,
            kg_snapshot_id=state.kg_snapshot_id,
        )

    async def _handle_audit_result(
        self,
        state: PipelineState,
        msg: AgentMessage,
        pipeline_id: str,
    ) -> None:
        audit = msg.payload.get("audit_result", {})
        state.audit_result = audit

        if audit.get("passed", False):
            state.current_step = PipelineStep.POLISH
            await self.post_message(
                "style_engineer",
                "POLISH",
                {"draft": state.draft},
                correlation_id=pipeline_id,
            )
        elif state.revision_count < state.max_revisions:
            state.revision_count += 1
            state.current_step = PipelineStep.REVISE
            await self.post_message(
                "writer",
                "REVISE",
                {"draft": state.draft, "audit_report": audit, "book_id": state.book_id},
                correlation_id=pipeline_id,
            )
        else:
            logger.error(f"[{pipeline_id}] 审计循环耗尽 ({state.max_revisions} 轮)")
            state.current_step = PipelineStep.FAILED
            self._active_pipelines.pop(pipeline_id, None)

    async def _handle_polish_done(
        self,
        state: PipelineState,
        msg: AgentMessage,
        pipeline_id: str,
    ) -> None:
        state.polished_draft = msg.payload.get("polished_draft", state.draft)
        state.current_step = PipelineStep.KG_UPDATE

        kg_result = await self._run_kg_update(
            {
                "book_id": state.book_id,
                "chapter": state.chapter_number,
                "blueprint": state.blueprint,
                "draft": state.polished_draft,
            }
        )

        if kg_result.get("success"):
            state.current_step = PipelineStep.PUBLISH
            pub_result = await self._run_publish(
                {
                    "book_id": state.book_id,
                    "chapter": state.chapter_number,
                    "draft": state.polished_draft,
                }
            )
            if pub_result.get("success"):
                state.current_step = PipelineStep.DONE
                logger.info(f"[{pipeline_id}] 流水线完成: {pub_result.get('path')}")
            else:
                state.current_step = PipelineStep.FAILED
                state.errors.append(f"PUBLISH_FAILED: {pub_result.get('error')}")
        else:
            state.current_step = PipelineStep.FAILED
            state.errors.append(f"KG_UPDATE_FAILED: {kg_result.get('error')}")

        self._active_pipelines.pop(pipeline_id, None)

    async def on_message(self, msg: AgentMessage) -> AgentMessage | None:
        pipeline_id = msg.correlation_id
        state = self._active_pipelines.get(pipeline_id)

        if not state:
            if msg.msg_type == "BLUEPRINT_READY":
                bp = msg.payload.get("blueprint", {})
                state = PipelineState(
                    book_id=pipeline_id.rsplit("_ch", 1)[0]
                    if "_ch" in pipeline_id
                    else pipeline_id,
                    chapter_number=bp.get("chapter", 1),
                    pipeline_id=pipeline_id,
                )
                self._active_pipelines[pipeline_id] = state
            else:
                return None

        _dispatch: dict[str, Callable[..., Any]] = {
            "BLUEPRINT_READY": self._handle_blueprint_ready,
            "DRAFT_READY": self._handle_draft_ready,
            "AUDIT_RESULT": self._handle_audit_result,
            "POLISH_DONE": self._handle_polish_done,
        }
        handler = _dispatch.get(msg.msg_type)
        if handler:
            await handler(state, msg, pipeline_id)

        return None
