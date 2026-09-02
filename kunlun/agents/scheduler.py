"""
Agent集群调度器 — WriteHERE风格任务分解 + 并行Agent编排

核心概念:
- TaskDecomposer: 将章节创作分解为可并行执行的子任务
- AgentCluster: 管理多个Agent实例，并行执行子任务
- Scheduler: 优先级队列 + 依赖解析 + 结果聚合

流程:
  输入task → Decomposer分解为子任务 → Scheduler调度 → AgentCluster并行执行 → 聚合结果
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from kunlun.agents.architect import Architect
from kunlun.agents.auditor import Auditor
from kunlun.agents.makefile import Makefile
from kunlun.agents.publisher import PublisherAgent
from kunlun.agents.sociologist import sociologist
from kunlun.agents.writer import Writer
from kunlun.kg.snapshot import snapshot_manager
from kunlun.style.engineer import StyleEngineer


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class SubTaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SubTask:
    """可被Agent执行的原子子任务"""

    id: str
    name: str
    agent_type: str  # architect/writer/auditor/sociologist/style
    action: str
    payload: dict
    priority: TaskPriority = TaskPriority.NORMAL
    depends_on: list[str] = field(default_factory=list)  # 依赖的子任务ID
    status: SubTaskStatus = SubTaskStatus.PENDING
    result: dict | None = None
    error: str | None = None
    started_at: float = 0
    completed_at: float = 0
    retries: int = 0
    max_retries: int = 2
    human_approval_required: bool = False  # 是否需要人工确认
    approved: bool = False


@dataclass
class TaskPlan:
    """分解后的任务计划"""

    task_id: str
    subtasks: list[SubTask]
    parallel_groups: list[list[str]]  # 每组内的子任务可并行执行
    estimated_time: float = 0


class TaskDecomposer:
    """任务分解器 — 将高层任务分解为可并行的原子子任务"""

    @staticmethod
    def decompose_chapter_generation(
        book_id: str, chapter: int, mode: str = "gacha_parallel_3", chapter_type: str = "normal"
    ) -> TaskPlan:
        """分解章节生成任务为子任务图"""
        task_id = f"{book_id}_ch{chapter}"
        subtasks = []

        # Step 0: KG快照 (必须最先)
        s0 = SubTask(
            id=f"{task_id}_snapshot",
            name="KG快照拍摄",
            agent_type="system",
            action="snapshot",
            payload={"book_id": book_id, "chapter": chapter},
            priority=TaskPriority.CRITICAL,
        )
        subtasks.append(s0)

        # Step 1a: 社会推演 (可与Architect并行，如果KG快照完成)
        s1a = SubTask(
            id=f"{task_id}_society",
            name="社会推演",
            agent_type="sociologist",
            action="deduce",
            payload={"book_id": book_id, "chapter": chapter},
            depends_on=[s0.id],
            priority=TaskPriority.NORMAL,
        )
        subtasks.append(s1a)

        # Step 1b: Architect蓝图 (KG快照完成后)
        s1b = SubTask(
            id=f"{task_id}_architect",
            name="架构师蓝图",
            agent_type="architect",
            action="generate_blueprint",
            payload={"book_id": book_id, "chapter": chapter, "chapter_type": chapter_type},
            depends_on=[s0.id],
            priority=TaskPriority.HIGH,
        )
        subtasks.append(s1b)

        # Step 2: Writer多模型抽卡 (依赖Architect)
        # 分解为多个模型并行调用
        models = ["deepseek-chat"]
        if mode == "gacha_parallel_3":
            models = ["deepseek-chat", "deepseek-chat", "deepseek-chat"]  # 3路并行不同temperature
        elif mode == "gacha_ultimate_5":
            models = ["deepseek-chat"] * 3 + ["deepseek-reasoner"] * 2

        writer_subtasks = []
        for i, model in enumerate(models):
            temp = 0.7 + i * 0.1  # 不同温度
            sw = SubTask(
                id=f"{task_id}_writer_{i}",
                name=f"Writer抽卡-{model}(T={temp:.1f})",
                agent_type="writer",
                action="generate_with_model",
                payload={"model": model, "temperature": temp, "mode": "single_fix"},
                depends_on=[s1b.id],
                priority=TaskPriority.HIGH,
                human_approval_required=False,
            )
            subtasks.append(sw)
            writer_subtasks.append(sw.id)

        # Step 3: Auditor审计 (依赖所有Writer)
        s3 = SubTask(
            id=f"{task_id}_auditor",
            name="8门禁审计",
            agent_type="auditor",
            action="audit",
            payload={},
            depends_on=writer_subtasks,
            priority=TaskPriority.HIGH,
            human_approval_required=True,
        )  # 审计结果需人工确认
        subtasks.append(s3)

        # Step 4: StyleEngineer润色 (依赖审计通过)
        s4 = SubTask(
            id=f"{task_id}_style",
            name="去AI味润色",
            agent_type="style_engineer",
            action="polish",
            payload={},
            depends_on=[s3.id],
            priority=TaskPriority.NORMAL,
        )
        subtasks.append(s4)

        # Step 5: KG更新 (依赖润色完成)
        s5 = SubTask(
            id=f"{task_id}_kg_update",
            name="知识图谱更新",
            agent_type="system",
            action="kg_update",
            payload={},
            depends_on=[s4.id],
            priority=TaskPriority.CRITICAL,
        )
        subtasks.append(s5)

        # Step 6: 发布
        s6 = SubTask(
            id=f"{task_id}_publish",
            name="章节发布",
            agent_type="publisher",
            action="publish",
            payload={},
            depends_on=[s5.id],
            priority=TaskPriority.NORMAL,
            human_approval_required=True,
        )  # 发布前人工确认
        subtasks.append(s6)

        # 并行分组
        parallel_groups = [
            [s0.id],
            [s1a.id, s1b.id],  # 社会推演和蓝图可并行
            writer_subtasks,  # 多模型并行
            [s3.id],
            [s4.id],
            [s5.id],
            [s6.id],
        ]

        return TaskPlan(task_id=task_id, subtasks=subtasks, parallel_groups=parallel_groups)


class AgentCluster:
    """Agent集群 — 管理多个Agent实例，提供统一接口"""

    def __init__(self):
        self._agents = {}

    def get_agent(self, agent_type: str):
        """获取或创建Agent实例"""
        if agent_type not in self._agents:
            if agent_type == "architect":
                self._agents[agent_type] = Architect()
            elif agent_type == "writer":
                self._agents[agent_type] = Writer()
            elif agent_type == "auditor":
                self._agents[agent_type] = Auditor()
            elif agent_type == "sociologist":
                self._agents[agent_type] = sociologist
            elif agent_type == "style_engineer":
                self._agents[agent_type] = StyleEngineer()
            elif agent_type == "publisher":
                self._agents[agent_type] = PublisherAgent()
            elif agent_type == "system":
                self._agents[agent_type] = None  # 系统任务直接执行
            else:
                raise ValueError(f"未知Agent类型: {agent_type}")
        return self._agents[agent_type]

    async def execute_subtask(self, subtask: SubTask, shared_context: dict) -> dict:
        """执行单个子任务"""
        agent = self.get_agent(subtask.agent_type)

        if subtask.agent_type == "system":
            return await self._execute_system_task(subtask, shared_context)

        if agent is None:
            raise ValueError(f"Agent {subtask.agent_type} 未初始化")

        # 构造task，合并共享上下文
        task = {**subtask.payload, **shared_context}
        return await agent.execute(task)

    async def _execute_system_task(self, subtask: SubTask, ctx: dict) -> dict:
        """执行系统级任务"""
        if subtask.action == "snapshot":
            snap = snapshot_manager.create_snapshot(ctx.get("book_id", ""), ctx.get("chapter", 1))
            return {"snapshot_id": snap.snapshot_id, "snapshot": snap}
        if subtask.action == "kg_update":
            m = Makefile()
            # 合并上下文 payload，确保 book_id 等关键字段传递
            kg_task = {**ctx, **subtask.payload} if isinstance(subtask.payload, dict) else ctx
            return await m._run_kg_update(kg_task)
        return {"status": "done"}


class Scheduler:
    """
    任务调度器 — 核心编排引擎

    功能:
    - 依赖解析: 自动识别子任务依赖关系，按DAG拓扑顺序执行
    - 并行执行: 同组无依赖子任务并发执行
    - 人工干预: 需要审批的节点暂停等待
    - 失败重试: 自动重试失败子任务
    - 进度追踪: 实时汇报进度
    """

    def __init__(self, max_parallel: int = 5):
        self.cluster = AgentCluster()
        self.decomposer = TaskDecomposer()
        self.max_parallel = max_parallel
        self._approval_callbacks: dict[str, Callable] = {}
        self._progress_callbacks: list[Callable] = []

    def on_progress(self, callback: Callable):
        """注册进度回调"""
        self._progress_callbacks.append(callback)

    def on_approval_required(self, subtask_id: str, callback: Callable):
        """注册审批回调"""
        self._approval_callbacks[subtask_id] = callback

    async def _report_progress(self, plan: TaskPlan, message: str):
        for cb in self._progress_callbacks:
            with contextlib.suppress(Exception):
                await cb(plan, message)

    async def execute_plan(
        self, plan: TaskPlan, shared_context: dict | None = None, auto_approve: bool = False
    ) -> dict:
        """
        执行任务计划

        Args:
            plan: 任务计划
            shared_context: 共享上下文（book_id, chapter等）
            auto_approve: 是否自动审批所有人工干预节点

        Returns:
            聚合的执行结果
        """
        ctx = shared_context or {}
        results: dict[str, Any] = {}
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def run_subtask(st: SubTask):
            async with semaphore:
                # 等待依赖
                for dep_id in st.depends_on:
                    while dep_id not in results:
                        await asyncio.sleep(0.5)
                    dep_result = results[dep_id]
                    if isinstance(dep_result, Exception):
                        st.status = SubTaskStatus.SKIPPED
                        results[st.id] = None
                        return
                    # 合并依赖结果到context
                    if isinstance(dep_result, dict):
                        ctx.update(dep_result)

                st.status = SubTaskStatus.RUNNING
                st.started_at = time.time()
                await self._report_progress(plan, f"执行: {st.name}")

                # 人工干预检查
                if st.human_approval_required and not auto_approve:
                    if st.id in self._approval_callbacks:
                        try:
                            approved = await self._approval_callbacks[st.id](st)
                            if not approved:
                                st.status = SubTaskStatus.SKIPPED
                                results[st.id] = None
                                return
                        except Exception as e:
                            logger.exception(f"[Scheduler] 审批回调失败: {e}")
                            logger.warning(f"[Scheduler] 审批回调失败: {st.id}")
                    else:
                        logger.info(f"[Scheduler] 子任务 {st.id} 需要人工审批，自动放行")

                # 执行（带重试）
                while st.retries <= st.max_retries:
                    try:
                        st.result = await self.cluster.execute_subtask(st, ctx)
                        st.status = SubTaskStatus.COMPLETED
                        st.completed_at = time.time()
                        results[st.id] = st.result
                        await self._report_progress(plan, f"完成: {st.name}")
                        return
                    except Exception as e:
                        logger.exception(f"[Scheduler] 子任务 {st.name} 执行异常: {e}")
                        st.retries += 1
                        if st.retries > st.max_retries:
                            st.status = SubTaskStatus.FAILED
                            st.error = str(e)
                            results[st.id] = e
                            logger.error(f"[Scheduler] 子任务 {st.name} 失败: {e}")
                            return
                        logger.warning(
                            f"[Scheduler] 重试 {st.name} ({st.retries}/{st.max_retries})"
                        )
                        await asyncio.sleep(1 << st.retries)  # 指数退避

        # 按并行组执行
        for group in plan.parallel_groups:
            group_sids = [sid for sid in group if sid not in results]
            if not group_sids:
                continue
            # TaskGroup 结构化并发: 无异常（异常已由 run_subtask 内部处理）
            group_tasks = [
                run_subtask(next(st for st in plan.subtasks if st.id == sid)) for sid in group_sids
            ]
            gathered = await asyncio.gather(*group_tasks, return_exceptions=True)
            for result in gathered:
                if isinstance(result, Exception):
                    logger.error(f"Scheduler 子任务异常: {result}")

        return self._aggregate_results(plan, results)

    def _aggregate_results(self, plan: TaskPlan, _results: dict[str, Any]) -> dict:
        """聚合子任务结果"""
        aggregated: dict[str, Any] = {
            "task_id": plan.task_id,
            "success": True,
            "subtasks_completed": 0,
            "subtasks_failed": 0,
            "subtasks_skipped": 0,
            "results": {},
        }
        for st in plan.subtasks:
            if st.status == SubTaskStatus.COMPLETED:
                aggregated["subtasks_completed"] += 1
                aggregated["results"][st.name] = st.result
            elif st.status == SubTaskStatus.FAILED:
                aggregated["subtasks_failed"] += 1
                aggregated["success"] = False
            elif st.status == SubTaskStatus.SKIPPED:
                aggregated["subtasks_skipped"] += 1

        return aggregated


# 全局单例
scheduler = Scheduler(max_parallel=5)
