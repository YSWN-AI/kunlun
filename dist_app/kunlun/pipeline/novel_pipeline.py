"""
昆仑创作引擎 — 共享小说创作管线

设计目标: 消除 Editor(8步) 和 Makefile(13步) 之间的代码重复。

用法:
    # 完整管线（13步）— 新书/关键章
    pipeline = NovelPipeline(book_id, chapter, mode="full")
    result = await pipeline.run()

    # 快速管线（6步）— 日常更新章
    pipeline = NovelPipeline(book_id, chapter, mode="quick")
    result = await pipeline.run()
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from loguru import logger


class PipelineStep(StrEnum):
    """管线步骤 — 共 17 步，六大驱动力全覆盖。

    注意：此枚举不同于 kunlun.agents.makefile.PipelineStep（10 步，旧调度员用）。
    本枚举是 NovelPipeline 的权威步骤定义，包含完整的 17 步链路。
    """

    SNAPSHOT = "snapshot"  # KG快照
    PLANNER = "planner"  # 章节意图规划
    ARCHITECT = "architect"  # 蓝图生成（含冲突/氛围规划）
    SOCIETY = "society"  # 社会推演
    WRITER = "writer"  # 正文生成（Gacha + Vibe注入）
    CONFLICT = "conflict"  # 冲突追踪（冲突驱动 #4）
    VIBE = "vibe"  # 氛围追踪（Vibe Writing #6）
    POST_WRITE = "post_write"  # 后写验证（零LLM成本，InkOS 11条规则）
    AUDIT = "audit"  # 审计（33维/8门禁）
    REVISE = "revise"  # 修订循环
    ICU = "icu"  # 连载ICU检查
    QUALITY = "quality"  # 质量看板（零LLM，可执行化结果）
    POLISH = "polish"  # 去AI味润色
    KG_UPDATE = "kg_update"  # KG更新
    PLEASURE = "pleasure"  # 爽点追踪
    TRUTH_SYNC = "truth_sync"  # 真相文件同步
    REFLECT = "reflect"  # 写后反思


# ── 管线模式定义 ────────────────────────────────────


@dataclass
class PipelineMode:
    """管线模式：定义启用的步骤和参数"""

    name: str
    steps: list[PipelineStep]
    description: str = ""


PIPELINE_MODES = {
    "full": PipelineMode(
        name="full",
        steps=[
            PipelineStep.SNAPSHOT,
            PipelineStep.PLANNER,
            PipelineStep.ARCHITECT,
            PipelineStep.SOCIETY,
            PipelineStep.WRITER,
            PipelineStep.CONFLICT,  # 冲突驱动追踪
            PipelineStep.VIBE,  # Vibe Writing追踪
            PipelineStep.POST_WRITE,
            PipelineStep.AUDIT,
            PipelineStep.REVISE,
            PipelineStep.ICU,
            PipelineStep.POLISH,
            PipelineStep.QUALITY,
            PipelineStep.KG_UPDATE,
            PipelineStep.PLEASURE,
            PipelineStep.TRUTH_SYNC,
            PipelineStep.REFLECT,
        ],
        description="完整17步管线：六大驱动力全覆盖",
    ),
    "standard": PipelineMode(
        name="standard",
        steps=[
            PipelineStep.SNAPSHOT,
            PipelineStep.ARCHITECT,
            PipelineStep.SOCIETY,
            PipelineStep.WRITER,
            PipelineStep.CONFLICT,  # 冲突驱动追踪
            PipelineStep.VIBE,  # Vibe Writing追踪
            PipelineStep.POST_WRITE,
            PipelineStep.AUDIT,
            PipelineStep.REVISE,
            PipelineStep.ICU,
            PipelineStep.POLISH,
            PipelineStep.QUALITY,
            PipelineStep.KG_UPDATE,
            PipelineStep.TRUTH_SYNC,
        ],
        description="标准14步管线：含冲突+Vibe追踪",
    ),
    "quick": PipelineMode(
        name="quick",
        steps=[
            PipelineStep.ARCHITECT,
            PipelineStep.WRITER,
            PipelineStep.CONFLICT,  # 冲突驱动追踪
            PipelineStep.VIBE,  # Vibe Writing追踪
            PipelineStep.POST_WRITE,
            PipelineStep.AUDIT,
            PipelineStep.POLISH,
            PipelineStep.QUALITY,
            PipelineStep.KG_UPDATE,
            PipelineStep.TRUTH_SYNC,
        ],
        description="快速10步管线：含冲突+Vibe追踪",
    ),
    "editor": PipelineMode(
        name="editor",
        steps=[
            PipelineStep.PLANNER,
            PipelineStep.ARCHITECT,
            PipelineStep.WRITER,
            PipelineStep.CONFLICT,  # 冲突驱动追踪
            PipelineStep.VIBE,  # Vibe Writing追踪
            PipelineStep.POST_WRITE,
            PipelineStep.AUDIT,
            PipelineStep.REVISE,
            PipelineStep.POLISH,
            PipelineStep.QUALITY,
            PipelineStep.KG_UPDATE,
            PipelineStep.TRUTH_SYNC,
        ],
        description="Editor兼容12步管线：含冲突+Vibe追踪",
    ),
}


@dataclass
class PipelineContext:
    """管线上下文（跨步骤共享数据）"""

    book_id: str
    chapter: int
    mode: str
    pipeline_id: str

    # 步骤产出
    kg_snapshot_id: str = ""
    blueprint: dict = field(default_factory=dict)
    society_insights: dict = field(default_factory=dict)
    draft: str = ""
    post_write_result: dict = field(default_factory=dict)  # InkOS 11条零LLM后写验证
    quality_report: dict = field(default_factory=dict)  # 质量看板（可执行结果）
    audit_passed: bool = False

    # 六大驱动力集成（运行时状态）
    conflict_report: dict = field(default_factory=dict)  # 冲突追踪结果
    vibe_report: dict = field(default_factory=dict)  # 氛围追踪结果
    audit_report: dict = field(default_factory=dict)
    revision_count: int = 0
    icu_report: dict = field(default_factory=dict)
    polished_draft: str = ""
    kg_update_result: dict = field(default_factory=dict)
    reflect_result: dict = field(default_factory=dict)

    # 进度回调
    progress_callback: Callable | None = None

    async def report(self, step: str, data: dict | None = None):
        """报告进度"""
        if self.progress_callback:
            await self.progress_callback(step, data or {})


class NovelPipeline:
    """
    共享小说创作管线

    统一 EditorInChief (8步) 和 Makefile (13步) 的管线定义。
    通过 PipelineMode 选择启用的步骤组合。

    用法:
        ctx = PipelineContext(book_id="my_book", chapter=5, mode="standard")
        pipeline = NovelPipeline(ctx)
        result = await pipeline.run()
    """

    def __init__(self, ctx: PipelineContext):
        self.ctx = ctx
        mode_cfg = PIPELINE_MODES.get(ctx.mode, PIPELINE_MODES["standard"])
        self.steps = mode_cfg.steps
        logger.info(f"[Pipeline] 初始化: {ctx.mode}模式 ({len(self.steps)}步)")

    async def run(self) -> dict:
        """按顺序执行配置的管线步骤"""
        ctx = self.ctx
        await ctx.report("pipeline_start", {"mode": ctx.mode, "steps": len(self.steps)})

        for step in self.steps:
            await ctx.report(f"{step.value}_start")
            try:
                handler = self._get_handler(step)
                if handler:
                    await handler(ctx)
                await ctx.report(f"{step.value}_done")
            except Exception as e:
                logger.error(f"[Pipeline] {step.value} 失败: {e}")
                await ctx.report(f"{step.value}_error", {"error": str(e)})
                # 关键步骤失败中断管线：蓝图/WRITER/审计失败时继续会产生垃圾输出
                if step in (PipelineStep.ARCHITECT, PipelineStep.WRITER, PipelineStep.AUDIT):
                    return {"success": False, "error": str(e), "failed_step": step.value}
            await asyncio.sleep(0.001)

        await ctx.report("pipeline_done", {"success": True})
        return self._build_result(ctx)

    def _get_handler(self, step: PipelineStep) -> Callable | None:
        """获取步骤处理器"""
        handlers = {
            PipelineStep.SNAPSHOT: self._step_snapshot,
            PipelineStep.PLANNER: self._step_planner,
            PipelineStep.ARCHITECT: self._step_architect,
            PipelineStep.SOCIETY: self._step_society,
            PipelineStep.WRITER: self._step_writer,
            PipelineStep.CONFLICT: self._step_conflict,
            PipelineStep.VIBE: self._step_vibe,
            PipelineStep.POST_WRITE: self._step_post_write,
            PipelineStep.AUDIT: self._step_audit,
            PipelineStep.REVISE: self._step_revise,
            PipelineStep.ICU: self._step_icu,
            PipelineStep.QUALITY: self._step_quality,
            PipelineStep.POLISH: self._step_polish,
            PipelineStep.KG_UPDATE: self._step_kg_update,
            PipelineStep.PLEASURE: self._step_pleasure,
            PipelineStep.TRUTH_SYNC: self._step_truth_sync,
            PipelineStep.REFLECT: self._step_reflect,
        }
        return handlers.get(step)

    @staticmethod
    def _build_result(ctx: PipelineContext) -> dict:
        return {
            "success": True,
            "pipeline_id": ctx.pipeline_id,
            "book_id": ctx.book_id,
            "chapter": ctx.chapter,
            "mode": ctx.mode,
            "draft": ctx.polished_draft or ctx.draft,
            "blueprint": ctx.blueprint,
            "audit_passed": ctx.audit_passed,
            "revisions": ctx.revision_count,
            "kg_snapshot_id": ctx.kg_snapshot_id,
            "reflect": ctx.reflect_result,
        }

    # ── 各步骤处理器 ──（委托给现有模块，不重新实现）──

    @staticmethod
    async def _step_snapshot(ctx: PipelineContext):
        from kunlun.kg.snapshot import snapshot_manager

        snap = snapshot_manager.create_snapshot(ctx.book_id, ctx.chapter)
        ctx.kg_snapshot_id = snap.snapshot_id

    @staticmethod
    async def _step_planner(ctx: PipelineContext):
        """章节意图规划（Editor独有，Makefile可忽略）"""
        # 委托给 EditorInChief 的规划方法
        try:
            from kunlun.agents.editor import EditorInChief

            eic = EditorInChief(ctx.book_id)
            if hasattr(eic, "_plan_chapter_intent"):
                intent = await eic._plan_chapter_intent(ctx.chapter, "", 3000)
                ctx.blueprint["chapter_intent"] = (
                    intent.__dict__ if hasattr(intent, "__dict__") else {}
                )
        except Exception as e:
            logger.debug(f"[Pipeline] Planner跳过: {e}")

    @staticmethod
    async def _step_architect(ctx: PipelineContext):
        from kunlun.agents.architect import Architect

        arch = Architect()
        result = await arch.execute(
            {
                "book_id": ctx.book_id,
                "chapter": ctx.chapter,
                "kg_snapshot_id": ctx.kg_snapshot_id,
                "chapter_type": ctx.blueprint.get("chapter_type", "normal"),
            }
        )
        ctx.blueprint = result.get("blueprint", result)

    @staticmethod
    async def _step_society(ctx: PipelineContext):
        from kunlun.agents.makefile import Makefile

        mf = Makefile()
        if hasattr(mf, "_run_society_deduce"):
            insights = await mf._run_society_deduce(
                {
                    "book_id": ctx.book_id,
                    "chapter": ctx.chapter,
                    "blueprint": ctx.blueprint,
                }
            )
            ctx.society_insights = insights or {}

    @staticmethod
    async def _step_writer(ctx: PipelineContext):
        from kunlun.agents.writer import Writer

        writer = Writer()
        result = await writer._generate(
            {
                "blueprint": ctx.blueprint,
                "mode": ctx.blueprint.get("mode", "gacha_cascade"),
                "kg_snapshot_id": ctx.kg_snapshot_id,
            }
        )
        ctx.draft = result.get("draft", "")

    @staticmethod
    async def _step_conflict(ctx: PipelineContext):
        """冲突驱动追踪（Conflict Driven #4）

        从草稿中检测冲突表现，更新冲突管理器的张力记录。
        与 conflict/ 模块联动，生成冲突热力图数据。
        """
        draft = ctx.polished_draft or ctx.draft
        if not draft or not ctx.book_id:
            return
        try:
            from kunlun.conflict import get_conflict_manager
            from kunlun.conflict.engine import ConflictType

            cm = get_conflict_manager(ctx.book_id)

            # 从蓝图中提取冲突设计
            blueprint = ctx.blueprint or {}
            conflict_marks = blueprint.get("conflicts", [])

            if not conflict_marks:
                # 自动检测冲突关键词
                conflict_keywords = {
                    "战斗": 7,
                    "对抗": 6,
                    "争执": 5,
                    "对峙": 6,
                    "冲突": 5,
                    "矛盾": 4,
                    "危机": 7,
                    "决战": 9,
                }
                for keyword in conflict_keywords:
                    if keyword in draft:
                        cm.register_conflict(
                            keyword,
                            ConflictType.PERSON_VS_PERSON,
                            participants=[],
                            chapter=ctx.chapter,
                        )
                        cm.analyze_chapter(draft, ctx.chapter)

            ctx.conflict_report = {"active_conflicts": len(cm.conflicts)}
        except Exception as e:
            logger.debug(f"[Pipeline] 冲突追踪跳过: {e}")

    @staticmethod
    async def _step_vibe(ctx: PipelineContext):
        """Vibe Writing 氛围追踪（Vibe Writing #6）

        从草稿和蓝图中提取氛围特征，更新Vibe引擎。
        为Writer prompt注入场景氛围提示词。
        """
        draft = ctx.polished_draft or ctx.draft
        if not draft or not ctx.book_id:
            return
        try:
            from kunlun.style.vibe import VibeType, get_vibe_engine

            ve = get_vibe_engine(ctx.book_id)

            # 从蓝图中提取场景氛围规划
            blueprint = ctx.blueprint or {}
            scenes = blueprint.get("scenes", [])
            emotion_curve = blueprint.get("emotion_curve", {})

            if scenes:
                for i, scene in enumerate(scenes):
                    vibe_str = scene.get("vibe", "") or scene.get("emotion", "")
                    if vibe_str:
                        try:
                            vibe_type = VibeType(vibe_str)
                            ve.register_scene_vibe(
                                chapter=ctx.chapter,
                                scene_index=i,
                                primary_vibe=vibe_type,
                                intensity=scene.get("intensity", 0.5),
                                description=scene.get("summary", ""),
                            )
                        except ValueError:
                            pass
            else:
                # 无场景规划时从情绪曲线推断
                start_emotion = emotion_curve.get("start_emotion", "")
                if start_emotion:
                    vibe_map = {
                        "tension": VibeType.TENSE,
                        "excitement": VibeType.JOYOUS,
                        "fear": VibeType.DARK,
                        "sadness": VibeType.MELANCHOLY,
                        "surprise": VibeType.MYSTERIOUS,
                    }
                    vibe_type = vibe_map.get(start_emotion, VibeType.TENSE)
                    ve.register_scene_vibe(
                        chapter=ctx.chapter,
                        scene_index=0,
                        primary_vibe=vibe_type,
                        intensity=0.6,
                    )

            ctx.vibe_report = {
                "chapter_vibe": ve.get_chapter_vibe(ctx.chapter),
                "vibe_arc": ve.get_vibe_arc()[-5:],
                "transition_suggestions": ve.suggest_vibe_transition(ctx.chapter - 1),
            }
        except Exception as e:
            logger.debug(f"[Pipeline] Vibe追踪跳过: {e}")

    @staticmethod
    async def _step_post_write(ctx: PipelineContext):
        """后写验证（零LLM成本，InkOS 11条规则 + Novel-OS 确定性检查）

        在审计之前运行，免费捕获 80% 常见写作问题。
        """
        if not ctx.draft:
            return
        try:
            from kunlun.audit.post_write_validator import post_write_validator

            result = post_write_validator.validate(ctx.draft)
            ctx.post_write_result = {
                "passed": result.passed,
                "score": result.overall_score,
                "critical_issues": result.critical_issues,
                "warnings": result.warnings,
            }
            if not ctx.post_write_result["passed"]:
                logger.warning(
                    f"[Pipeline] 后写验证未通过: "
                    f"{len(ctx.post_write_result['critical_issues'])}个关键问题"
                )
        except Exception as e:
            logger.debug(f"[Pipeline] 后写验证跳过: {e}")

    @staticmethod
    async def _step_audit(ctx: PipelineContext):
        if not ctx.draft:
            return
        from kunlun.audit.audit33 import auditor33

        report33 = auditor33.run_audit(ctx.draft, ctx.chapter, ctx.blueprint, ctx.book_id)
        ctx.audit_passed = report33.passed
        ctx.audit_report = {
            "passed": report33.passed,
            "overall_score": report33.overall_score,
            "ai_detection_score": report33.ai_detection_score,
        }

    @staticmethod
    async def _step_revise(ctx: PipelineContext):
        if ctx.audit_passed or not ctx.draft:
            return
        from kunlun.agents.writer import Writer

        writer = Writer()
        for i in range(3):
            if ctx.audit_passed:
                break
            result = await writer._revise(
                {
                    "draft": ctx.draft,
                    "audit_report": ctx.audit_report,
                    "book_id": ctx.book_id,
                }
            )
            ctx.draft = result.get("draft", ctx.draft)
            ctx.revision_count = i + 1
            # 重新审计
            from kunlun.audit.audit33 import auditor33

            report = auditor33.run_audit(ctx.draft, ctx.chapter, ctx.blueprint, ctx.book_id)
            ctx.audit_passed = report.passed
            ctx.audit_report["passed"] = report.passed

    @staticmethod
    async def _step_icu(ctx: PipelineContext):
        draft = ctx.polished_draft or ctx.draft
        if not draft:
            return
        from kunlun.audit.icu import icu_system

        icu_report, icu_draft = await icu_system.run_full_check(
            draft, ctx.chapter, chapter_type="normal", auto_fix=True
        )
        if icu_report.passed:
            ctx.draft = icu_draft
        ctx.icu_report = {
            "score": icu_report.overall_score,
            "issues": len(icu_report.critical_issues),
        }

    @staticmethod
    async def _step_quality(ctx: PipelineContext):
        """质量看板（零LLM成本，可执行结果）

        聚合AI特征检测、后写验证、精炼统计 → 统一质量评分。
        - score >= 0.70: pass ✅
        - score >= 0.50: revise ⚠️
        - score >= 0.30: review 🔍（需人工检查）
        - score < 0.30:  reject ❌（需重写）
        """
        draft = ctx.polished_draft or ctx.draft
        if not draft:
            return
        try:
            from kunlun.quality import QualityEvaluator

            evaluator = QualityEvaluator()
            report = evaluator.evaluate(draft, chapter_number=ctx.chapter)
            ctx.quality_report = report.to_dict()
            action = ctx.quality_report.get("action", "pass")
            score = ctx.quality_report.get("overall_score", 0.5)

            if action == "reject":
                logger.warning(f"[Pipeline] 质量看板: 拒绝 (score={score:.2f}) — 建议人工审核")
                ctx.quality_report["pipeline_action"] = "需人工审核"
            elif action == "review":
                logger.info(f"[Pipeline] 质量看板: 需审查 (score={score:.2f})")
                ctx.quality_report["pipeline_action"] = "标记审查"
            elif action == "revise":
                logger.info(f"[Pipeline] 质量看板: 建议修订 (score={score:.2f})")
                ctx.quality_report["pipeline_action"] = "建议修订"
            else:
                logger.info(f"[Pipeline] 质量看板: 通过 ✅ (score={score:.2f})")
                ctx.quality_report["pipeline_action"] = "通过"
        except Exception as e:
            logger.debug(f"[Pipeline] 质量看板跳过: {e}")

    @staticmethod
    async def _step_polish(ctx: PipelineContext):
        draft = ctx.polished_draft or ctx.draft
        if not draft:
            return
        from kunlun.agents.makefile import Makefile

        mf = Makefile()
        if hasattr(mf, "_run_polish"):
            polished = await mf._run_polish(draft)
            ctx.polished_draft = polished.get("polished_draft", draft)
        else:
            from kunlun.style.engineer import StyleEngineer

            result = await StyleEngineer().execute({"draft": draft})
            ctx.polished_draft = result.get("polished_draft", draft)

    @staticmethod
    async def _step_kg_update(ctx: PipelineContext):
        from kunlun.kg.client import kg_client

        draft = ctx.polished_draft or ctx.draft
        if draft:
            kg_client.query_cypher(
                """MERGE (ch:Chapter {uid: $uid})
                SET ch.status = 'written', ch.wordCount = $wc""",
                {"uid": f"{ctx.book_id}_ch{ctx.chapter}", "wc": len(draft)},
            )

    @staticmethod
    async def _step_pleasure(ctx: PipelineContext):
        """爽点追踪 — 委托给 pleasure 模块"""
        try:
            from kunlun.pleasure import PleasureEngine

            engine = PleasureEngine(ctx.book_id)
            engine.detect_events(ctx.draft, str(ctx.chapter))
        except Exception as e:
            logger.debug(f"[Pipeline] Pleasure跳过: {e}")

    @staticmethod
    async def _step_truth_sync(ctx: PipelineContext):
        """真相文件同步"""
        try:
            from kunlun.autosync import AutoSync

            await AutoSync.trigger(
                "chapter_generated",
                {
                    "book_id": ctx.book_id,
                    "chapter": ctx.chapter,
                    "draft": ctx.polished_draft or ctx.draft,
                },
            )
        except Exception as e:
            logger.debug(f"[Pipeline] TruthSync跳过: {e}")

    @staticmethod
    async def _step_reflect(ctx: PipelineContext):
        """写后反思"""
        try:
            from kunlun.learn.reflector import post_reflect_hook

            ctx.reflect_result = post_reflect_hook(
                raw_draft=ctx.draft,
                corrected_draft=ctx.polished_draft or ctx.draft,
                pipeline_id=ctx.pipeline_id,
            )
        except Exception as e:
            logger.debug(f"[Pipeline] Reflect跳过: {e}")


# ── 便捷工厂函数 ────────────────────────────────────


async def run_pipeline(
    book_id: str, chapter: int, mode: str = "standard", progress_cb: Callable | None = None
) -> dict:
    """一键运行小说生成管线"""
    ctx = PipelineContext(
        book_id=book_id,
        chapter=chapter,
        mode=mode,
        pipeline_id=f"{book_id}_ch{chapter}",
        progress_callback=progress_cb,
    )
    pipeline = NovelPipeline(ctx)
    return await pipeline.run()
